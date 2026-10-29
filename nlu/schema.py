"""Constrained-decoding schema; Python validation/capability remain authoritative."""
from queryplan.contract import (COMPARISON_KINDS, FILTER_FIELDS, OPERATIONS, PERIOD_FIELDS,
                                PERIOD_KINDS, TOP_FIELDS, UNSUPPORTED_REASONS)


def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def _nullable(spec):
    return {'anyOf': [spec, {'type': 'null'}]}


def _integer(name):
    spec = {'type': 'integer', 'minimum': 1}
    if name in ('month', 'quarter', 'year'):
        spec['maximum'] = {'month': 12, 'quarter': 4, 'year': 9999}[name]
    return spec


def _period_variant(kind):
    """Encode nullability implied by kind so the model cannot fill unrelated fields."""
    props = {'kind': {'const': kind}}
    allowed = {'last_days': ('n',), 'month': ('month', 'year'),
               'quarter': ('quarter', 'year'), 'tet': ('year',),
               'date_range': ('start_date', 'end_date')}.get(kind, ())
    optional = {'year'} if kind in ('month', 'quarter') else set()
    for name in PERIOD_FIELDS[1:]:
        if name not in allowed:
            props[name] = {'type': 'null'}
        elif name.endswith('_date'):
            props[name] = {'type': 'string', 'pattern': r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'}
        elif name in optional:
            props[name] = _nullable(_integer(name))
        else:
            props[name] = _integer(name)
    return _object(props)


def _period(kinds):
    return {'anyOf': [_period_variant(kind) for kind in kinds]}


def _filters(*, allow_unit=False, order_only=False):
    mention = {'type': 'string', 'minLength': 1}
    props = {name: _nullable(mention.copy()) for name in FILTER_FIELDS}
    props['product_mentions'] = _nullable({'type': 'array', 'items': mention, 'minItems': 1})
    props['shift'] = {'enum': ['sang', 'chieu', None]}
    if not allow_unit:
        props['unit_mention'] = {'type': 'null'}
    if order_only:
        props['product_mentions'] = {'type': 'null'}
        props['product_group_mention'] = {'type': 'null'}
    return _object(props)


def _operation(operations, expected_type, *, comparison=False, ranking=None,
               allow_unit=False, order_only=False):
    operation = ({'const': operations[0]} if len(operations) == 1
                 else {'type': 'string', 'enum': list(operations)})
    return _object({
        'version': {'const': '1.0'}, 'status': {'const': 'supported'},
        'unsupported_reason': {'type': 'null'}, 'operation': operation,
        'expected_type': {'const': expected_type}, 'period': _period(PERIOD_KINDS),
        'comparison_period': (_nullable(_period(COMPARISON_KINDS)) if comparison
                              else {'type': 'null'}),
        'filters': _filters(allow_unit=allow_unit, order_only=order_only),
        'ranking': ranking if ranking is not None else {'type': 'null'},
    })


def plan_schema() -> dict:
    """Return a fresh schema that blocks known contract-invalid field combinations.

    Calendar validity, entity resolution, capability and business truth still belong to
    the public Python validator/executor. The schema only narrows combinations already
    declared by the QueryPlan contract.
    """
    top_products = _object({'k': {'type': 'integer', 'minimum': 1},
                            'metric': {'enum': ['quantity', 'revenue']}})
    top_customers = _object({'k': {'type': 'integer', 'minimum': 1},
                             'metric': {'enum': ['orders', 'revenue']}})
    supported = [
        _operation(('revenue', 'order_count', 'cancelled_orders', 'average_order_value'), 'number'),
        _operation(('quantity',), 'number', allow_unit=True),
        _operation(('cancellation_rate',), 'percent', order_only=True),
        _operation(('revenue_share',), 'percent'),
        _operation(('revenue_growth',), 'percent', comparison=True),
        _operation(('top_products',), 'list', ranking=top_products),
        _operation(('top_customers',), 'list', ranking=top_customers, order_only=True),
    ]
    unsupported = _object({k: {'type': 'null'} for k in TOP_FIELDS})
    unsupported['properties'].update(version={'const': '1.0'}, status={'const': 'unsupported'},
        unsupported_reason={'enum': list(UNSUPPORTED_REASONS)})
    assert {op for branch in supported for op in
            (branch['properties']['operation'].get('enum') or
             [branch['properties']['operation']['const']])} == set(OPERATIONS)
    return {'anyOf': [*supported, unsupported]}
