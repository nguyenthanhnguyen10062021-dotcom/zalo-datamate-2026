"""Synthetic annotation sampling and completeness checks, no reference answers."""
from copy import deepcopy

import pytest

from queryplan_fixtures import plan
from verification.audit import sample_unparsed, validate_annotations
from verification.manifest import ManifestError, object_hash


def entries():
    return [dict(id=f'q{i}', business_id=f'b{i%3}', question_sha256=object_hash(i),
                 selection='unparsed', reason='scope' if i < 9 else 'time') for i in range(12)]


def test_sample_is_deterministic_order_independent_diverse_and_bounded():
    rows = entries()
    before = deepcopy(rows)
    selected = sample_unparsed(rows, per_reason=4)
    assert selected == sample_unparsed(rows[::-1], per_reason=4)
    assert len(selected) == 7
    assert len({r['business_id'] for r in selected if r['reason'] == 'scope'}) == 3
    assert rows == before


def packet_and_annotations():
    packet = dict(version='1.0', entries=[dict(id='q', question_sha256='abc')])
    packet['packet_sha256'] = object_hash(packet)
    annotations = dict(packet_sha256=packet['packet_sha256'], annotator='Codex AI',
        gold_access_this_audit=False, prior_aggregate_score_exposure=True,
        entries=[dict(id='q', question_sha256='abc', decision='supported_plan',
                      plan=plan(), rationale='Explicit revenue and month',
                      evidence=['question: full text', 'rulebook: sales and time'],
                      grammar_gap='wording', confidence='high')])
    return packet, annotations


def test_complete_annotation_validated_without_reference_or_executor():
    packet, annotations = packet_and_annotations()
    assert validate_annotations(packet, annotations) == annotations['entries']


def test_annotation_digest_detects_edit_even_when_plan_schema_still_valid():
    packet, annotations = packet_and_annotations()
    annotations['annotations_sha256'] = object_hash(annotations)
    annotations['entries'][0]['rationale'] = 'Changed interpretation after freeze'
    with pytest.raises(ManifestError, match='annotation.*fingerprint'):
        validate_annotations(packet, annotations)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'plan', 'provenance', 'fingerprint', 'packet'])
def test_bad_annotation_or_stale_packet_rejected(change):
    packet, annotations = packet_and_annotations()
    if change == 'missing':
        annotations['entries'] = []
    elif change == 'duplicate':
        annotations['entries'] *= 2
    elif change == 'plan':
        annotations['entries'][0]['plan'] = None
    elif change == 'provenance':
        annotations['gold_access_this_audit'] = True
    elif change == 'fingerprint':
        annotations['entries'][0]['question_sha256'] = 'stale'
    else:
        packet['entries'][0]['id'] = 'changed'
    with pytest.raises(ManifestError):
        validate_annotations(packet, annotations)
