"""Only synthetic plans; no competition questions or gold."""


def period_spec(kind='this_month', **values):
    return dict(kind=kind, n=None, month=None, quarter=None, year=None,
                start_date=None, end_date=None) | values


def plan(operation='revenue', **values):
    expected = {'cancellation_rate': 'percent', 'revenue_growth': 'percent',
                'revenue_share': 'percent', 'top_products': 'list', 'top_customers': 'list'}
    result = dict(version='1.0', status='supported', unsupported_reason=None,
                  operation=operation, expected_type=expected.get(operation, 'number'),
                  period=period_spec(), comparison_period=None,
                  filters=dict(product_mentions=None, product_group_mention=None,
                               channel_mention=None, payment_mention=None,
                               customer_group_mention=None, shift=None, unit_mention=None),
                  ranking=None)
    if operation.startswith('top_'):
        result['ranking'] = dict(k=3, metric='revenue')
    result.update(values)
    return result
