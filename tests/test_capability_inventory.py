"""Synthetic grammar and frozen-corpus checks; no competition rows or gold."""
import json

import pytest

from test_business_sales import tables
from verification.selection import select_question
from verification.manifest import ManifestError, build_manifest, validate_manifest


@pytest.mark.parametrize('text,operation', [
    ('Doanh thu tháng 3/2026 bao nhiêu?', 'revenue'),
    ('Có bao nhiêu đơn hàng hôm nay?', 'order_count'),
    ('Bao nhiêu đơn bị hủy tháng này?', 'cancelled_orders'),
    ('Tỷ lệ đơn hủy tháng này là bao nhiêu phần trăm?', 'cancellation_rate'),
    ('Giá trị trung bình một đơn tháng này là bao nhiêu?', 'average_order_value'),
    ('Bán được bao nhiêu ly tháng này?', 'quantity'),
    ('Top 2 mặt hàng theo doanh thu tháng này?', 'top_products'),
    ('Top 2 khách hàng theo số đơn tháng này?', 'top_customers'),
    ('Doanh thu tháng 3/2026 tăng bao nhiêu phần trăm so với tháng 2/2026?', 'revenue_growth'),
    ('Tỷ trọng doanh thu nhóm hàng "Đồ uống" tháng này là bao nhiêu?', 'revenue_share'),
])
def test_ten_operations_selected_from_question_only(text, operation):
    result = select_question(text)
    assert result['selection'] == 'selected'
    assert result['plan']['operation'] == operation


@pytest.mark.parametrize('text', [
    'Doanh thu tháng này trừ phí giao hàng bao nhiêu?',
    'Doanh thu tháng này và số đơn tháng này bao nhiêu?',
    'Doanh thu tháng này riêng khách mới bao nhiêu?',
    'Doanh thu bao nhiêu?',
    'Top 2 mặt hàng ít bán nhất tháng này?',
    'Doanh thu tháng 13/2026 bao nhiêu?',
    'Doanh thu tháng này hoặc tháng trước bao nhiêu?',
])
def test_unconsumed_or_ambiguous_scope_not_silently_dropped(text):
    result = select_question(text)
    assert result['selection'] == 'unparsed'
    assert result['reason']
    assert result['plan'] is None


def test_filter_mentions_keep_accents_and_unit_and_same_elapsed():
    result = select_question('Bán được bao nhiêu ly mặt hàng "CÀ PHÊ" tháng này?')
    assert result['plan']['filters']['product_mentions'] == ['CÀ PHÊ']
    assert result['plan']['filters']['unit_mention'] == 'ly'
    result = select_question('Doanh thu tháng này tăng bao nhiêu phần trăm so với tháng trước?')
    assert result['plan']['comparison_period']['kind'] == 'previous_month_same_elapsed'


def test_quantity_unit_preserves_accents_through_executor(tables, rules):
    from queryplan import QueryExecutor
    result = select_question('Bán được bao nhiêu phần tháng này?')
    assert result['plan']['filters']['unit_mention'] == 'phần'
    executed = QueryExecutor(tables, rules, '2026-03-04').execute(result['plan'])
    assert executed.status == 'answered'
    assert executed.answer.answer == 1


@pytest.mark.parametrize('comparison_scope', ['thanh toán "cod"', 'ca chiều'])
def test_filters_in_comparison_are_not_applied_to_both_periods(comparison_scope):
    text = ('Doanh thu kênh "online" tháng này tăng bao nhiêu phần trăm '
            f'so với tháng trước {comparison_scope}?')
    result = select_question(text)
    assert result['selection'] == 'unparsed'
    assert result['plan'] is None


@pytest.mark.parametrize('text,kind', [
    ('Doanh thu 7 ngày gần nhất bao nhiêu?', 'last_days'),
    ('Doanh thu quý 2/2026 bao nhiêu?', 'quarter'),
    ('Doanh thu từ ngày 2026-03-01 đến hết ngày 2026-03-04 bao nhiêu?', 'date_range'),
    ('Doanh thu Tết năm 2026 bao nhiêu?', 'tet'),
])
def test_period_shapes(text, kind):
    assert select_question(text)['plan']['period']['kind'] == kind


@pytest.fixture
def corpus(tmp_path, rules):
    questions = tmp_path / 'questions.jsonl'
    rows = [dict(id='q1', business_id='shop', as_of_date='2026-03-04',
                 question='Doanh thu tháng này bao nhiêu?'),
            dict(id='q2', business_id='shop', as_of_date='2026-03-04', question='Ngoài grammar')]
    questions.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows), encoding='utf-8')
    rulebook = tmp_path / 'rulebook.md'
    rulebook.write_text(rules.text, encoding='utf-8')
    return questions, rulebook


def test_inventory_needs_neither_gold_nor_cache_and_is_deterministic(corpus):
    questions, rules = corpus
    manifest = build_manifest(questions, rules)
    assert manifest == build_manifest(questions, rules)
    assert len(manifest['entries']) == 2
    assert [e['selection'] for e in manifest['entries']] == ['selected', 'unparsed']
    assert validate_manifest(manifest, questions, rules) == manifest['entries']
    (questions.parent / 'answers.jsonl').write_text('broken gold never read', encoding='utf-8')
    assert manifest == build_manifest(questions, rules)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'plan', 'version', 'questions', 'rulebook'])
def test_manifest_refuses_changed_corpus_or_payload(corpus, change):
    questions, rules = corpus
    manifest = build_manifest(questions, rules)
    if change == 'missing':
        manifest['entries'].pop()
    elif change == 'duplicate':
        manifest['entries'].append(manifest['entries'][0])
    elif change == 'plan':
        manifest['entries'][0]['plan']['operation'] = 'order_count'
    elif change == 'version':
        manifest['version'] = 'future'
    elif change == 'questions':
        questions.write_text(questions.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    else:
        rules.write_text(rules.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    with pytest.raises(ManifestError):
        validate_manifest(manifest, questions, rules)


def test_duplicate_question_ids_rejected(corpus):
    questions, rules = corpus
    first = questions.read_text(encoding='utf-8').splitlines()[0]
    questions.write_text(first + '\n' + first, encoding='utf-8')
    with pytest.raises(ManifestError, match='duplicate'):
        build_manifest(questions, rules)
