"""Question-only sampling and validation for local AI plan annotation audits."""
from collections import defaultdict

from queryplan import PlanValidationError, validate_plan
from .manifest import ManifestError, object_hash


def sample_unparsed(entries, per_reason=10):
    """Stable fingerprint order; round-robin businesses within each reason bucket."""
    if type(per_reason) is not int or per_reason <= 0:
        raise ValueError('per_reason must be a positive integer')
    buckets = defaultdict(lambda: defaultdict(list))
    for entry in entries:
        if entry['selection'] == 'unparsed':
            buckets[entry['reason']][entry['business_id']].append(entry)
    selected = []
    for reason, businesses in sorted(buckets.items()):
        queues = [sorted(rows, key=lambda e: (e['question_sha256'], e['id']))
                  for rows in businesses.values()]
        queues.sort(key=lambda rows: (rows[0]['question_sha256'], rows[0]['business_id']))
        count = 0
        while queues and count < per_reason:
            remaining = []
            for rows in queues:
                if count == per_reason:
                    break
                selected.append(dict(rows[0]))
                count += 1
                if len(rows) > 1:
                    remaining.append(rows[1:])
            queues = remaining
    return selected


def validate_annotations(packet, annotations):
    """Validate integrity and schema, not the truth of the annotator's reading."""
    def require(condition, message):
        if not condition:
            raise ManifestError(message)
    require(isinstance(packet, dict) and packet.get('version') == '1.0', 'invalid audit packet')
    digest = packet.get('packet_sha256')
    require(digest == object_hash({k: v for k, v in packet.items() if k != 'packet_sha256'}),
            'audit packet fingerprint changed')
    require(isinstance(annotations, dict) and annotations.get('packet_sha256') == digest,
            'annotations require the frozen packet fingerprint')
    if 'annotations_sha256' in annotations:
        require(annotations['annotations_sha256'] == object_hash(
            {k: v for k, v in annotations.items() if k != 'annotations_sha256'}),
            'annotation payload fingerprint changed')
    require(annotations.get('gold_access_this_audit') is False
            and type(annotations.get('prior_aggregate_score_exposure')) is bool
            and isinstance(annotations.get('annotator'), str) and bool(annotations['annotator'].strip()),
            'missing or incompatible annotation provenance')
    expected = {e['id']: e['question_sha256'] for e in packet['entries']}
    require(len(expected) == len(packet['entries']), 'duplicate packet id')
    rows = annotations.get('entries')
    require(isinstance(rows, list), 'annotation entries must be a list')
    seen = set()
    decisions = ('supported_plan', 'unsupported_capability', 'unsupported_domain', 'needs_clarification')
    for row in rows:
        require(isinstance(row, dict), 'annotation must be an object')
        qid = row.get('id')
        require(isinstance(qid, str) and qid in expected and qid not in seen, 'unknown/duplicate annotation id')
        seen.add(qid)
        require(row.get('question_sha256') == expected[qid], 'stale annotation question fingerprint')
        require(row.get('decision') in decisions, 'unknown annotation decision')
        for field in ('rationale', 'grammar_gap'):
            require(isinstance(row.get(field), str) and bool(row[field].strip()), f'missing {field}')
        require(row.get('confidence') in ('high', 'medium', 'low'), 'invalid confidence')
        require(isinstance(row.get('evidence'), list) and bool(row['evidence'])
                and all(isinstance(v, str) and v.strip() for v in row['evidence']), 'missing evidence')
        if row['decision'] == 'supported_plan':
            try:
                require(validate_plan(row.get('plan')) == row['plan'] and row['plan']['status'] == 'supported',
                        'annotation plan must be normalized and supported')
            except PlanValidationError as exc:
                raise ManifestError(f'invalid annotation plan: {exc}') from exc
        else:
            require(row.get('plan') is None, 'unsupported/uncertain annotation must keep plan null')
    require(seen == set(expected), 'annotations must cover the entire frozen sample')
    return rows
