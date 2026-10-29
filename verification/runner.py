"""Replay frozen plans, then score with the local evaluator; no legacy dependency."""
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

import pandas as pd

from business import Rulebook
from queryplan import QueryExecutor
from .manifest import ManifestError, file_hash, inventory_summary, read_records, validate_manifest


ROOT = Path(__file__).resolve().parents[1]


def _scorer():
    # pytest also imports evaluate.py as top-level 'evaluate'; avoid namespace collision.
    spec = importlib.util.spec_from_file_location('datamate_local_scorer', ROOT/'evaluate/evaluate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reference(path, ids, scorer):
    records = read_records(path)
    if {r['id'] for r in records} != ids:
        raise ManifestError('gold ids must match the complete question corpus exactly')
    for row in records:
        kind = row.get('type')
        if kind not in ('number', 'percent', 'list', 'date', 'string', 'boolean', 'table', 'unanswerable'):
            raise ManifestError('unknown reference type')
        if kind != 'unanswerable' and ('answer' not in row or not scorer.is_valid_format(kind, row['answer'])):
            raise ManifestError('invalid reference answer format')
    return {r['id']: r for r in records}


def _load_cache(directory):
    files = [directory/f'{key}.parquet' for key in ('don_hang', 'dong_hang', 'mat_hang')]
    files.append(directory/'cua_hang.json')
    fingerprints = {path.name: file_hash(path) for path in files}
    tables = {path.stem: pd.read_parquet(path) for path in files[:-1]}
    tables['cua_hang'] = json.loads(files[-1].read_text(encoding='utf-8-sig'))
    return tables, fingerprints


def verify_manifest(manifest_path, train_dir, cache_dir, progress=None) -> dict:
    manifest_path, train_dir, cache_dir = map(Path, (manifest_path, train_dir, cache_dir))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    entries = validate_manifest(manifest, train_dir/'questions.jsonl', train_dir/'rulebook.md')
    summary = inventory_summary(manifest)
    rules = Rulebook.from_path(train_dir/'rulebook.md')
    groups = defaultdict(list)
    for index, entry in enumerate(entries):
        if entry['selection'] == 'selected':
            groups[entry['business_id']].append((index, entry))
    rows, cache_hashes = [], {}
    calendar = train_dir/'calendar.csv'
    for group_index, (bid, selected) in enumerate(groups.items(), 1):
        try:
            tables, fingerprints = _load_cache(cache_dir/bid)
            cache_hashes[bid] = fingerprints
        except Exception as exc:
            # A broken/missing cache remains an explicit error for EVERY affected plan.
            for index, entry in selected:
                rows.append(dict(index=index, id=entry['id'], operation=entry['plan']['operation'],
                    execution_status='cache_error', stage='cache', prediction=None,
                    reason=f'{type(exc).__name__}: {exc}'))
        else:
            for index, entry in selected:
                row = dict(index=index, id=entry['id'], operation=entry['plan']['operation'])
                try:
                    result = QueryExecutor(tables, rules, entry['as_of_date'], calendar).execute(entry['plan'])
                    row.update(execution_status=result.status, stage=result.stage,
                               prediction=result.answer.to_submission(entry['id']), reason=result.answer.reason)
                except Exception as exc:
                    # Development diagnostics only: never disguise implementation bugs as business answers.
                    row.update(execution_status='execution_error', stage='execution', prediction=None,
                               reason=f'{type(exc).__name__}: {exc}')
                rows.append(row)
            del tables  # Retain at most one business's complete canonical tables.
        if progress:
            progress(group_index, len(groups), len(rows))
    rows.sort(key=lambda r: r.pop('index'))
    # Selection and predictions are complete BEFORE reference answers are read.
    scorer = _scorer()
    gold = _reference(train_dir/'answers.jsonl', {e['id'] for e in entries}, scorer)
    counts = Counter()
    by_operation = defaultdict(Counter)
    for row in rows:
        status = row['execution_status']
        if status in ('cache_error', 'execution_error'):
            outcome = 'execution_errors'
            row.update(score=None, score_reason='not scored: execution failed')
        else:
            score, reason = scorer.score_one(gold[row['id']], row['prediction'])
            row.update(score=score, score_reason=reason)
            outcome = {'correct': 'matched', 'wrong': 'mismatch', 'abstain': 'abstained'}[score]
        counts[outcome] += 1
        by_operation[row['operation']][outcome] += 1
    # Refuse a mixed snapshot if another process changed the corpus/rulebook during replay.
    validate_manifest(manifest, train_dir/'questions.jsonl', train_dir/'rulebook.md')
    result = {k: summary[k] for k in ('total', 'selected', 'outside_selection')}
    result.update({k: counts[k] for k in ('matched', 'mismatch', 'abstained', 'execution_errors')})
    result['compared'] = counts['matched'] + counts['mismatch']
    if result['selected'] != result['compared'] + result['abstained'] + result['execution_errors']:
        raise RuntimeError('verification denominator invariant violated')
    sources = ('verification/selection.py', 'verification/manifest.py', 'verification/runner.py',
               'queryplan/contract.py', 'queryplan/executor.py', 'queryplan/resolution.py',
               'business/sales.py', 'business/periods.py', 'business/rules.py', 'evaluate/evaluate.py')
    return result | dict(evaluation='retrospective_grammar_executor',
        by_operation={op: dict(values) for op, values in by_operation.items()},
        execution_statuses=dict(Counter(r['execution_status'] for r in rows)),
        unselected_reasons=summary['unselected_reasons'],
        manifest_sha256=file_hash(manifest_path), sources=manifest['sources'],
        gold_sha256=file_hash(train_dir/'answers.jsonl'),
        calendar_sha256=file_hash(calendar) if calendar.exists() else None,
        code_sha256={name: file_hash(ROOT/name) for name in sources}, cache_sha256=cache_hashes, rows=rows)


def verification_exit_code(result):
    return int(not result['selected'] or not result['compared'] or any(
        result[key] for key in ('mismatch', 'abstained', 'execution_errors')))
