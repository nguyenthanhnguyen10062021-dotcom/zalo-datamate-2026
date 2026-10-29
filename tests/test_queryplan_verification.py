"""Retrospective replay on synthetic questions, cache and reference answers."""
import json

import pandas as pd
import pytest

from test_business_sales import tables
from verification.manifest import ManifestError, build_manifest, write_json
from verification.runner import verification_exit_code, verify_manifest


def jsonl(path, rows):
    path.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows), encoding='utf-8')


@pytest.fixture
def replay_corpus(tmp_path, tables, rules):
    train = tmp_path / 'train'
    train.mkdir()
    examples = [
        ('Doanh thu tháng này bao nhiêu?', 'number', 201),
        ('Có bao nhiêu đơn hôm nay?', 'number', 1),  # Wrong literal deliberately retained.
        ('Bao nhiêu đơn bị hủy tháng này?', 'number', 1),
        ('Tỷ lệ đơn hủy tháng này là bao nhiêu phần trăm?', 'percent', 25),
        ('Giá trị trung bình một đơn tháng này là bao nhiêu?', 'number', 101),
        ('Bán được bao nhiêu ly tháng này?', 'number', 2),
        ('Top 2 mặt hàng theo doanh thu tháng này?', 'list', ['Coffee', 'Tea']),
        ('Top 2 khách hàng theo số đơn tháng này?', 'list', ['Lan', 'Lan']),
        ('Doanh thu ngày 2026-03-02 tăng bao nhiêu phần trăm so với ngày 2026-03-01?', 'percent', -0.99),
        ('Tỷ trọng doanh thu nhóm hàng "Đồ uống" tháng này là bao nhiêu?', 'percent', 84.58),
        ('Doanh thu kênh "unknown" tháng này bao nhiêu?', 'number', 0),
        ('Câu ngoài grammar', 'string', 'x'),
    ]
    questions, gold = [], []
    for i, (text, kind, answer) in enumerate(examples):
        qid = f'q{i}'
        questions.append(dict(id=qid, business_id='shop', as_of_date='2026-03-04', question=text))
        gold.append(dict(id=qid, type=kind, answer=answer))
    gold[6]['alias'] = [['Cà phê'], ['Trà']]
    jsonl(train/'questions.jsonl', questions)
    jsonl(train/'answers.jsonl', gold)
    (train/'rulebook.md').write_text(rules.text, encoding='utf-8')
    cache = tmp_path / 'cache' / 'shop'
    cache.mkdir(parents=True)
    for key in ('don_hang', 'dong_hang', 'mat_hang'):
        tables[key].to_parquet(cache/f'{key}.parquet')
    write_json(cache/'cua_hang.json', tables['cua_hang'])
    manifest = tmp_path / 'manifest.json'
    write_json(manifest, build_manifest(train/'questions.jsonl', train/'rulebook.md'))
    return manifest, train, cache.parent, gold


def test_verifier_executes_all_ten_apis_without_legacy_gate_and_preserves_denominators(replay_corpus):
    manifest, train, cache, _ = replay_corpus
    result = verify_manifest(manifest, train, cache)
    assert (result['total'], result['selected'], result['outside_selection']) == (12, 11, 1)
    assert (result['compared'], result['matched'], result['mismatch'], result['abstained']) == (10, 9, 1, 1)
    assert result['execution_errors'] == 0
    assert result['selected'] == result['compared'] + result['abstained'] + result['execution_errors']
    assert len(result['by_operation']) == 10
    assert result['rows'][6]['score'] == 'correct'  # Evaluator aliases, not literal equality.
    assert result['rows'][10]['execution_status'] == 'unresolved_entity'
    assert result['rows'][10]['score'] == 'abstain'
    assert len(result['cache_sha256']['shop']) == 4
    assert verification_exit_code(result) == 1


def test_reference_values_do_not_change_selection_or_execution(replay_corpus):
    manifest, train, cache, gold = replay_corpus
    first = verify_manifest(manifest, train, cache)
    gold[0]['answer'] = -999
    jsonl(train/'answers.jsonl', gold)
    second = verify_manifest(manifest, train, cache)
    assert first['selected'] == second['selected']
    assert [r['prediction'] for r in first['rows']] == [r['prediction'] for r in second['rows']]
    assert second['mismatch'] == first['mismatch'] + 1


def test_list_order_uses_real_evaluator(replay_corpus):
    manifest, train, cache, gold = replay_corpus
    gold[6]['answer'] = ['Trà', 'Cà phê']
    gold[6].pop('alias')
    jsonl(train/'answers.jsonl', gold)
    assert verify_manifest(manifest, train, cache)['rows'][6]['score'] == 'wrong'


@pytest.mark.parametrize('bad_gold', ['duplicate', 'missing', 'unknown', 'format'])
def test_incomplete_or_invalid_reference_refuses_to_score(replay_corpus, bad_gold):
    manifest, train, cache, gold = replay_corpus
    if bad_gold == 'duplicate':
        gold.append(gold[0])
    elif bad_gold == 'missing':
        gold.pop()
    elif bad_gold == 'unknown':
        gold[0]['id'] = 'not-in-corpus'
    else:
        gold[0]['answer'] = 'not a number'
    jsonl(train/'answers.jsonl', gold)
    with pytest.raises(ManifestError):
        verify_manifest(manifest, train, cache)


def test_missing_cache_is_reported_for_every_selected_question(replay_corpus):
    manifest, train, cache, _ = replay_corpus
    (cache/'shop'/'dong_hang.parquet').unlink()
    result = verify_manifest(manifest, train, cache)
    assert result['execution_errors'] == result['selected'] == 11
    assert result['compared'] == 0
    assert {r['execution_status'] for r in result['rows']} == {'cache_error'}
    assert verification_exit_code(result) == 1


def test_unexpected_exception_is_error_not_unanswerable(replay_corpus, monkeypatch):
    from queryplan import QueryExecutor
    def broken(*args, **kwargs):
        raise RuntimeError('synthetic implementation bug')
    monkeypatch.setattr(QueryExecutor, 'execute', broken)
    manifest, train, cache, _ = replay_corpus
    result = verify_manifest(manifest, train, cache)
    assert result['execution_errors'] == 11
    assert result['compared'] == result['abstained'] == 0
    assert {r['execution_status'] for r in result['rows']} == {'execution_error'}


def test_business_unanswerable_is_scored(replay_corpus):
    manifest, train, cache, gold = replay_corpus
    rows = [dict(id='a', business_id='shop', as_of_date='2026-03-04',
                 question='Doanh thu tháng 3/2025 bao nhiêu?')]
    jsonl(train/'questions.jsonl', rows)
    jsonl(train/'answers.jsonl', [dict(id='a', type='unanswerable')])
    write_json(manifest, build_manifest(train/'questions.jsonl', train/'rulebook.md'))
    result = verify_manifest(manifest, train, cache)
    assert result['matched'] == result['compared'] == 1
    assert result['rows'][0]['execution_status'] == 'unanswerable'
    assert verification_exit_code(result) == 0


def test_classified_data_error_stays_in_selected_denominator(replay_corpus):
    manifest, train, cache, _ = replay_corpus
    path = cache/'shop'/'dong_hang.parquet'
    lines = pd.read_parquet(path)
    lines['thanh_tien'] = lines['thanh_tien'].astype(float)
    lines.at[0, 'thanh_tien'] = float('nan')
    lines.to_parquet(path)
    result = verify_manifest(manifest, train, cache)
    row = result['rows'][0]
    assert (row['execution_status'], row['prediction']['type'], row['score']) == ('data_error', 'abstain', 'abstain')
    assert result['selected'] == 11
    assert result['selected'] == result['compared'] + result['abstained'] + result['execution_errors']


def test_no_selection_fails_explicitly(replay_corpus):
    manifest, train, cache, gold = replay_corpus
    jsonl(train/'questions.jsonl', [dict(id='a', business_id='shop', as_of_date='2026-03-04', question='unknown')])
    jsonl(train/'answers.jsonl', [dict(id='a', type='string', answer='x')])
    write_json(manifest, build_manifest(train/'questions.jsonl', train/'rulebook.md'))
    result = verify_manifest(manifest, train, cache)
    assert result['total'] == result['outside_selection'] == 1
    assert result['selected'] == result['compared'] == 0
    assert verification_exit_code(result) == 1
