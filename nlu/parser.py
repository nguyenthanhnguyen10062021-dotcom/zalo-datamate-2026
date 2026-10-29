"""Strict JSON transport parsing. QueryPlan owns normalization and semantics."""
import json
import math
import re

from queryplan import validate_plan


class NLUParseError(ValueError):
    pass


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise NLUParseError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _nonfinite(value):
    raise NLUParseError(f'Non-finite JSON number: {value}')


def _float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise NLUParseError('Non-finite JSON number')
    return parsed


def parse_plan(text: str, *, max_chars: int = 65536) -> dict:
    """Accept a single complete object or exactly one whole-output JSON fence."""
    if not isinstance(text, str) or not text.strip() or len(text) > max_chars:
        raise NLUParseError('Empty/non-string/oversized generation')
    value = text.strip()
    if value.startswith('```'):
        match = re.fullmatch(r'```(?:json)?[ \t]*\r?\n(.*?)\r?\n```', value, re.DOTALL)
        if not match:
            raise NLUParseError('Expected exactly one whole-output JSON fence')
        value = match[1]
    try:
        plan = json.loads(value, object_pairs_hook=_pairs, parse_constant=_nonfinite, parse_float=_float)
    except NLUParseError:
        raise
    except (ValueError, RecursionError) as exc:
        raise NLUParseError(f'Invalid single JSON object: {exc}') from exc
    if type(plan) is not dict:
        raise NLUParseError('Plan must be a JSON object')
    return validate_plan(plan)
