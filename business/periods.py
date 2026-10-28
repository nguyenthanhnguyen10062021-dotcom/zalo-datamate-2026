"""Explicit date-period API. Natural-language question parsing belongs upstream."""
from calendar import monthrange
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .rules import Rulebook


def as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else date.fromisoformat(value)


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self):
        object.__setattr__(self, 'start', as_date(self.start))
        object.__setattr__(self, 'end', as_date(self.end))
        if self.start > self.end:
            raise ValueError('start must not be after end')


class Periods:
    def __init__(self, rules: Rulebook, as_of_date, calendar_path: str | Path | None = None):
        self.rules, self.as_of = rules, as_date(as_of_date)
        self.calendar_path = Path(calendar_path) if calendar_path is not None else None

    def today(self):
        return DateRange(self.as_of, self.as_of)

    def yesterday(self):
        day = self.as_of - timedelta(days=1)
        return DateRange(day, day)

    def last_days(self, n: int):
        if type(n) is not int or n <= 0:
            raise ValueError('n must be a positive integer')
        self.rules.require('N ngày gần nhất', 'ke ca hom nay', 'ngay cuoi la hom nay')
        return DateRange(self.as_of - timedelta(days=n-1), self.as_of)

    def this_week(self):
        self.rules.require('Tuần', 'bat dau thu Hai', 'den het hom nay')
        return DateRange(self.as_of - timedelta(days=self.as_of.weekday()), self.as_of)

    def previous_week(self):
        self.rules.require('Tuần', 'bat dau thu Hai', 'thu Hai den Chu nhat')
        end = self.this_week().start - timedelta(days=1)
        return DateRange(end - timedelta(days=6), end)

    def this_month(self):
        self.rules.require('Tháng này', 'tu ngay 1 den het hom nay')
        return DateRange(self.as_of.replace(day=1), self.as_of)

    def previous_month(self, same_elapsed: bool = False):
        end = self.as_of.replace(day=1) - timedelta(days=1)
        if same_elapsed:
            self.rules.require('Tháng này', 'cung so ngay', 'thang truoc')
            end = end.replace(day=min(end.day, self.as_of.day))
        return DateRange(self.month(end.month, end.year).start, end)

    def month(self, month: int, year: int | None = None):
        if type(month) is not int or not 1 <= month <= 12:
            raise ValueError('month must be 1..12')
        if year is None:
            self.rules.implicit_year()
            year = self.as_of.year - (month > self.as_of.month)
        self.rules.require('Tháng M/Y', 'ca thang')
        return DateRange(date(year, month, 1), date(year, month, monthrange(year, month)[1]))

    def quarter(self, quarter: int, year: int | None = None):
        if type(quarter) is not int or not 1 <= quarter <= 4:
            raise ValueError('quarter must be 1..4')
        self.rules.require('Tháng M, quý Q không ghi năm', 'quy theo duong lich', '3 thang')
        month = 3 * (quarter - 1) + 1
        if year is None:
            self.rules.implicit_year()
            year = self.as_of.year - (month > self.as_of.month)
        return DateRange(date(year, month, 1), self.month(month + 2, year).end)

    def year_to_date(self):
        self.rules.require('Từ đầu năm, từ đầu năm tới nay', '01/01', 'den het hom nay')
        return DateRange(date(self.as_of.year, 1, 1), self.as_of)

    def tet(self, year: int):
        self.rules.require('Tết năm Y, dịp Tết, mùa Tết', '23 thang Chap', 'mung 10 thang Gieng', 'calendar.csv')
        if self.calendar_path is None:
            raise ValueError('calendar_path is required for Tet')
        matches = {(year-1, 12, 23): [], (year, 1, 10): []}
        with self.calendar_path.open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                if row['lunar_leap'].lower() not in ('false', '0'):
                    continue
                key = tuple(int(row[c]) for c in ('lunar_year','lunar_month','lunar_day'))
                if key in matches:
                    matches[key].append(row['date'])
        if any(len(v) != 1 for v in matches.values()):
            raise ValueError(f'calendar has missing/ambiguous Tet endpoints for {year}')
        return DateRange(matches[(year-1,12,23)][0], matches[(year,1,10)][0])

    def before(self, period: DateRange):
        self.rules.require('Tết năm Y, dịp Tết, mùa Tết', 'cung so ngay ngay truoc')
        return DateRange(period.start - (period.end - period.start) - timedelta(days=1),
                         period.start - timedelta(days=1))
