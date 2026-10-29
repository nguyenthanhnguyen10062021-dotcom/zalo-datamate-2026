"""Resolve validated periods and exact normalized mentions against canonical data."""
from dataclasses import dataclass
from datetime import date, timedelta
import csv
import unicodedata

import pandas as pd

from business import DataError, DateRange, Filters, Periods


class ResolutionError(LookupError):
    """Information exists, but the requested label is unknown."""


class AmbiguousEntityError(ResolutionError):
    """Several distinct entities/labels match; do not choose one silently."""


class MissingInformation(LookupError):
    """The input lacks the type of information required for resolution."""


class PeriodResolutionError(ValueError):
    """Proven calendar/input range error, distinct from implementation exceptions."""


def _key(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())


def _labels(frame, column):
    if column not in frame or not frame[column].notna().any():
        raise MissingInformation(f'Không ghi thông tin {column}')
    values = frame[column].dropna()
    if any(not isinstance(v, str) or not _key(v) for v in values):
        raise DataError(f'Nhãn {column} sai kiểu/rỗng')
    return values.unique().tolist()


def _label(frame, column, mention, *, unit=False):
    values = _labels(frame, column)
    matches = [v for v in values if _key(v) == _key(mention)]
    if not matches:
        raise ResolutionError(f'Không khớp {column}: {mention}')
    # quantity itself normalizes base units; other business filters compare raw strings.
    if len(matches) > 1 and not unit:
        raise AmbiguousEntityError(f'Nhiều nhãn {column} cùng cách viết chuẩn hóa: {mention}')
    return _key(matches[0]) if unit else matches[0]


def _catalog(products):
    if ('ma_hang' not in products or products['ma_hang'].isna().any()
            or products['ma_hang'].duplicated().any()):
        raise DataError('Khóa ma_hang thiếu/trùng trong bảng chuẩn')


@dataclass(frozen=True)
class ResolvedFilters:
    filters: Filters
    unit: str | None


def resolve_filters(spec: dict, tables: dict, as_of_date) -> ResolvedFilters:
    """No fuzzy aliases. Only inspect catalogs/columns needed by supplied mentions.

    Caller must validate the canonical table envelope/order dates with SalesMetrics first.
    """
    products, orders = tables['mat_hang'], tables['don_hang']
    product_ids = None
    if any(spec[k] is not None for k in ('product_mentions', 'product_group_mention', 'unit_mention')):
        _catalog(products)
    if spec['product_mentions'] is not None:
        _labels(products, 'ten_hang')
        if products['ten_hang'].isna().any():
            raise DataError('Một số mặt hàng thiếu tên để resolve')
        keys = products['ten_hang'].map(_key)
        ids = []
        for mention in spec['product_mentions']:
            matches = products.loc[keys.eq(_key(mention)), 'ma_hang'].tolist()
            if not matches:
                raise ResolutionError(f'Không khớp tên mặt hàng: {mention}')
            if len(matches) != 1:
                raise AmbiguousEntityError(f'Nhiều mã hàng cùng tên: {mention}')
            if matches[0] not in ids:
                ids.append(matches[0])
        product_ids = tuple(ids)
    # Future transactions have not happened at the question's as_of_date.
    known_orders = orders[pd.to_datetime(orders['ngay_dat']).dt.normalize() <= pd.Timestamp(as_of_date)]
    resolved = dict(product_ids=product_ids, shift=spec['shift'])
    for source, column, field, frame in (
        ('product_group_mention', 'nhom_hang', 'product_group', products),
        ('channel_mention', 'kenh_ban', 'channel', known_orders),
        ('payment_mention', 'hinh_thuc_tt', 'payment', known_orders),
        ('customer_group_mention', 'nhom_khach', 'customer_group', known_orders),
    ):
        resolved[field] = _label(frame, column, spec[source]) if spec[source] is not None else None
    unit = _label(products, 'don_vi_co_ban', spec['unit_mention'], unit=True) if spec['unit_mention'] is not None else None
    return ResolvedFilters(Filters(**resolved), unit)


def _validate_tet_calendar(periods, year):
    """Validate external CSV at its input boundary, before calling the business API."""
    if periods.calendar_path is None:
        raise PeriodResolutionError('calendar_path is required for Tet')
    endpoints = {(year - 1, 12, 23): [], (year, 1, 10): []}
    fields = ('date', 'lunar_year', 'lunar_month', 'lunar_day', 'lunar_leap')
    try:
        with periods.calendar_path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, strict=True)
            if (reader.fieldnames is None or not set(fields).issubset(reader.fieldnames)
                    or len(reader.fieldnames) != len(set(reader.fieldnames))):
                raise PeriodResolutionError('calendar: missing/duplicate required headers')
            for row in reader:
                if any(not isinstance(row[f], str) or not row[f].strip() for f in fields):
                    raise PeriodResolutionError('calendar: missing required cell')
                leap = row['lunar_leap'].lower()
                if leap not in ('false', '0', 'true', '1'):
                    raise PeriodResolutionError('calendar: invalid lunar_leap')
                if leap in ('false', '0'):
                    key = tuple(int(row[f]) for f in fields[1:4])
                    if key in endpoints:
                        endpoints[key].append(date.fromisoformat(row['date']))
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        # Only external reading/parsing lives inside this boundary; no Periods calls.
        raise PeriodResolutionError(f'calendar: {exc}') from exc
    if any(len(values) != 1 for values in endpoints.values()):
        raise PeriodResolutionError(f'calendar: missing/ambiguous Tet endpoints for {year}')
    if endpoints[(year - 1, 12, 23)][0] > endpoints[(year, 1, 10)][0]:
        raise PeriodResolutionError('calendar: reversed Tet endpoints')


def _period_bounds(spec, periods, primary):
    """Check representable date bounds explicitly rather than catching API bugs."""
    kind, today = spec['kind'], periods.as_of
    ordinal = today.toordinal()
    if (kind == 'last_days' and spec['n'] > ordinal
            or kind == 'yesterday' and ordinal == 1
            or kind == 'previous_week' and ordinal - today.weekday() - 7 < 1
            or kind in ('previous_month', 'previous_month_same_elapsed') and today.year == 1 and today.month == 1):
        raise PeriodResolutionError('period exceeds representable calendar bounds')
    if kind in ('month', 'quarter') and spec['year'] is None and today.year == 1:
        month = spec['month'] if kind == 'month' else 3 * (spec['quarter'] - 1) + 1
        if month > today.month:
            raise PeriodResolutionError('implicit year would precede year 1')
    if kind == 'before_period' and primary is not None:
        if primary.start.toordinal() <= (primary.end - primary.start).days + 1:
            raise PeriodResolutionError('comparison would precede year 1')
    if (kind in ('previous_calendar_month', 'previous_calendar_quarter') and primary is not None
            and primary.start.year == 1 and primary.start.month == 1):
        raise PeriodResolutionError('calendar comparison would precede year 1')


def resolve_period(spec: dict, periods: Periods, primary: DateRange | None = None) -> DateRange:
    """Map a validated period spec onto the public Periods API."""
    kind = spec['kind']
    _period_bounds(spec, periods, primary)
    if kind == 'date_range':
        return DateRange(spec['start_date'], spec['end_date'])
    if kind == 'last_days':
        return periods.last_days(spec['n'])
    if kind == 'month':
        return periods.month(spec['month'], spec['year'])
    if kind == 'quarter':
        return periods.quarter(spec['quarter'], spec['year'])
    if kind == 'tet':
        _validate_tet_calendar(periods, spec['year'])
        return periods.tet(spec['year'])
    if kind == 'before_period':
        if primary is None:
            raise ValueError('before_period requires primary period')
        return periods.before(primary)
    if kind == 'previous_month_same_elapsed':
        return periods.previous_month(same_elapsed=True)
    if kind in ('previous_calendar_month', 'previous_calendar_quarter'):
        if primary is None:
            raise ValueError(f'{kind} requires primary calendar period')
        previous_end = primary.start - timedelta(days=1)
        if kind == 'previous_calendar_month':
            return periods.month(previous_end.month, previous_end.year)
        return periods.quarter((previous_end.month - 1) // 3 + 1, previous_end.year)
    simple = {name: getattr(periods, name) for name in (
        'today', 'yesterday', 'this_week', 'previous_week', 'this_month',
        'previous_month', 'year_to_date')}
    return simple[kind]()
