"""Calendar-relative comparisons preserve existing as_of-relative contracts."""
import pytest

from business import DateRange, Periods, Rulebook, UnsupportedRule
from queryplan import PlanValidationError, QueryExecutor, check_capability, validate_plan
from queryplan.resolution import resolve_period
from queryplan_fixtures import plan, period_spec
from test_business_sales import tables


@pytest.mark.parametrize('primary,kind,start,end', [
    (period_spec('month', month=1, year=2024), 'previous_calendar_month', '2023-12-01', '2023-12-31'),
    (period_spec('month', month=3, year=2024), 'previous_calendar_month', '2024-02-01', '2024-02-29'),
    (period_spec('month', month=12), 'previous_calendar_month', '2025-11-01', '2025-11-30'),
    (period_spec('quarter', quarter=1, year=2026), 'previous_calendar_quarter', '2025-10-01', '2025-12-31'),
    (period_spec('quarter', quarter=4), 'previous_calendar_quarter', '2025-07-01', '2025-09-30'),
])
def test_calendar_comparison_resolves_primary_year_then_moves_calendar(primary, kind, start, end, rules):
    raw = plan('revenue_growth', period=primary, comparison_period=period_spec(kind))
    normalized = validate_plan(raw)
    check_capability(normalized)
    periods = Periods(rules, '2026-03-04')
    main = resolve_period(primary, periods)
    assert resolve_period(normalized['comparison_period'], periods, main) == DateRange(start, end)


@pytest.mark.parametrize('primary,kind', [
    (period_spec('month', month=1, year=1), 'previous_calendar_month'),
    (period_spec('quarter', quarter=1, year=1), 'previous_calendar_quarter'),
])
def test_calendar_comparison_underflow_is_period_error_before_data(primary, kind, rules):
    result = QueryExecutor({}, rules, '2026-03-04').execute(
        plan('revenue_growth', period=primary, comparison_period=period_spec(kind)))
    assert (result.status, result.stage, result.answer.type) == ('period_error', 'period', 'abstain')


@pytest.mark.parametrize('primary,kind', [
    (period_spec('today'), 'previous_calendar_month'),
    (period_spec('this_month'), 'previous_calendar_month'),
    (period_spec('month', month=2), 'previous_calendar_quarter'),
    (period_spec('quarter', quarter=2), 'previous_calendar_month'),
])
def test_new_kinds_only_allow_corresponding_explicit_calendar_kind(primary, kind, rules):
    result = QueryExecutor({}, rules, '2026-03-04').execute(
        plan('revenue_growth', period=primary, comparison_period=period_spec(kind)))
    assert (result.status, result.stage) == ('unsupported_capability', 'capability')


def test_new_comparison_kind_not_allowed_as_primary_or_with_parameters():
    with pytest.raises(PlanValidationError):
        validate_plan(plan(period=period_spec('previous_calendar_month')))
    with pytest.raises(PlanValidationError):
        validate_plan(plan('revenue_growth', comparison_period=period_spec('previous_calendar_month', month=1)))


def test_fixed_vs_as_of_relative_and_old_relative_meaning_are_preserved(rules):
    periods = Periods(rules, '2026-03-04')
    for primary, comparison, expected in [
        (period_spec('date_range', start_date='2026-03-01', end_date='2026-03-01'),
         period_spec('yesterday'), DateRange('2026-03-03', '2026-03-03')),
        (period_spec('month', month=1, year=2024), period_spec('previous_month'),
         DateRange('2026-02-01', '2026-02-28')),
    ]:
        normalized = validate_plan(plan('revenue_growth', period=primary, comparison_period=comparison))
        check_capability(normalized)
        assert resolve_period(comparison, periods, resolve_period(primary, periods)) == expected


def test_calendar_helpers_still_require_caller_rulebook(rules):
    changed = Rulebook.from_text(rules.text.replace('cả tháng', 'một phần tháng'))
    with pytest.raises(UnsupportedRule):
        resolve_period(period_spec('previous_calendar_month'), Periods(changed, '2026-03-04'),
                       DateRange('2026-03-01', '2026-03-31'))


def test_executor_uses_whole_previous_calendar_month_not_same_elapsed(tables, rules):
    orders, lines = tables['don_hang'], tables['dong_hang']
    orders.loc[5] = orders.loc[0].copy()
    orders.loc[5, ['ma_don', 'ngay_dat', 'thoi_diem_dat']] = ['FEB', '2026-02-20', '2026-02-20 12:00:00']
    lines.loc[len(lines)] = ['FEB', 'P1', 'hang', 1, 10]
    result = QueryExecutor(tables, rules, '2026-03-04').execute(plan('revenue_growth',
        period=period_spec('month', month=3, year=2026),
        comparison_period=period_spec('previous_calendar_month')))
    assert (result.status, result.answer.type, result.answer.answer) == ('answered', 'percent', 1910)
