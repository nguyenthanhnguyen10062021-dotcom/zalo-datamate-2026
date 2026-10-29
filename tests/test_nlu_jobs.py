"""Protocol, prompt and temporal context tests use synthetic inputs only."""
from copy import deepcopy

import pandas as pd
import pytest

from nlu.prompt import build_messages
from tools.nlu_jobs import balanced_sample, make_protocol, table_context
from tools.nlu_budget import (PROFILE, reserve_call, reserve_policy_call,
                              reserve_public_submission_call, reserve_semantic_parallel_call)
from tools.nlu_artifacts import combine, split_records
from tools.generation_prefix import pending_jobs
from verification.manifest import object_hash


def test_protocol_is_business_disjoint_stable_and_covers_all_inputs():
    records = [dict(id=f'q{i}-{j}',business_id=f'b{i}',question=f'Synthetic {j}',as_of_date='2026-03-04')
               for i in range(30) for j in range(2)]
    protocol = make_protocol(records,'fixed-seed')
    assert len(protocol['entries']) == 60
    assert {role:list(protocol['businesses'].values()).count(role) for role in
            ('development','calibration','evaluation')} == {'development':18,'calibration':6,'evaluation':6}
    for bid,role in protocol['businesses'].items():
        assert {e['role'] for e in protocol['entries'] if e['business_id']==bid} == {role}
    assert make_protocol(list(reversed(records)),'fixed-seed')['businesses'] == protocol['businesses']
    sample = balanced_sample(protocol['entries'],30)
    assert len(sample) == len({r['business_id'] for r in sample}) == 30


def test_prompt_has_no_implicit_routing_or_gold_features():
    context = {'known_labels':{'channels':['online']}}
    before = deepcopy(context)
    messages = build_messages('Doanh thu hôm nay?', '2026-03-04', context)
    assert messages[-1]['role'] == 'user'
    assert 'as_of_date' in messages[-1]['content'] and 'online' in messages[-1]['content']
    assert 'business_id' not in messages[-1]['content'] and 'question_id' not in messages[-1]['content']
    assert context == before


def test_context_excludes_future_labels_and_exposes_truncation():
    tables = {'don_hang':pd.DataFrame({'ngay_dat':['2026-03-01','2026-03-20'],
                                      'kenh_ban':['known','future']}),
              'mat_hang':pd.DataFrame({'nhom_hang':['B','A','C']})}
    result = table_context(tables,'2026-03-04',limit=2)
    assert result['known_labels']['channels']['values'] == ['known']
    assert result['known_labels']['channels']['complete'] is True
    assert result['known_labels']['product_groups']['values'] == ['A','B']
    assert result['known_labels']['product_groups']['complete'] is False


def test_budget_reserves_failed_calls_too_and_refuses_fifth_or_wrong_profile(tmp_path):
    path = tmp_path/'budget.json'
    with pytest.raises(ValueError, match='profile'):
        reserve_call(path,'test','wrong')
    assert not path.exists()
    for i in range(4):
        result = reserve_call(path,f'test-{i}',PROFILE)
        assert result['envelope_usd'] == 4
        assert result['maximum_compute_usd'] < 2
    with pytest.raises(ValueError, match='exhausted'):
        reserve_call(path,'fifth',PROFILE)
    assert not path.with_suffix('.lock').exists()


def test_public_submission_budget_is_one_call_five_dollars_and_keeps_baseline_unchanged(tmp_path):
    baseline = tmp_path/'baseline.json'
    for i in range(4):
        reserve_call(baseline,f'baseline-{i}',PROFILE)
    baseline_bytes = baseline.read_bytes()

    public = tmp_path/'public.json'
    with pytest.raises(ValueError,match='profile'):
        reserve_public_submission_call(public,'public-test','wrong')
    reservation = reserve_public_submission_call(public,'public-test',PROFILE)
    ledger = __import__('json').loads(public.read_text(encoding='utf-8'))
    assert reservation['envelope_usd'] == 4.0
    assert ledger['authorization'] == 'public_submission_v1'
    assert ledger['limit_usd'] == 5.0 and ledger['margin_usd'] == 1.0
    assert ledger['total_reserved_with_margin_usd'] == 5.0
    assert len(ledger['calls']) == 1
    with pytest.raises(ValueError,match='exhausted'):
        reserve_public_submission_call(public,'second-call',PROFILE)

    tampered = tmp_path/'tampered.json'
    tampered.write_text('{"authorization":"other"}',encoding='utf-8')
    with pytest.raises(ValueError,match='ledger'):
        reserve_public_submission_call(tampered,'public-test',PROFILE)
    assert baseline.read_bytes() == baseline_bytes
    assert not public.with_suffix('.lock').exists()
    assert not tampered.with_suffix('.lock').exists()


def test_budget_policy_maps_only_to_fixed_report_ledgers(tmp_path):
    with pytest.raises(ValueError,match='policy'):
        reserve_policy_call(tmp_path,'other','test',PROFILE)
    reserve_policy_call(tmp_path,'public_submission_v1','public-test',PROFILE)
    assert (tmp_path/'reports/public_submission/v1/budget.json').is_file()
    assert not (tmp_path/'reports/nlu_baseline/v1/budget.json').exists()


def test_semantic_experiment_has_separate_bounded_ledger(tmp_path):
    baseline = tmp_path/'reports/nlu_baseline/v1/budget.json'
    public = tmp_path/'reports/public_submission/v1/budget.json'
    reserve_policy_call(tmp_path,'baseline_v1','original',PROFILE)
    reserve_policy_call(tmp_path,'public_submission_v1','original',PROFILE)
    protected = baseline.read_bytes(), public.read_bytes()
    for stage in ('development', 'evaluation', 'public'):
        reserve_policy_call(tmp_path,'semantic_safety_v1',stage,PROFILE)
    with pytest.raises(ValueError, match='exhausted'):
        reserve_policy_call(tmp_path,'semantic_safety_v1','fourth',PROFILE)
    assert (baseline.read_bytes(), public.read_bytes()) == protected


def test_new_parallel_authorization_cannot_overwrite_sequential_ledger(tmp_path):
    reserve_policy_call(tmp_path,'semantic_safety_v1','development',PROFILE)
    old = tmp_path/'reports/semantic_safety/v1/budget.json'
    protected = old.read_bytes()
    for workers in (0,11,True):
        with pytest.raises(ValueError,match='workers'):
            reserve_semantic_parallel_call(tmp_path,workers,PROFILE)
    receipt = reserve_semantic_parallel_call(tmp_path,10,PROFILE)
    assert receipt['workers'] == 10 and receipt['parallel_maximum_compute_usd'] < 8
    with pytest.raises(ValueError,match='exhausted'):
        reserve_semantic_parallel_call(tmp_path,10,PROFILE)
    assert old.read_bytes() == protected


def test_recovery_freezes_transport_prefix_without_outcome_selection(tmp_path):
    import json
    payload = dict(jobs_sha256='fixed',jobs=[dict(request_id=x) for x in ('a','b','c')])
    prefix = '\n'.join(json.dumps(r) for r in [
        dict(record_type='run_metadata',jobs_sha256='fixed'),
        dict(request_id='a',error='backend_error'),dict(request_id='b',text='any answer')])+'\n'
    complete, jobs = pending_jobs(payload,prefix.encode()+b'{"partial":')
    assert complete == prefix.encode() and jobs == [dict(request_id='c')]
    for invalid in (dict(request_id='a'),dict(request_id='unknown')):
        with pytest.raises(ValueError,match='Unknown/duplicate'):
            pending_jobs(payload,(prefix+json.dumps(invalid)+'\n').encode())
    with pytest.raises(ValueError,match='bound'):
        pending_jobs(payload,prefix.replace('fixed','changed').encode())
    original = reserve_semantic_parallel_call(tmp_path,10,PROFILE)
    protected = (tmp_path/'reports/semantic_safety/v1/parallel-budget.json').read_bytes()
    recovered = reserve_semantic_parallel_call(tmp_path,8,PROFILE,recovery=True)
    assert recovered['workers'] == 8 and original['workers'] == 10
    assert (tmp_path/'reports/semantic_safety/v1/parallel-budget.json').read_bytes() == protected
    with pytest.raises(ValueError,match='exhausted'):
        reserve_semantic_parallel_call(tmp_path,8,PROFILE,recovery=True)


def test_public_budget_rejects_preexisting_ledger_even_with_erased_calls(tmp_path):
    import json

    path = tmp_path/'public.json'
    reserve_public_submission_call(path,'first',PROFILE)
    ledger = json.loads(path.read_text(encoding='utf-8'))
    ledger['calls'] = []
    path.write_text(json.dumps(ledger),encoding='utf-8')
    before = path.read_bytes()
    with pytest.raises(ValueError,match='ledger|exhausted'):
        reserve_public_submission_call(path,'reset-attempt',PROFILE)
    assert path.read_bytes() == before
    assert not path.with_suffix('.lock').exists()


def test_combined_batch_derivation_keeps_fixed_membership_and_partial_failures():
    def payload(ids):
        value=dict(schema={},sampling={},selected=len(ids),jobs=[{'request_id':i,'messages':[]} for i in ids])
        return value|{'jobs_sha256':object_hash(value)}
    first,second=payload(['a','b']),payload(['c'])
    parent=combine([first,second])
    raw=[{'record_type':'run_metadata','jobs_sha256':parent['jobs_sha256']},
         {'request_id':'a','text':'raw-output-unchanged'}, {'request_id':'c','error':'timeout'}]
    derived=split_records(parent,first,raw,'parent-file-hash')
    assert derived[0]['jobs_sha256']==first['jobs_sha256']
    assert derived[-1]==raw[1]
    assert [r['request_id'] for r in derived if 'request_id' in r]==['a']
    assert 'b' in parent['parents'][0]['request_ids']  # absent output stays in frozen child input
    with pytest.raises(ValueError,match='Overlap'):
        combine([first,first])
    with pytest.raises(ValueError,match='declared'):
        split_records(parent,payload(['a']),raw,'hash')
