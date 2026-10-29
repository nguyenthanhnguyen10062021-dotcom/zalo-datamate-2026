"""Synthetic end-to-end diagnostics keep missing/truncated jobs in denominators."""
import json
from pathlib import Path
import shutil

import pandas as pd
import pytest

import run_nlu
import tools.nlu_jobs as jobs_tool
from queryplan_fixtures import plan
from verification.manifest import object_hash, questions


@pytest.mark.parametrize('records', [
    [{'request_id':'other','text':'{}'}],
    [{'request_id':'r1','text':'{}'},{'request_id':'r1','text':'{}'}],
])
def test_generation_artifact_rejects_unknown_or_duplicate_records(records):
    with pytest.raises(ValueError,match='Unknown/duplicate'):
        run_nlu.generation_index(records,{'r1'})


def test_scoring_freezes_all_predictions_before_gold_including_missing_and_truncated(tmp_path,rules,monkeypatch):
    original_root = Path(run_nlu.__file__).resolve().parent
    for name in ('run_nlu.py','nlu/parser.py','nlu/pipeline.py','queryplan/executor.py','business/sales.py','evaluate/evaluate.py'):
        target = tmp_path/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original_root/name,target)
    monkeypatch.setattr(run_nlu,'ROOT',tmp_path)
    monkeypatch.setattr(jobs_tool,'ROOT',tmp_path)
    train,cache,out = tmp_path/'train',tmp_path/'cache',tmp_path/'reports/run'
    train.mkdir()
    records = [dict(id=f'q{i}',business_id=f'b{i}',question='Doanh thu thang nay?',as_of_date='2026-03-04') for i in range(3)]
    (train/'questions.jsonl').write_text('\n'.join(json.dumps(r) for r in records),encoding='utf-8')
    (train/'answers.jsonl').write_text('\n'.join(json.dumps({'id':r['id'],'type':'number','answer':100}) for r in records),encoding='utf-8')
    (train/'rulebook.md').write_text(rules.text,encoding='utf-8')
    (train/'calendar.csv').write_text('synthetic unused calendar',encoding='utf-8')
    for record in records:
        folder = cache/record['business_id']
        folder.mkdir(parents=True)
        pd.DataFrame([dict(ma_don='O1',ngay_dat='2026-03-01',trang_thai='hoan_thanh',tong_tien_hang=100)]).to_parquet(folder/'don_hang.parquet')
        pd.DataFrame().to_parquet(folder/'dong_hang.parquet')
        pd.DataFrame().to_parquet(folder/'mat_hang.parquet')
        (folder/'cua_hang.json').write_text(json.dumps({'co_ma_don':True,'ngay_bat_dau_du_lieu':'2026-03-01','ngay_ket_thuc_du_lieu':'2026-03-31'}),encoding='utf-8')
    protocol_path = tmp_path/'reports/protocol.json'
    protocol = jobs_tool.freeze_protocol(train,cache,protocol_path)
    messages=[{'role':'user','content':'synthetic'}]
    roles={e['id']:e['role'] for e in protocol['entries']}
    payload=dict(protocol_path=str(protocol_path),protocol_sha256=protocol['protocol_sha256'],
        role='all',selected=3,total_eligible=3,outside_selection=0,code_sha256={},jobs=[
            dict(id=r['id'],business_id=r['business_id'],as_of_date=r['as_of_date'],role=roles[r['id']],
                 request_id=object_hash({'protocol':protocol['protocol_sha256'],'question':object_hash(r)}),
                 question_sha256=object_hash(r),messages=messages,messages_sha256=object_hash(messages))
            for i,r in enumerate(records)])
    payload['jobs_sha256']=object_hash(payload)
    jobs_path=tmp_path/'reports/jobs.json'
    jobs_tool.write_new(jobs_path,payload)
    generations = tmp_path/'reports/generations.jsonl'
    raw=[dict(record_type='run_metadata',jobs_sha256=payload['jobs_sha256']),
         dict(request_id=payload['jobs'][0]['request_id'],text=json.dumps(plan()),finish_reason='stop'),
         dict(request_id=payload['jobs'][2]['request_id'],text=json.dumps(plan()),finish_reason='length')]
    generations.write_text('\n'.join(json.dumps(r) for r in raw),encoding='utf-8')
    actual_reference=run_nlu._reference
    def after_freeze(*args):
        frozen=json.loads((out/'predictions.json').read_text(encoding='utf-8'))
        assert frozen['gold_opened_this_run'] is False and len(frozen['rows'])==3
        return actual_reference(*args)
    monkeypatch.setattr(run_nlu,'_reference',after_freeze)
    result=run_nlu.run(jobs_path,generations,out)
    assert (result['total'],result['correct'],result['wrong'],result['abstain'])==(3,1,0,2)
    assert result['execution_statuses']=={'answered':1,'missing_generation':1,'incomplete_generation':1}
    assert result['json_valid']==result['plan_contract_valid']==1
    assert result['penalized_accuracy']==pytest.approx(1/3)
    assert len((out/'submission.jsonl').read_text(encoding='utf-8').splitlines())==3
