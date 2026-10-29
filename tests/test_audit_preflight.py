"""Preflight receipts do not rewrite frozen annotation decisions or execute data."""
from copy import deepcopy

import pytest

from queryplan import UnsupportedCapability, check_capability, validate_plan
from queryplan_fixtures import plan
from test_plan_annotation_audit import packet_and_annotations
from verification.audit import preflight_annotations


def test_preflight_keeps_frozen_annotations_and_separates_status():
    packet, annotations = packet_and_annotations()
    annotations['entries'][0]['plan'] = plan('top_products', ranking=dict(k=2, metric='orders'))
    before = deepcopy((packet, annotations))
    receipt = preflight_annotations(packet, annotations)
    assert (packet, annotations) == before
    entry = receipt['entries'][0]
    assert entry['schema_status'] == 'valid'
    assert entry['capability_status'] == 'unsupported_capability'
    assert entry['resolution_status'] == 'not_checked'
    assert entry['execution_status'] == 'not_run'
    assert receipt['packet_sha256'] == packet['packet_sha256']
    assert 'answer' not in entry


def test_valid_preflight_is_not_resolution_or_execution_verification():
    packet, annotations = packet_and_annotations()
    result = preflight_annotations(packet, annotations)
    assert result['entries'][0]['capability_status'] == 'supported'
    assert result['entries'][0]['resolution_status'] == 'not_checked'
    assert result['entries'][0]['execution_status'] == 'not_run'


def test_public_capability_preserves_validation_and_exception_contract():
    raw = plan('revenue')
    raw['filters']['unit_mention'] = 'ly'
    normalized = validate_plan(raw)
    with pytest.raises(UnsupportedCapability):
        check_capability(normalized)
