"""Replay integrity, denominator preservation and prediction-before-gold checks."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from queryplan_fixtures import plan, period_spec
from tools import nlu_jobs
from tools import replay_semantic as replay
from verification.manifest import file_hash, object_hash


@pytest.fixture
def frozen_case(tmp_path, monkeypatch):
    real_root = replay.ROOT
    for name in ('nlu/semantic.py', 'nlu/parser.py', 'nlu/pipeline.py',
                 'tools/replay_semantic.py', 'evaluate/evaluate.py'):
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(real_root/name, target)
    monkeypatch.setattr(replay, 'ROOT', tmp_path)
    monkeypatch.setattr(nlu_jobs, 'ROOT', tmp_path)
    split, cache, reports = tmp_path/'split', tmp_path/'cache', tmp_path/'reports'
    split.mkdir()
    reports.mkdir()
    records = [
        dict(id='q0', business_id='b0', as_of_date='2024-09-12', question='Doanh thu tháng này?'),
        dict(id='q1', business_id='b0', as_of_date='2024-09-12', question='Ngày nào tháng này doanh thu cao nhất?'),
    ]
    (split/'questions.jsonl').write_text('\n'.join(json.dumps(r) for r in records), encoding='utf-8')
    (split/'rulebook.md').write_text('synthetic rulebook', encoding='utf-8')
    (split/'calendar.csv').write_text('synthetic calendar', encoding='utf-8')
    (split/'answers.jsonl').mkdir()  # Public replay must never try to read this.
    business = cache/'b0'
    business.mkdir(parents=True)
    for name in ('don_hang.parquet', 'dong_hang.parquet', 'mat_hang.parquet',
                 'quy_doi_don_vi.parquet', 'khach_hang.parquet', 'cua_hang.json'):
        (business/name).write_bytes(b'fake cache bytes used only for hashing')
    jobs = dict(purpose='public_test_submission_generation', split_root=str(split),
        cache_root=str(cache), sources=replay._source_hashes(split), businesses=['b0'],
        cache_sha256=replay._cache_hashes(cache, ['b0']), selected=2, code_sha256={'old.py':'original'},
        jobs=[dict(id=q['id'], business_id=q['business_id'], as_of_date=q['as_of_date'],
            question_sha256=object_hash(q), request_id='r'+str(i),
            messages=[], messages_sha256=object_hash([])) for i,q in enumerate(records)])
    jobs['jobs_sha256'] = object_hash(jobs)
    jobs_path = reports/'jobs.json'
    nlu_jobs.write_new(jobs_path, jobs)
    generations = [dict(record_type='run_metadata', jobs_sha256=jobs['jobs_sha256']),
        *[dict(request_id=j['request_id'], text=json.dumps(plan()), finish_reason='stop') for j in jobs['jobs']]]
    generations_path = reports/'generations.jsonl'
    generations_path.write_text('\n'.join(json.dumps(r) for r in generations), encoding='utf-8')
    rows = [dict(id=j['id'], business_id='b0', request_id=j['request_id'],
            submission=dict(id=j['id'], type='number', answer=0), status='answered',
            stage='dispatch', plan=plan()) for j in jobs['jobs']]
    prior = dict(jobs_sha256=jobs['jobs_sha256'], jobs_file_sha256=file_hash(jobs_path),
        generations_file_sha256=file_hash(generations_path), rows=rows)
    prior['predictions_sha256'] = object_hash(prior)
    predictions_path = reports/'old.json'
    nlu_jobs.write_new(predictions_path, prior)
    return jobs_path, predictions_path, generations_path, reports/'out', records


def test_public_replay_preserves_zero_and_never_opens_gold(frozen_case, monkeypatch):
    from verification import runner
    def forbidden(*args):
        raise AssertionError('Public replay tried to load scorer/gold')
    monkeypatch.setattr(runner, '_scorer', forbidden)
    monkeypatch.setattr(runner, '_reference', forbidden)
    jobs, prior, generations, out, records = frozen_case
    old_bytes = prior.read_bytes()
    summary = replay.replay(jobs, prior, generations, out, 'public')
    rows = [json.loads(line) for line in (out/'submission.jsonl').read_text(encoding='utf-8').splitlines()]
    assert rows == [dict(id='q0', type='number', answer=0), dict(id='q1', type='abstain')]
    assert summary['total'] == 2 and summary['inference_rerun'] is False
    assert summary['submission_types'] == {'number':1, 'abstain':1}
    assert prior.read_bytes() == old_bytes
    assert 'after' not in summary
    with pytest.raises(FileExistsError):
        replay.replay(jobs, prior, generations, out, 'public')


@pytest.mark.parametrize('target', ['predictions', 'jobs', 'generations', 'corpus', 'cache'])
def test_replay_rejects_modified_original_artifacts_before_writing(frozen_case, target):
    jobs, prior, generations, out, _ = frozen_case
    if target in ('predictions', 'jobs'):
        path = prior if target == 'predictions' else jobs
        payload = json.loads(path.read_text(encoding='utf-8'))
        payload['tampered'] = True
        path.write_text(json.dumps(payload), encoding='utf-8')
    elif target == 'generations':
        with generations.open('a', encoding='utf-8') as stream:
            stream.write('\n')
    else:
        payload = json.loads(jobs.read_text(encoding='utf-8'))
        path = (Path(payload['split_root'])/'questions.jsonl' if target == 'corpus'
                else Path(payload['cache_root'])/'b0/mat_hang.parquet')
        with path.open('ab') as stream:
            stream.write(b' ')
    with pytest.raises(ValueError, match='changed|binding'):
        replay.replay(jobs, prior, generations, out, 'public')
    assert not out.exists()


def test_raw_generation_must_match_the_frozen_prediction_plan(frozen_case):
    jobs, prior, generations, out, _ = frozen_case
    payload = json.loads(prior.read_text(encoding='utf-8'))
    payload['rows'][0]['plan']['period'] = period_spec('yesterday')
    payload['predictions_sha256'] = object_hash({k:v for k,v in payload.items() if k != 'predictions_sha256'})
    prior.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError, match='plan differs'):
        replay.replay(jobs, prior, generations, out, 'public')
    assert not out.exists()


def test_train_replay_freezes_all_predictions_before_scoring(frozen_case, monkeypatch):
    from verification import runner
    jobs_path, prior_path, generations, out, records = frozen_case
    jobs = json.loads(jobs_path.read_text(encoding='utf-8'))
    protocol = dict(protocol_sha256='synthetic-protocol', train_root=jobs['split_root'],
                    entries=[dict(id=r['id'], role='evaluation') for r in records])
    jobs.update(protocol_path='synthetic-protocol', protocol_sha256='synthetic-protocol',
                role='evaluation', total_eligible=2, outside_selection=0)
    for job in jobs['jobs']:
        job['role'] = 'evaluation'
    jobs['jobs_sha256'] = object_hash({k:v for k,v in jobs.items() if k != 'jobs_sha256'})
    jobs_path.write_text(json.dumps(jobs), encoding='utf-8')
    wires = [json.loads(line) for line in generations.read_text(encoding='utf-8').splitlines()]
    wires[0]['jobs_sha256'] = jobs['jobs_sha256']
    generations.write_text('\n'.join(json.dumps(r) for r in wires), encoding='utf-8')
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    prior.update(jobs_file_sha256=file_hash(jobs_path), jobs_sha256=jobs['jobs_sha256'],
                 generations_file_sha256=file_hash(generations))
    prior['predictions_sha256'] = object_hash({k:v for k,v in prior.items() if k != 'predictions_sha256'})
    prior_path.write_text(json.dumps(prior), encoding='utf-8')
    monkeypatch.setattr(replay, 'load_protocol', lambda path:(protocol, records))
    class Scorer:
        def score_one(self, gold, submission):
            if submission['type'] == 'abstain':
                return 'abstain', None
            return ('correct' if gold == submission else 'wrong'), None
    def reference_after_freeze(*args):
        frozen = json.loads((out/'predictions.json').read_text(encoding='utf-8'))
        assert frozen['gold_opened_this_run'] is False and len(frozen['rows']) == 2
        return {'q0':dict(id='q0', type='number', answer=0), 'q1':dict(id='q1', type='date', answer='2024-09-01')}
    monkeypatch.setattr(runner, '_scorer', Scorer)
    monkeypatch.setattr(runner, '_reference', reference_after_freeze)
    monkeypatch.setattr(replay, 'file_hash', lambda path: 'synthetic-gold' if Path(path).name == 'answers.jsonl' else file_hash(path))
    summary = replay.replay(jobs_path, prior_path, generations, out, 'train')
    assert summary['before']['correct'] == summary['before']['wrong'] == 1
    assert summary['after']['correct'] == summary['after']['abstain'] == 1
    assert summary['after']['wrong'] == 0 and summary['total'] == 2
    assert summary['transitions'] == {'correct->correct':1, 'wrong->abstain':1}
