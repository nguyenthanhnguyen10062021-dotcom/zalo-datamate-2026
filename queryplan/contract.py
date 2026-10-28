"""Strict v1 JSON contract, independent of data, models and business execution."""
from copy import deepcopy
from datetime import date
import math
import re


OPERATIONS = {
    'revenue': 'number', 'order_count': 'number', 'cancelled_orders': 'number',
    'average_order_value': 'number', 'quantity': 'number',
    'cancellation_rate': 'percent', 'revenue_growth': 'percent', 'revenue_share': 'percent',
    'top_products': 'list', 'top_customers': 'list',
}
TOP_FIELDS = ('version', 'status', 'unsupported_reason', 'operation', 'expected_type',
              'period', 'comparison_period', 'filters', 'ranking')
PERIOD_FIELDS = ('kind', 'n', 'month', 'quarter', 'year', 'start_date', 'end_date')
FILTER_FIELDS = ('product_mentions', 'product_group_mention', 'channel_mention',
                 'payment_mention', 'customer_group_mention', 'shift', 'unit_mention')
PERIOD_KINDS = ('today', 'yesterday', 'last_days', 'this_week', 'previous_week',
                'this_month', 'previous_month', 'previous_month_same_elapsed',
                'month', 'quarter', 'year_to_date', 'tet', 'date_range')
COMPARISON_KINDS = ('yesterday', 'previous_week', 'previous_month',
                    'previous_month_same_elapsed', 'month', 'quarter', 'tet',
                    'date_range', 'before_period')
UNSUPPORTED_REASONS = ('unsupported_domain', 'unsupported_answer_type',
    'unsupported_comparison_or_denominator', 'ambiguous_question', 'unparseable_time')


class PlanValidationError(ValueError):
    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(message)


def _require(condition, stage, message):
    if not condition:
        raise PlanValidationError(stage, message)


def _object(value, fields, path):
    _require(type(value) is dict, 'structure', f'{path}: expected object')
    _require(set(value) == set(fields), 'structure', f'{path}: missing or unknown fields')


def _integer(value, path):
    if value is None or type(value) is int:
        return value
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value)
    raise PlanValidationError('normalize', f'{path}: expected finite integer, not bool/string/fraction')


def _mention(value, path):
    _require(type(value) is str and bool(value.strip()), 'normalize', f'{path}: empty/non-string mention')
    return value.strip()


def _normalize(raw):
    _require(type(raw) is dict, 'structure', 'plan: expected object')
    plan = deepcopy(raw)
    for name in ('period', 'comparison_period', 'ranking'):
        spec = plan.get(name)
        if type(spec) is dict:
            for field in (('k',) if name == 'ranking' else ('n', 'month', 'quarter', 'year')):
                if field in spec:
                    spec[field] = _integer(spec[field], f'{name}.{field}')
    filters = plan.get('filters')
    if type(filters) is dict:
        mentions = filters.get('product_mentions')
        if type(mentions) is list:
            filters['product_mentions'] = [_mention(v, 'product_mentions') for v in mentions] or None
        for field in FILTER_FIELDS[1:-2] + ('unit_mention',):
            if filters.get(field) is not None:
                filters[field] = _mention(filters[field], field)
    return plan


def _period_structure(spec, comparison=False):
    _object(spec, PERIOD_FIELDS, 'comparison_period' if comparison else 'period')
    _require(spec['kind'] in (COMPARISON_KINDS if comparison else PERIOD_KINDS),
             'structure', 'period.kind: unknown kind')
    for field, low, high in (('n', 1, None), ('month', 1, 12), ('quarter', 1, 4), ('year', 1, 9999)):
        value = spec[field]
        _require(value is None or type(value) is int and value >= low and (high is None or value <= high),
                 'structure', f'period.{field}: invalid integer/range')
    for field in ('start_date', 'end_date'):
        value = spec[field]
        _require(value is None or type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value),
                 'structure', f'period.{field}: expected YYYY-MM-DD')


def _structure(plan):
    _object(plan, TOP_FIELDS, 'plan')
    _require(plan['version'] == '1.0', 'structure', 'version must be 1.0')
    for field, allowed in (('status', ('supported', 'unsupported')),
        ('unsupported_reason', (*UNSUPPORTED_REASONS, None)),
        ('operation', (*OPERATIONS, None)), ('expected_type', ('number', 'percent', 'list', None))):
        _require(plan[field] in allowed, 'structure', f'{field}: unknown value')
    for name in ('period', 'comparison_period'):
        if plan[name] is not None:
            _period_structure(plan[name], comparison=name == 'comparison_period')
    filters = plan['filters']
    if filters is not None:
        _object(filters, FILTER_FIELDS, 'filters')
        mentions = filters['product_mentions']
        _require(mentions is None or type(mentions) is list and bool(mentions)
                 and all(type(v) is str and bool(v.strip()) for v in mentions),
                 'structure', 'product_mentions: expected nonempty list or null')
        _require(filters['shift'] in ('sang', 'chieu', None), 'structure', 'shift: unknown value')
    ranking = plan['ranking']
    if ranking is not None:
        _object(ranking, ('k', 'metric'), 'ranking')
        _require(type(ranking['k']) is int and ranking['k'] > 0, 'structure', 'ranking.k must be positive')
        _require(ranking['metric'] in ('quantity', 'revenue', 'orders'), 'structure', 'ranking.metric: unknown')


def _period_semantics(spec):
    kind = spec['kind']
    allowed = {'last_days': ('n',), 'month': ('month', 'year'), 'quarter': ('quarter', 'year'),
               'tet': ('year',), 'date_range': ('start_date', 'end_date')}.get(kind, ())
    required = {'month': ('month',), 'quarter': ('quarter',)}.get(kind, allowed)
    _require(all(spec[field] is not None for field in required), 'semantic', f'{kind}: missing parameters')
    _require(all(spec[field] is None for field in PERIOD_FIELDS[1:] if field not in allowed),
             'semantic', f'{kind}: unused parameters must be null')
    if kind == 'date_range':
        try:
            start, end = date.fromisoformat(spec['start_date']), date.fromisoformat(spec['end_date'])
        except ValueError as exc:
            raise PlanValidationError('semantic', 'date_range: invalid calendar date') from exc
        _require(start <= end, 'semantic', 'date_range: reversed endpoints')


def _semantics(plan):
    if plan['status'] == 'unsupported':
        _require(plan['unsupported_reason'] is not None and all(plan[k] is None for k in TOP_FIELDS[3:]),
                 'semantic', 'unsupported plan requires reason and null executable fields')
        return
    _require(plan['unsupported_reason'] is None and all(plan[k] is not None for k in
             ('operation', 'expected_type', 'period', 'filters')), 'semantic', 'supported plan is incomplete')
    op = plan['operation']
    _require(plan['expected_type'] == OPERATIONS[op], 'semantic', 'expected_type conflicts with operation')
    _period_semantics(plan['period'])
    comparison = plan['comparison_period']
    if comparison is not None:
        _require(op == 'revenue_growth', 'semantic', 'comparison only supported for revenue_growth')
        _period_semantics(comparison)
    elif op == 'revenue_growth':
        _require(plan['period']['kind'] == 'this_month', 'semantic', 'growth requires explicit comparison')
    _require((plan['ranking'] is not None) == op.startswith('top_'), 'semantic', 'ranking conflicts with operation')
    if op == 'revenue_share':
        _require(any(plan['filters'][k] is not None for k in FILTER_FIELDS if k != 'unit_mention'),
                 'semantic', 'revenue_share requires a nonempty filter')


def validate_plan(raw: dict) -> dict:
    """Return a normalized, independent JSON plan; never infer data availability."""
    plan = _normalize(raw)
    _structure(plan)
    _semantics(plan)
    return plan
