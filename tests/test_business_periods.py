from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from business import DateRange, Periods, Rulebook, UnsupportedRule


def test_month_to_date_comparison_clamps_february(rules):
    p = Periods(rules, '2024-03-31')
    assert p.this_month() == DateRange('2024-03-01', '2024-03-31')
    assert p.previous_month(same_elapsed=True) == DateRange('2024-02-01', '2024-02-29')
    assert p.previous_month() == DateRange('2024-02-01', '2024-02-29')
    assert Periods(rules, '2024-03-05').previous_month(same_elapsed=True).end == date(2024, 2, 5)


def test_week_and_relative_days_cross_year(rules):
    p = Periods(rules, '2026-01-01')
    assert p.this_week() == DateRange('2025-12-29', '2026-01-01')
    assert p.previous_week() == DateRange('2025-12-22', '2025-12-28')
    assert p.last_days(3) == DateRange('2025-12-30', '2026-01-01')
    assert p.yesterday() == DateRange('2025-12-31', '2025-12-31')
    assert p.today() == DateRange('2026-01-01', '2026-01-01')
    assert p.year_to_date() == DateRange('2026-01-01', '2026-01-01')


def test_implicit_year_and_explicit_full_period(rules):
    p = Periods(rules, '2026-03-04')
    assert p.month(8) == DateRange('2025-08-01', '2025-08-31')
    assert p.month(3) == DateRange('2026-03-01', '2026-03-31')
    assert p.month(8, 2026) == DateRange('2026-08-01', '2026-08-31')
    assert p.quarter(4) == DateRange('2025-10-01', '2025-12-31')
    assert p.quarter(1) == DateRange('2026-01-01', '2026-03-31')


def test_tet_uses_supplied_calendar_and_equal_prior_window(rules, tmp_path):
    calendar = tmp_path / 'calendar.csv'
    calendar.write_text('date,lunar_day,lunar_month,lunar_year,lunar_leap\n'
                        '2026-02-10,23,12,2025,false\n'
                        '2026-02-26,10,1,2026,false\n'
                        '2026-03-26,10,1,2026,true\n', encoding='utf-8')
    p = Periods(rules, '2026-03-01', calendar)
    assert p.tet(2026) == DateRange('2026-02-10', '2026-02-26')
    assert p.before(p.tet(2026)) == DateRange('2026-01-24', '2026-02-09')
    with pytest.raises(ValueError, match='calendar'):
        p.tet(2027)


def test_changed_week_rule_is_not_silently_accepted(rules):
    changed = Rulebook.from_text(rules.text.replace('bắt đầu **thứ Hai**', 'bắt đầu **Chủ nhật**'))
    with pytest.raises(UnsupportedRule):
        Periods(changed, '2026-03-04').this_week()


@pytest.mark.parametrize('start,end', [('2026-03-05','2026-03-04'), ('bad','2026-03-04')])
def test_invalid_ranges_rejected(start, end):
    with pytest.raises(ValueError):
        DateRange(start, end)


def test_invalid_counts_and_missing_calendar(rules):
    p = Periods(rules, '2026-03-04')
    for n in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            p.last_days(n)
    with pytest.raises(ValueError):
        p.month(13)
    with pytest.raises(ValueError):
        p.quarter(0)
    with pytest.raises(ValueError, match='calendar'):
        p.tet(2026)


def test_duplicate_rule_labels_in_different_industries_are_scoped(rules):
    text = rules.text + '\n### Điện thoại\n| Bảo hành | theo số máy |\n### Sửa xe\n| Bảo hành | theo số phiếu |\n'
    parsed = Rulebook.from_text(text)
    assert Periods(parsed, '2026-03-04').this_week() == DateRange('2026-03-02','2026-03-04')
    with pytest.raises(UnsupportedRule):
        parsed.require('Bảo hành')


@pytest.mark.parametrize('method,value', [('month',8),('quarter',4)])
def test_reversed_implicit_year_rule_rejected(rules,method,value):
    changed=Rulebook.from_text(rules.text.replace('năm nay nếu không sau hôm nay, còn lại năm trước',
                                               'năm trước nếu không sau hôm nay, còn lại năm nay'))
    with pytest.raises(UnsupportedRule):
        getattr(Periods(changed,'2026-03-04'),method)(value)
