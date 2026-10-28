"""Contract boundary tests: reject model mistakes before any calculation."""
from copy import deepcopy
import math

import pytest

from queryplan import PlanValidationError, validate_plan
from queryplan_fixtures import period_spec, plan


def test_normalize_integer_float_mentions_and_empty_products_without_mutation():
    raw = plan('top_products', period=period_spec('month', month=3.0, year=2026.0),
               ranking=dict(k=1.0, metric='quantity'))
    raw['filters'].update(product_mentions=[], channel_mention='  online  ')
    before = deepcopy(raw)
    actual = validate_plan(raw)
    assert type(actual['ranking']['k']) is int
    assert type(actual['period']['month']) is int
    assert actual['filters']['product_mentions'] is None
    assert actual['filters']['channel_mention'] == 'online'
    assert raw == before


@pytest.mark.parametrize('value', [True, False, '1', 1.5, math.inf, math.nan])
def test_reject_non_integer_ranking(value):
    with pytest.raises(PlanValidationError):
        validate_plan(plan('top_products', ranking=dict(k=value, metric='quantity')))


@pytest.mark.parametrize('section,key', [(None, 'operation'), ('period', 'n'),
                                       ('filters', 'unit_mention'), ('ranking', 'metric')])
def test_required_and_unknown_fields_at_every_level(section, key):
    raw = plan('top_products')
    target = raw if section is None else raw[section]
    del target[key]
    with pytest.raises(PlanValidationError):
        validate_plan(raw)
    raw = plan('top_products')
    target = raw if section is None else raw[section]
    target['typo'] = None
    with pytest.raises(PlanValidationError):
        validate_plan(raw)


@pytest.mark.parametrize('value', [None, [], 'json', 1, True])
def test_root_must_be_object(value):
    with pytest.raises(PlanValidationError):
        validate_plan(value)


@pytest.mark.parametrize('values', [dict(status=[]), dict(operation={}), dict(version=1),
                                  dict(expected_type=True), dict(filters=[]), dict(ranking=[]),
                                  dict(unsupported_reason=[]), dict(period=[])])
def test_malformed_structure_is_validation_error_not_python_error(values):
    raw = plan()
    raw.update(values)
    with pytest.raises(PlanValidationError):
        validate_plan(raw)


@pytest.mark.parametrize('spec', [period_spec('date_range', start_date='2026-02-31', end_date='2026-03-04'),
    period_spec('date_range', start_date='2026-03-05', end_date='2026-03-04'),
    period_spec('date_range', start_date='20260301', end_date='2026-03-04'),
    period_spec('today', n=3), period_spec('last_days'), period_spec('month', month=13),
    period_spec('quarter', quarter=0), period_spec('tet'), period_spec('month', month=3, year=True),
    period_spec('date_range', start_date='2026-03-01'), period_spec('month', month=3, year=10000)])
def test_invalid_calendar_dates_and_unused_or_missing_period_fields(spec):
    with pytest.raises(PlanValidationError):
        validate_plan(plan(period=spec))


@pytest.mark.parametrize('field,value', [('channel_mention', '  '), ('unit_mention', 3),
    ('product_mentions', ['']), ('product_mentions', 'Trà'), ('product_mentions', [None]),
    ('shift', 'morning')])
def test_bad_filter_mentions(field, value):
    raw = plan()
    raw['filters'][field] = value
    with pytest.raises(PlanValidationError):
        validate_plan(raw)


@pytest.mark.parametrize('values', [dict(expected_type='list'), dict(ranking=dict(k=1, metric='revenue')),
    dict(comparison_period=period_spec('previous_week')), dict(filters=None),
    dict(unsupported_reason='ambiguous_question')])
def test_inconsistent_supported_plan(values):
    with pytest.raises(PlanValidationError):
        validate_plan(plan(**values))


def test_unsupported_envelope_cannot_contain_executable_fields():
    raw = dict(version='1.0', status='unsupported', unsupported_reason='unsupported_domain',
               operation=None, expected_type=None, period=None, comparison_period=None,
               filters=None, ranking=None)
    assert validate_plan(raw) == raw
    raw['operation'] = 'revenue'
    with pytest.raises(PlanValidationError):
        validate_plan(raw)


def test_growth_default_and_explicit_comparison_contract():
    assert validate_plan(plan('revenue_growth'))['comparison_period'] is None
    with pytest.raises(PlanValidationError):
        validate_plan(plan('revenue_growth', period=period_spec('today')))
    assert validate_plan(plan('revenue_growth', period=period_spec('today'),
                             comparison_period=period_spec('yesterday')))


def test_empty_share_rejected_after_normalization():
    raw = plan('revenue_share')
    raw['filters']['product_mentions'] = []
    with pytest.raises(PlanValidationError):
        validate_plan(raw)
