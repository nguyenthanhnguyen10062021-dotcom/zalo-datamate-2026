"""Synthetic public-submission preparation and integrity tests; no BTC rows or gold."""
import json
from pathlib import Path

import pandas as pd
import pytest

import run_public_submission
from queryplan import QueryExecutor as RealQueryExecutor
from queryplan_fixtures import plan
from tools import public_jobs


@pytest.fixture
def public_case(tmp_path, monkeypatch):
    split = tmp_path/'public_test'
    cache = tmp_path/'cache'
    reports = tmp_path/'reports'
    split.mkdir()
    reports.mkdir()
    questions = [
        dict(id='route-001',business_id='shop-a',question='Doanh thu hôm nay?',as_of_date='2026-03-04'),
        dict(id='route-002',business_id='shop-b',question='Số đơn hôm qua?',as_of_date='2026-03-05'),
        dict(id='route-003',business_id='shop-a',question='Doanh thu tháng này?',as_of_date='2026-03-06'),
    ]
    (split/'questions.jsonl').write_text(
        '\n'.join(json.dumps(row,ensure_ascii=False) for row in questions),encoding='utf-8')
    (split/'rulebook.md').write_text('# Synthetic rulebook\n',encoding='utf-8')
    (split/'calendar.csv').write_text('solar_date,lunar_date\n2026-03-04,2026-01-16\n',encoding='utf-8')
    (split/'answers.jsonl').mkdir()  # Any attempt to read a public gold file must fail.
    for bid in ('shop-a','shop-b'):
        folder = cache/bid
        folder.mkdir(parents=True)
        pd.DataFrame([dict(ma_don='O1',ngay_dat='2026-03-01',kenh_ban='online',
                           hinh_thuc_tt='cash',nhom_khach='regular')]).to_parquet(folder/'don_hang.parquet')
        pd.DataFrame([dict(ma_hang='P1',so_luong=1)]).to_parquet(folder/'dong_hang.parquet')
        pd.DataFrame([dict(ma_hang='P1',ten_hang='Synthetic',nhom_hang='Group',
                           don_vi_co_ban='cai')]).to_parquet(folder/'mat_hang.parquet')
        pd.DataFrame([dict(ma_hang='P1',don_vi='cai',he_so=1)]).to_parquet(
            folder/'quy_doi_don_vi.parquet')
        pd.DataFrame([dict(ma_khach='C1',ten_khach='Synthetic customer')]).to_parquet(
            folder/'khach_hang.parquet')
        (folder/'cua_hang.json').write_text(json.dumps({'business_id':bid}),encoding='utf-8')
    code = tmp_path/'code.py'
    code.write_text('VERSION = 1\n',encoding='utf-8')
    monkeypatch.setattr(public_jobs,'ROOT',tmp_path)
    monkeypatch.setattr(public_jobs,'code_paths',lambda:[code])
    return split,cache,reports,questions,code


def test_prepare_public_jobs_freezes_all_inputs_without_gold_or_routing_in_messages(public_case):
    split,cache,reports,questions,_ = public_case
    payload = public_jobs.prepare_public_jobs(split,cache,reports/'jobs.json')
    loaded,records = public_jobs.load_public_jobs(reports/'jobs.json')
    assert loaded == payload and records == questions
    assert payload['selected'] == 3 and payload['businesses'] == ['shop-a','shop-b']
    assert [job['id'] for job in payload['jobs']] == [row['id'] for row in questions]
    assert len({job['request_id'] for job in payload['jobs']}) == 3
    assert payload['prompt_version'] == 'nlu-safety-3'
    assert payload['sampling'] == {'temperature':0.0,'seed':20261029,'max_tokens':768}
    assert set(payload['sources']) == {'questions.jsonl','rulebook.md','calendar.csv'}
    assert set(payload['cache_sha256']) == {'shop-a','shop-b'}
    assert payload['code_sha256']
    for job in payload['jobs']:
        wire = json.dumps(job['messages'],ensure_ascii=False)
        assert job['id'] not in wire and job['business_id'] not in wire
    assert 'answers.jsonl' not in json.dumps(payload,ensure_ascii=False)


@pytest.mark.parametrize('bad_row', [
    dict(id='route-001',business_id='shop-a',question='Duplicate',as_of_date='2026-03-04'),
    dict(id='route-004',business_id='../escape',question='Invalid business',as_of_date='2026-03-04'),
])
def test_prepare_public_jobs_rejects_duplicate_id_or_unsafe_business(public_case,bad_row):
    split,cache,reports,questions,_ = public_case
    rows = [*questions,bad_row]
    (split/'questions.jsonl').write_text(
        '\n'.join(json.dumps(row) for row in rows),encoding='utf-8')
    with pytest.raises(ValueError):
        public_jobs.prepare_public_jobs(split,cache,reports/'bad-jobs.json')


def test_prepare_public_jobs_requires_every_canonical_cache_file(public_case):
    split,cache,reports,_,_ = public_case
    (cache/'shop-b/khach_hang.parquet').unlink()
    with pytest.raises(ValueError,match='khach_hang'):
        public_jobs.prepare_public_jobs(split,cache,reports/'missing-cache.json')


@pytest.mark.parametrize('target', ['questions','rulebook','calendar','cache','code'])
def test_load_public_jobs_rejects_frozen_input_drift(public_case,target):
    split,cache,reports,_,code = public_case
    path = reports/f'jobs-{target}.json'
    public_jobs.prepare_public_jobs(split,cache,path)
    if target == 'questions':
        with (split/'questions.jsonl').open('a',encoding='utf-8') as stream:
            stream.write('\n')
    elif target == 'rulebook':
        with (split/'rulebook.md').open('a',encoding='utf-8') as stream:
            stream.write('changed')
    elif target == 'calendar':
        with (split/'calendar.csv').open('a',encoding='utf-8') as stream:
            stream.write('changed')
    elif target == 'cache':
        pd.DataFrame([dict(ma_khach='C2')]).to_parquet(cache/'shop-a/khach_hang.parquet')
    else:
        code.write_text('VERSION = 2\n',encoding='utf-8')
    with pytest.raises(ValueError,match='changed|drift|fingerprint'):
        public_jobs.load_public_jobs(path)


@pytest.mark.parametrize('records', [
    [dict(request_id='unknown',text='{}',finish_reason='stop')],
    [dict(request_id='r1',text='{}',finish_reason='stop'),
     dict(request_id='r1',text='{}',finish_reason='stop')],
])
def test_public_generation_index_rejects_unknown_or_duplicate_records(records):
    with pytest.raises(ValueError,match='Unknown/duplicate'):
        run_public_submission.generation_index(records,{'r1'})


@pytest.mark.parametrize('metadata', [
    [],
    [dict(record_type='run_metadata',jobs_sha256='wrong')],
])
def test_public_runner_rejects_missing_or_wrong_job_binding_before_artifacts(
        public_case,monkeypatch,metadata):
    split,cache,reports,_,_ = public_case
    jobs_path = reports/'bound-jobs.json'
    public_jobs.prepare_public_jobs(split,cache,jobs_path)
    generations_path = reports/'unbound-generations.jsonl'
    generations_path.write_text(
        '\n'.join(json.dumps(row) for row in metadata),encoding='utf-8')
    monkeypatch.setattr(run_public_submission,'ROOT',public_jobs.ROOT)
    out = reports/'unbound-run'
    with pytest.raises(ValueError,match='bound|metadata'):
        run_public_submission.run(jobs_path,generations_path,out)
    assert not out.exists()


def test_public_runner_preserves_all_rows_and_sanitizes_failures(
        public_case,rules,monkeypatch):
    split,cache,reports,_,_ = public_case
    questions = [
        dict(id=f'public-{index}',business_id='shop-a',
             question='Số đơn tháng này?' if index == 4 else 'Doanh thu tháng này?',
             as_of_date='2026-03-04')
        for index in range(5)
    ]
    (split/'questions.jsonl').write_text(
        '\n'.join(json.dumps(row,ensure_ascii=False) for row in questions),encoding='utf-8')
    (split/'rulebook.md').write_text(rules.text,encoding='utf-8')
    pd.DataFrame([dict(ma_don='O1',ngay_dat='2026-03-01',trang_thai='hoan_thanh',
                       tong_tien_hang=100,kenh_ban='online',hinh_thuc_tt='cash',
                       nhom_khach='regular')]).to_parquet(cache/'shop-a/don_hang.parquet')
    pd.DataFrame().to_parquet(cache/'shop-a/dong_hang.parquet')
    (cache/'shop-a/cua_hang.json').write_text(json.dumps(dict(business_id='shop-a',
        co_ma_don=True,ngay_bat_dau_du_lieu='2026-03-01',
        ngay_ket_thuc_du_lieu='2026-03-31')),encoding='utf-8')
    jobs_path = reports/'runner-jobs.json'
    jobs = public_jobs.prepare_public_jobs(split,cache,jobs_path)
    generations = [dict(record_type='run_metadata',jobs_sha256=jobs['jobs_sha256']),
        dict(record_type='worker_metadata',model='synthetic'),
        dict(request_id=jobs['jobs'][0]['request_id'],text=json.dumps(plan()),finish_reason='stop'),
        dict(request_id=jobs['jobs'][2]['request_id'],text=json.dumps(plan()),finish_reason='length'),
        dict(request_id=jobs['jobs'][3]['request_id'],error='backend_error',reason='synthetic'),
        dict(request_id=jobs['jobs'][4]['request_id'],text=json.dumps(plan('order_count')),
             finish_reason='stop')]
    generations_path = reports/'runner-generations.jsonl'
    generations_path.write_text(
        '\n'.join(json.dumps(row) for row in generations),encoding='utf-8')

    class ExplodingExecutor:
        def __init__(self,*args,**kwargs):
            self.delegate = RealQueryExecutor(*args,**kwargs)
        def execute(self,raw_plan):
            if raw_plan['operation'] == 'order_count':
                raise RuntimeError('synthetic unexpected failure')
            return self.delegate.execute(raw_plan)

    monkeypatch.setattr(run_public_submission,'ROOT',public_jobs.ROOT)
    monkeypatch.setattr(run_public_submission,'QueryExecutor',ExplodingExecutor)
    out = reports/'runner-output'
    summary = run_public_submission.run(jobs_path,generations_path,out)
    rows = [json.loads(line) for line in
            (out/'submission.jsonl').read_text(encoding='utf-8').splitlines()]
    sidecar = json.loads((out/'predictions.json').read_text(encoding='utf-8'))
    assert [row['id'] for row in rows] == [row['id'] for row in questions]
    assert rows[0] == {'id':'public-0','type':'number','answer':100}
    assert rows[1:] == [{'id':f'public-{index}','type':'abstain'} for index in range(1,5)]
    assert [row['status'] for row in sidecar['rows']] == [
        'answered','missing_generation','incomplete_generation','backend_error','execution_error']
    assert sidecar['metadata'] == generations[:2]
    assert all('reason' not in row for row in rows)
    assert any('synthetic unexpected failure' in (row.get('diagnostic_reason') or '')
               for row in sidecar['rows'])
    assert summary['total'] == 5 and sum(summary['submission_types'].values()) == 5


def test_submission_validator_accepts_all_official_output_types():
    rows = [
        {'id':'q0','type':'number','answer':1},
        {'id':'q1','type':'percent','answer':1.5},
        {'id':'q2','type':'date','answer':'2026-03'},
        {'id':'q3','type':'boolean','answer':False},
        {'id':'q4','type':'string','answer':'Synthetic'},
        {'id':'q5','type':'list','answer':['A',2]},
        {'id':'q6','type':'table','answer':{'columns':['name','value'],'rows':[['A',2]]}},
        {'id':'q7','type':'unanswerable','reason':'Không đủ dữ liệu'},
        {'id':'q8','type':'abstain'},
    ]
    run_public_submission.validate_submission(
        rows,[{'id':f'q{index}'} for index in range(len(rows))])


def test_public_runner_checks_the_original_question_before_dispatch(public_case, rules, monkeypatch):
    split,cache,reports,questions,_ = public_case
    (split/'rulebook.md').write_text(rules.text,encoding='utf-8')
    jobs_path = reports/'semantic-jobs.json'
    jobs = public_jobs.prepare_public_jobs(split,cache,jobs_path)
    # Every plan is valid JSON/schema, but asks for this_month instead of the
    # original corpus's today/yesterday. No business execution should occur.
    path = reports/'semantic-generations.jsonl'
    records = [dict(record_type='run_metadata',jobs_sha256=jobs['jobs_sha256']),
        *[dict(request_id=job['request_id'],text=json.dumps(plan()),finish_reason='stop')
          for job in jobs['jobs'][:2]]]
    path.write_text('\n'.join(json.dumps(row) for row in records),encoding='utf-8')
    class NeverExecute:
        def __init__(self,*args,**kwargs):
            pass
        def execute(self, candidate):
            raise AssertionError('Mismatched question reached execution')
    monkeypatch.setattr(run_public_submission,'ROOT',public_jobs.ROOT)
    monkeypatch.setattr(run_public_submission,'QueryExecutor',NeverExecute)
    summary = run_public_submission.run(jobs_path,path,reports/'semantic-result')
    assert summary['execution_statuses'] == {'semantic_rejected':2,'missing_generation':1}
    assert summary['submission_types'] == {'abstain':3}


@pytest.mark.parametrize('mutate', [
    lambda rows: rows.append({'id':'q1','type':'abstain'}),
    lambda rows: rows.reverse(),
    lambda rows: rows[0].update(answer=float('nan')),
    lambda rows: rows[0].update(answer=True),
    lambda rows: rows[0].update(status='answered'),
    lambda rows: rows[0].update(alias=[]),
    lambda rows: rows[0].update(type='string'),
    lambda rows: rows[0].update(type='list',answer=[{'nested':'bad'}]),
    lambda rows: rows[0].update(type='table',answer={'columns':['x'],'rows':[[1,2]]}),
])
def test_submission_validator_rejects_order_duplicates_nonfinite_and_bad_shapes(mutate):
    rows = [{'id':'q0','type':'number','answer':1},
            {'id':'q1','type':'abstain'}]
    mutate(rows)
    with pytest.raises(ValueError):
        run_public_submission.validate_submission(rows,[{'id':'q0'},{'id':'q1'}])


def test_parallel_merge_keeps_primary_precedence_and_complete_frozen_order(public_case):
    from tools.merge_public_generations import merge

    split,cache,reports,_,_ = public_case
    jobs_path = reports/'merge-jobs.json'
    jobs = public_jobs.prepare_public_jobs(split,cache,jobs_path)
    metadata = dict(record_type='run_metadata',jobs_sha256=jobs['jobs_sha256'])
    rows = [dict(request_id=job['request_id'],text=f'primary-{index}',finish_reason='stop')
            for index,job in enumerate(jobs['jobs'])]
    primary,secondary,out = reports/'primary.jsonl',reports/'secondary.jsonl',reports/'merged.jsonl'
    primary.write_text('\n'.join(json.dumps(row) for row in [metadata,*rows[:2]])+'\n',encoding='utf-8')
    secondary.write_text(json.dumps(metadata)+'\n',encoding='utf-8')
    assert merge(jobs_path,primary,secondary,out)['ready'] is False
    assert not out.exists()
    secondary.write_text('\n'.join(json.dumps(row) for row in
        [metadata,dict(rows[1],text='secondary-overlap'),rows[2]])+'\n',encoding='utf-8')
    result = merge(jobs_path,primary,secondary,out)
    assert result == dict(ready=True,received=3,expected=3,overlaps=1)
    merged = [json.loads(line) for line in out.read_text(encoding='utf-8').splitlines()]
    assert merged[1:] == rows


def test_merge_cli_imports_from_repository_root():
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run([sys.executable,str(root/'tools/merge_public_generations.py'),'--help'],
        cwd=root,capture_output=True,text=True,timeout=30)
    assert completed.returncode == 0, completed.stderr


def test_local_process_workers_preserve_serial_submission_order(public_case,monkeypatch,rules):
    split,cache,reports,_,_ = public_case
    (split/'rulebook.md').write_text(rules.text,encoding='utf-8')
    jobs_path = reports/'process-jobs.json'
    jobs = public_jobs.prepare_public_jobs(split,cache,jobs_path)
    path = reports/'missing-generations.jsonl'
    path.write_text(json.dumps(dict(record_type='run_metadata',
        jobs_sha256=jobs['jobs_sha256']))+'\n',encoding='utf-8')
    monkeypatch.setattr(run_public_submission,'ROOT',public_jobs.ROOT)
    run_public_submission.run(jobs_path,path,reports/'serial',workers=1)
    run_public_submission.run(jobs_path,path,reports/'parallel',workers=2)
    assert (reports/'serial/submission.jsonl').read_bytes() == (
        reports/'parallel/submission.jsonl').read_bytes()
