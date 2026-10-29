"""Synthetic strict parsing and model/executor boundary regressions."""
import json
from copy import deepcopy

import pytest

from nlu import (Generation, GenerationFailure, NLUParseError, execute_attempt,
                 generate_plan, inspect_generation, parse_plan)
from nlu.schema import plan_schema
from queryplan import PlanValidationError
from queryplan.contract import OPERATIONS, PERIOD_FIELDS, PERIOD_KINDS
from queryplan_fixtures import plan


@pytest.mark.parametrize('wrapper', ['{}', ' \n{}\n ', '```json\n{}\n```', '```\n{}\n```'])
def test_parser_accepts_only_unambiguous_whole_output(wrapper):
    expected = plan()
    assert parse_plan(wrapper.format(json.dumps(expected))) == expected


@pytest.mark.parametrize('text', [
    '', ' ', 'null', '[]', '3', 'true', '"text"',
    '{} {}', 'explanation\n{}', '{}\nextra', '```json\n{}\n```\n{}',
    '```json\n{}', '{"version":"1.0","version":"2.0"}',
    '{"filters":{"unit_mention":null,"unit_mention":"ly"}}',
    '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}',
    '{"value":1e999}', '{"x":1,}',
])
def test_parser_rejects_ambiguous_or_malformed_transport(text):
    with pytest.raises(NLUParseError):
        parse_plan(text)


def test_parser_does_not_fill_missing_fields_or_repair_enum():
    value = plan()
    del value['ranking']
    with pytest.raises(PlanValidationError):
        parse_plan(json.dumps(value))
    value = plan()
    value['period']['kind'] = 'pre_month'
    with pytest.raises(PlanValidationError):
        parse_plan(json.dumps(value))


def test_only_public_validator_normalizes_integer_values_and_empty_mentions():
    value = plan('top_products')
    value['ranking']['k'] = 2.0
    value['filters']['product_mentions'] = []
    parsed = parse_plan(json.dumps(value))
    assert parsed['ranking']['k'] == 2 and type(parsed['ranking']['k']) is int
    assert parsed['filters']['product_mentions'] is None
    assert value['filters']['product_mentions'] == []


def test_two_complete_plans_are_not_repaired_by_selecting_last_block():
    with pytest.raises(NLUParseError):
        parse_plan(json.dumps(plan()) + '\n' + json.dumps(plan('order_count')))


def test_truncated_but_parseable_generation_is_abstained_without_dispatch():
    attempt = inspect_generation(Generation(json.dumps(plan()), finish_reason='length'))
    result = execute_attempt(attempt, None, 'synthetic')
    assert result['submission']['type'] == 'abstain'
    assert result['status'] == 'incomplete_generation' and result['stage'] == 'generation'


def test_capability_failure_is_not_json_failure():
    value = plan('top_customers')
    value['filters']['product_mentions'] = ['Synthetic product']
    attempt = inspect_generation(Generation(json.dumps(value)))
    assert attempt.status == 'unsupported_capability' and attempt.stage == 'capability'


def test_expected_backend_failure_and_unexpected_bug_remain_distinct():
    class Failed:
        def generate(self, *args):
            raise GenerationFailure('backend_timeout', 'timed out')
    result = generate_plan([], Failed(), {}, {})
    assert result.status == 'backend_timeout' and result.stage == 'generation'
    class Bug:
        def generate(self, *args):
            raise RuntimeError('implementation bug')
    with pytest.raises(RuntimeError, match='implementation bug'):
        generate_plan([], Bug(), {}, {})


def test_valid_plan_dispatch_uses_public_executor_result_without_recasting():
    class Answer:
        def to_submission(self, qid):
            return {'id': qid, 'type': 'unanswerable'}
    class Result:
        answer, status, stage = Answer(), 'unanswerable', 'resolve'
    class Executor:
        def execute(self, received):
            assert received == plan()
            return Result()
    result = execute_attempt(inspect_generation(Generation(json.dumps(plan()))), Executor(), 'synthetic')
    assert result['submission'] == {'id': 'synthetic', 'type': 'unanswerable'}
    assert result['status'] == 'unanswerable' and result['stage'] == 'resolve'


def _branch_operations(branch):
    spec = branch['properties']['operation']
    return set(spec.get('enum', [spec.get('const')]))


def test_schema_has_contract_specific_supported_envelopes_and_is_fresh():
    schema = plan_schema()
    for branch in schema['anyOf']:
        assert branch['additionalProperties'] is False
        assert set(branch['required']) == set(plan())
    supported, unsupported = schema['anyOf'][:-1], schema['anyOf'][-1]
    assert set().union(*map(_branch_operations, supported)) == set(OPERATIONS)
    assert unsupported['properties']['operation'] == {'type': 'null'}
    for branch in supported:
        for operation in _branch_operations(branch):
            assert branch['properties']['expected_type']['const'] == OPERATIONS[operation]
            assert (branch['properties']['ranking'].get('type') != 'null') == operation.startswith('top_')
            assert (branch['properties']['comparison_period'].get('type') != 'null') == \
                   (operation == 'revenue_growth')
            unit = branch['properties']['filters']['properties']['unit_mention']
            assert (unit.get('type') != 'null') == (operation == 'quantity')
    before = deepcopy(schema)
    schema['anyOf'].clear()
    assert plan_schema() == before


def test_schema_period_variants_require_only_parameters_used_by_kind():
    supported = plan_schema()['anyOf'][0]
    variants = supported['properties']['period']['anyOf']
    assert {v['properties']['kind']['const'] for v in variants} == set(PERIOD_KINDS)
    month = next(v for v in variants if v['properties']['kind']['const'] == 'month')
    assert month['properties']['month']['type'] == 'integer'
    assert 'anyOf' in month['properties']['year']
    assert all(month['properties'][field] == {'type': 'null'}
               for field in PERIOD_FIELDS[1:] if field not in ('month', 'year'))
    today = next(v for v in variants if v['properties']['kind']['const'] == 'today')
    assert all(today['properties'][field] == {'type': 'null'} for field in PERIOD_FIELDS[1:])
