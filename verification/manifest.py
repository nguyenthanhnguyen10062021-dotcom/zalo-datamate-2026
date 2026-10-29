"""Frozen inventory and source integrity. This module never opens gold or cache."""
from collections import Counter
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from queryplan import PlanValidationError, validate_plan
from . import selection


class ManifestError(ValueError):
    pass


def file_hash(path):
    digest = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def read_records(path):
    records, seen = [], set()
    for line_no, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise ManifestError(f'{Path(path).name}:{line_no}: invalid JSON') from exc
        if not isinstance(record, dict) or not isinstance(record.get('id'), str) or not record['id']:
            raise ManifestError(f'{Path(path).name}:{line_no}: missing/string id required')
        if record['id'] in seen:
            raise ManifestError(f'{Path(path).name}:{line_no}: duplicate id')
        seen.add(record['id'])
        records.append(record)
    if not records:
        raise ManifestError(f'{Path(path).name}: empty corpus')
    return records


def questions(path):
    rows = read_records(path)
    for row in rows:
        if any(not isinstance(row.get(k), str) or not row[k].strip()
               for k in ('question', 'business_id', 'as_of_date')):
            raise ManifestError('question/business_id/as_of_date must be nonempty strings')
        bid = row['business_id']
        if bid in ('.', '..') or any(c in bid for c in '/\\:'):
            raise ManifestError('business_id must be one local cache directory component')
        try:
            date.fromisoformat(row['as_of_date'])
        except ValueError as exc:
            raise ManifestError('invalid as_of_date') from exc
    return rows


def _sources(questions_path, rulebook_path):
    return dict(questions_sha256=file_hash(questions_path), rulebook_sha256=file_hash(rulebook_path),
                selector_sha256=file_hash(selection.__file__))


def build_manifest(questions_path, rulebook_path) -> dict:
    entries = []
    for row in questions(questions_path):
        entries.append(dict(id=row['id'], business_id=row['business_id'], as_of_date=row['as_of_date'],
                            question_sha256=object_hash(row), **selection.select_question(row['question'])))
    result = dict(version='1.0', evaluation='retrospective_grammar_executor',
                  sources=_sources(questions_path, rulebook_path), entries=entries)
    return result | dict(manifest_sha256=object_hash(result))


def validate_manifest(manifest, questions_path, rulebook_path):
    if (not isinstance(manifest, dict) or set(manifest) !=
            {'version', 'evaluation', 'sources', 'entries', 'manifest_sha256'} or manifest['version'] != '1.0'
            or manifest['evaluation'] != 'retrospective_grammar_executor'):
        raise ManifestError('unsupported manifest envelope/version')
    payload = {k: v for k, v in manifest.items() if k != 'manifest_sha256'}
    if object_hash(payload) != manifest['manifest_sha256']:
        raise ManifestError('manifest payload fingerprint changed')
    if manifest['sources'] != _sources(questions_path, rulebook_path):
        raise ManifestError('stale corpus/rulebook/selector fingerprint')
    rows = {q['id']: q for q in questions(questions_path)}
    entries = manifest['entries']
    if not isinstance(entries, list):
        raise ManifestError('manifest entries must be a list')
    seen = set()
    fields = {'id', 'business_id', 'as_of_date', 'question_sha256', 'selection', 'reason', 'plan'}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ManifestError('invalid entry envelope')
        qid = entry['id']
        if not isinstance(qid, str) or qid not in rows or qid in seen:
            raise ManifestError('missing/unknown/duplicate manifest id')
        seen.add(qid)
        row = rows[qid]
        if any(entry[k] != row[k] for k in ('business_id', 'as_of_date')) or entry['question_sha256'] != object_hash(row):
            raise ManifestError('entry does not match corpus')
        if not isinstance(entry['reason'], str) or not entry['reason']:
            raise ManifestError('entry requires reason')
        if entry['selection'] == 'selected':
            try:
                if validate_plan(entry['plan']) != entry['plan'] or entry['plan']['status'] != 'supported':
                    raise ManifestError('manifest plan must be normalized and executable')
            except PlanValidationError as exc:
                raise ManifestError(f'invalid manifest plan: {exc}') from exc
        elif entry['selection'] != 'unparsed' or entry['plan'] is not None:
            raise ManifestError('invalid unselected entry')
    if seen != set(rows):
        raise ManifestError('manifest does not cover entire corpus')
    return entries


def inventory_summary(manifest):
    entries = manifest['entries']
    selected = [e for e in entries if e['selection'] == 'selected']
    return dict(total=len(entries), selected=len(selected), outside_selection=len(entries)-len(selected),
        by_operation=dict(Counter(e['plan']['operation'] for e in selected)),
        by_period=dict(Counter(e['plan']['period']['kind'] for e in selected)),
        by_filter=dict(Counter(k for e in selected for k, v in e['plan']['filters'].items() if v is not None)),
        by_ranking_metric=dict(Counter(e['plan']['ranking']['metric'] for e in selected if e['plan']['ranking'])),
        unselected_reasons=dict(Counter(e['reason'] for e in entries if e['selection'] != 'selected')))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def local_output(path, protected=()):
    """Keep row-level artifacts under ignored reports/ and never overwrite inputs."""
    path = Path(path).resolve()
    reports = Path(__file__).resolve().parents[1] / 'reports'
    if not path.is_relative_to(reports.resolve()) or path in {Path(p).resolve() for p in protected}:
        raise ManifestError('output must be under repository reports/ and distinct from input files')
    return path
