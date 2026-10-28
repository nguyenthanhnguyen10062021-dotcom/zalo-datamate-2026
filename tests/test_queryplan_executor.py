"""Execute real public business APIs on synthetic data; no model or gold."""
from copy import deepcopy
import unicodedata

import pandas as pd
import pytest

from business import Answer, DateRange, Filters, Periods, Rulebook, SalesMetrics
from queryplan_fixtures import period_spec, plan
from test_business_sales import tables  # Shared synthetic fixture, no local data.


@pytest.fixture
def executor_class():
    import queryplan
    assert hasattr(queryplan, 'QueryExecutor'), 'QueryExecutor is not implemented'
    return queryplan.QueryExecutor


@pytest.mark.parametrize('operation,mentions,ranking,expected,direct_filters,unit', [
    ('revenue', {}, None, 201, Filters(), None),
    ('order_count', {}, None, 2, Filters(), None),
    ('cancelled_orders', {}, None, 1, Filters(), None),
    ('cancellation_rate', {'channel_mention': 'ONLINE'}, None, 33.33, Filters(channel='online'), None),
    ('average_order_value', {}, None, 101, Filters(), None),
    ('quantity', {'unit_mention': ' LY '}, None, 2, Filters(), 'ly'),
    ('top_products', {}, {'k': 2, 'metric': 'revenue'}, ['Cà phê', 'Trà'], Filters(), None),
    ('top_customers', {'customer_group_mention': 'vip'}, {'k': 2, 'metric': 'orders'},
     ['Lan', 'Lan'], Filters(customer_group='VIP'), None),
    ('revenue_share', {'product_group_mention': 'đồ uống'}, None, 84.58,
     Filters(product_group='Đồ uống'), None),
    ('revenue_growth', {}, None, -0.99, Filters(), None),
])
def test_ten_operations_match_literal_and_direct_api(executor_class, tables, rules,
        operation, mentions, ranking, expected, direct_filters, unit):
    raw = plan(operation)
    raw['filters'].update(mentions)
    raw['ranking'] = ranking
    selected = DateRange('2026-03-01', '2026-03-04')
    engine = SalesMetrics(tables, rules, '2026-03-04')
    kwargs = dict(filters=direct_filters)
    if operation == 'quantity':
        kwargs['unit'] = unit
    if ranking:
        kwargs.update(ranking)
    if operation == 'revenue_growth':
        raw['period'] = period_spec('date_range', start_date='2026-03-02', end_date='2026-03-02')
        raw['comparison_period'] = period_spec('date_range', start_date='2026-03-01', end_date='2026-03-01')
        selected = DateRange('2026-03-02', '2026-03-02')
        kwargs['comparison'] = DateRange('2026-03-01', '2026-03-01')
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert result.status == 'answered'
    assert result.stage == 'dispatch'
    assert result.answer.answer == expected
    assert result.answer == getattr(engine, operation)(selected, **kwargs)


def test_product_names_resolve_with_nfc_case_and_spaces(executor_class, tables, rules):
    raw = plan()
    raw['filters']['product_mentions'] = [unicodedata.normalize('NFD', '  CÀ   PHÊ ')]
    assert executor_class(tables, rules, '2026-03-04').execute(raw).answer.answer == 90


@pytest.mark.parametrize('field,value', [('product_mentions', ['Không biết']),
    ('channel_mention', 'mystery'), ('payment_mention', 'mystery'),
    ('customer_group_mention', 'mystery'), ('product_group_mention', 'mystery'),
    ('unit_mention', 'thùng')])
def test_unknown_mentions_abstain_instead_of_zero_or_unanswerable(executor_class, tables, rules, field, value):
    raw = plan('quantity' if field == 'unit_mention' else 'revenue')
    raw['filters'][field] = value
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert (result.status, result.stage, result.answer.type) == ('unresolved_entity', 'resolve', 'abstain')


def test_duplicate_product_name_is_ambiguous_not_union(executor_class, tables, rules):
    tables['mat_hang'].loc[4] = ['P3', 'Cà phê', 'Đồ uống', 'chai']
    raw = plan()
    raw['filters']['product_mentions'] = ['Cà phê']
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert result.status == 'ambiguous_entity'
    assert result.answer.type == 'abstain'


def test_normalized_label_collision_does_not_drop_rows(executor_class, tables, rules):
    tables['don_hang'].loc[2, 'kenh_ban'] = ' ONLINE '
    raw = plan('cancellation_rate')
    raw['filters']['channel_mention'] = 'online'
    assert executor_class(tables, rules, '2026-03-04').execute(raw).status == 'ambiguous_entity'


def test_future_only_label_is_not_used_to_resolve(executor_class, tables, rules):
    tables['don_hang'].loc[4, 'kenh_ban'] = 'future_channel'
    raw = plan()
    raw['filters']['channel_mention'] = 'future_channel'
    assert executor_class(tables, rules, '2026-03-04').execute(raw).status == 'unresolved_entity'


def test_known_label_outside_query_period_still_returns_zero(executor_class, tables, rules):
    raw = plan(period=period_spec('month', month=2))
    raw['filters']['channel_mention'] = 'online'
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert result.status == 'answered'
    assert result.answer.answer == 0


@pytest.mark.parametrize('column,field', [('kenh_ban', 'channel_mention'), ('hinh_thuc_tt', 'payment_mention')])
def test_no_label_information_is_unanswerable_with_resolve_stage(executor_class, tables, rules, column, field):
    tables['don_hang'][column] = None
    raw = plan()
    raw['filters'][field] = 'label'
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert (result.status, result.stage, result.answer.type) == ('unanswerable', 'resolve', 'unanswerable')


@pytest.mark.parametrize('operation,changes', [
    ('revenue', {'unit_mention': 'ly'}), ('cancellation_rate', {'product_mentions': ['Trà']}),
    ('top_customers', {'product_group_mention': 'Đồ uống'}),
])
def test_unsupported_filter_capability_has_distinct_status(executor_class, tables, rules, operation, changes):
    raw = plan(operation)
    raw['filters'].update(changes)
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert (result.status, result.stage, result.answer.type) == ('unsupported_capability', 'capability', 'abstain')


@pytest.mark.parametrize('operation,metric', [('top_products', 'orders'), ('top_customers', 'quantity')])
def test_ranking_metric_capability(executor_class, tables, rules, operation, metric):
    result = executor_class(tables, rules, '2026-03-04').execute(plan(operation, ranking=dict(k=2, metric=metric)))
    assert result.status == 'unsupported_capability'


def test_invalid_and_unsupported_plans_need_no_data(executor_class, rules):
    executor = executor_class({}, rules, '2026-03-04')
    assert executor.execute({}).status == 'invalid_plan'
    raw = dict(version='1.0', status='unsupported', unsupported_reason='unsupported_domain',
               operation=None, expected_type=None, period=None, comparison_period=None, filters=None, ranking=None)
    result = executor.execute(raw)
    assert result.status == 'unsupported_plan'
    assert result.answer.type == 'abstain'


def test_data_errors_keep_dependency_scope(executor_class, tables, rules):
    tables['dong_hang'].loc[7] = ['ORPHAN', 'P1', 'hang', 1, 900]
    executor = executor_class(tables, rules, '2026-03-04')
    assert executor.execute(plan('order_count')).answer.answer == 2
    result = executor.execute(plan())
    assert (result.status, result.answer.type) == ('data_error', 'abstain')


def test_bad_catalog_not_validated_by_order_count_but_rejected_when_resolving(executor_class, tables, rules):
    tables['mat_hang'].loc[1, 'ma_hang'] = 'P1'
    executor = executor_class(tables, rules, '2026-03-04')
    assert executor.execute(plan('order_count')).answer.answer == 2
    raw = plan()
    raw['filters']['product_mentions'] = ['Trà']
    assert executor.execute(raw).status == 'data_error'


@pytest.mark.parametrize('table,column,field,operation', [
    ('don_hang', 'kenh_ban', 'channel_mention', 'revenue'),
    ('mat_hang', 'ten_hang', 'product_mentions', 'revenue'),
    ('mat_hang', 'don_vi_co_ban', 'unit_mention', 'quantity'),
])
@pytest.mark.parametrize('bad_label', [['label'], {'name': 'label'}])
def test_non_string_labels_are_data_errors_when_resolved(
        executor_class, tables, rules, table, column, field, operation, bad_label):
    tables[table][column] = tables[table][column].astype(object)
    tables[table].at[0, column] = bad_label
    executor = executor_class(tables, rules, '2026-03-04')
    assert executor.execute(plan('order_count')).answer.answer == 2
    raw = plan(operation)
    raw['filters'][field] = ['label'] if field == 'product_mentions' else 'label'
    result = executor.execute(raw)
    assert (result.status, result.stage, result.answer.type) == ('data_error', 'resolve', 'abstain')
    assert column in result.answer.reason


def test_unsupported_rule_is_not_unanswerable(executor_class, tables, rules):
    changed = Rulebook.from_text(rules.text.replace('không gồm phí giao hàng', 'gồm phí giao hàng'))
    result = executor_class(tables, changed, '2026-03-04').execute(plan())
    assert (result.status, result.answer.type) == ('unsupported_rule', 'abstain')


def test_unanswerable_from_business_preserved(executor_class, tables, rules):
    raw = plan(period=period_spec('date_range', start_date='2025-01-01', end_date='2025-01-31'))
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert (result.status, result.stage, result.answer.type) == ('unanswerable', 'dispatch', 'unanswerable')


def test_growth_same_elapsed_default_and_explicit_full_month(executor_class, tables, rules):
    orders = tables['don_hang']
    lines = tables['dong_hang']
    for i, day, amount in [(5, '2026-02-02', 10), (6, '2026-02-20', 390)]:
        orders.loc[i] = orders.loc[0].copy()
        orders.loc[i, ['ma_don', 'ngay_dat', 'thoi_diem_dat', 'tong_tien_hang']] = [f'B{i}', day, day+' 12:00:00', amount]
        lines.loc[len(lines)] = [f'B{i}', 'P1', 'hang', 1, amount]
    executor = executor_class(tables, rules, '2026-03-04')
    assert executor.execute(plan('revenue_growth')).answer.answer == 1910
    raw = plan('revenue_growth', comparison_period=period_spec('previous_month'))
    assert executor.execute(raw).answer.answer == -49.75


@pytest.mark.parametrize('comparison', [period_spec('before_period'), period_spec('previous_month_same_elapsed')])
def test_comparison_scope_restrictions(executor_class, tables, rules, comparison):
    raw = plan('revenue_growth', period=period_spec('today'), comparison_period=comparison)
    assert executor_class(tables, rules, '2026-03-04').execute(raw).status == 'unsupported_capability'


def test_calendar_required_and_malformed_are_period_errors(executor_class, tables, rules, tmp_path):
    raw = plan(period=period_spec('tet', year=2026))
    result = executor_class(tables, rules, '2026-03-04').execute(raw)
    assert result.status == 'period_error'
    calendar = tmp_path / 'calendar.csv'
    calendar.write_text('wrong_header\nvalue\n', encoding='utf-8')
    assert executor_class(tables, rules, '2026-03-04', calendar).execute(raw).status == 'period_error'
    calendar.write_text('date,lunar_year,lunar_month,lunar_day,lunar_leap\n'
                        '2026-02-10,2025,12,23,false\n2026-02-26,2026,1,10,false\n', encoding='utf-8')
    raw = plan('revenue_growth', period=period_spec('tet', year=2026),
               comparison_period=period_spec('before_period'))
    # Both synthetic periods contain no orders; baseline=0 is business unanswerable.
    result = executor_class(tables, rules, '2026-03-04', calendar).execute(raw)
    assert (result.status, result.stage) == ('unanswerable', 'dispatch')


@pytest.mark.parametrize('spec,start,end', [
    (period_spec('today'), '2026-03-04', '2026-03-04'),
    (period_spec('yesterday'), '2026-03-03', '2026-03-03'),
    (period_spec('last_days', n=3), '2026-03-02', '2026-03-04'),
    (period_spec('this_week'), '2026-03-02', '2026-03-04'),
    (period_spec('previous_week'), '2026-02-23', '2026-03-01'),
    (period_spec('this_month'), '2026-03-01', '2026-03-04'),
    (period_spec('previous_month'), '2026-02-01', '2026-02-28'),
    (period_spec('previous_month_same_elapsed'), '2026-02-01', '2026-02-04'),
    (period_spec('month', month=12), '2025-12-01', '2025-12-31'),
    (period_spec('quarter', quarter=4), '2025-10-01', '2025-12-31'),
    (period_spec('year_to_date'), '2026-01-01', '2026-03-04'),
    (period_spec('date_range', start_date='2026-02-01', end_date='2026-03-01'), '2026-02-01', '2026-03-01'),
])
def test_period_dispatch_has_correct_endpoints(executor_class, rules, spec, start, end):
    from queryplan.resolution import resolve_period
    assert resolve_period(spec, Periods(rules, '2026-03-04')) == DateRange(start, end)


def test_partial_period_and_inputs_unchanged(executor_class, tables, rules):
    before = deepcopy(tables)
    raw = plan(period=period_spec('date_range', start_date='2025-12-01', end_date='2026-03-02'))
    raw_before = deepcopy(raw)
    executor = executor_class(tables, rules, '2026-03-04')
    assert executor.execute(raw).answer.answer == 201
    assert raw == raw_before
    for key in ('don_hang', 'dong_hang', 'mat_hang'):
        pd.testing.assert_frame_equal(tables[key], before[key])


def test_unexpected_failure_and_type_mismatch_are_not_hidden(executor_class, tables, rules, monkeypatch):
    executor = executor_class(tables, rules, '2026-03-04')
    def broken(*args, **kwargs):
        raise RuntimeError('implementation bug')
    monkeypatch.setattr(SalesMetrics, 'revenue', broken)
    with pytest.raises(RuntimeError, match='implementation bug'):
        executor.execute(plan())
    monkeypatch.setattr(SalesMetrics, 'revenue', lambda *a, **kw: Answer('list', []))
    with pytest.raises(RuntimeError, match='type'):
        executor.execute(plan())


@pytest.mark.parametrize('error', [KeyError, ValueError, RuntimeError])
def test_period_implementation_exceptions_propagate(executor_class, tables, rules, monkeypatch, error):
    def broken(*args):
        raise error('implementation_bug')
    monkeypatch.setattr(Periods, 'today', broken)
    with pytest.raises(error, match='implementation_bug'):
        executor_class(tables, rules, '2026-03-04').execute(plan(period=period_spec('today')))


@pytest.mark.parametrize('rows', [
    '2026-02-10,2025,12,23\n',  # Missing leap cell, not a programming exception.
    '2026-02-10,2025,12,23,maybe\n',
    '2026-02-10,not_a_year,12,23,false\n',
    '2026-02-31,2025,12,23,false\n2026-02-26,2026,1,10,false\n',
    '2026-02-10,2025,12,23,false\n',  # Missing endpoint.
    '2026-02-10,2025,12,23,false\n2026-02-10,2025,12,23,false\n2026-02-26,2026,1,10,false\n',
])
def test_calendar_input_errors_classified_at_adapter(executor_class, tables, rules, tmp_path, rows):
    calendar = tmp_path / 'calendar.csv'
    calendar.write_text('date,lunar_year,lunar_month,lunar_day,lunar_leap\n' + rows, encoding='utf-8')
    result = executor_class(tables, rules, '2026-03-04', calendar).execute(plan(period=period_spec('tet', year=2026)))
    assert (result.status, result.stage, result.answer.type) == ('period_error', 'period', 'abstain')


@pytest.mark.parametrize('spec,as_of', [
    (period_spec('last_days', n=10**30), '2026-03-04'),
    (period_spec('yesterday'), '0001-01-01'),
    (period_spec('previous_month'), '0001-01-01'),
    (period_spec('previous_week'), '0001-01-01'),
    (period_spec('month', month=12), '0001-01-01'),
    (period_spec('quarter', quarter=4), '0001-01-01'),
])
def test_unrepresentable_period_is_input_error(executor_class, tables, rules, spec, as_of):
    result = executor_class(tables, rules, as_of).execute(plan(period=spec))
    assert result.status == 'period_error'
