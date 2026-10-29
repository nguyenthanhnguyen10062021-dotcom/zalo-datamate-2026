"""Ablate the semantic gate on immutable predictions; never relabel old inference.

This reuses prior answers without executing business logic or calling a model.
Original generation/prediction/job/data hashes are checked; current gate source
is recorded separately. Train scoring opens gold only after the new predictions
have been frozen. Public mode never loads a scorer or reference answers.
"""
from collections import Counter
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nlu.semantic import GATE_VERSION, rejection_reason
from run_public_submission import (generation_attempt, generation_index,
                                   validate_submission, _read_jsonl)
from tools.nlu_jobs import load_protocol, write_new
from tools.public_jobs import _cache_hashes, _source_hashes
from verification.manifest import file_hash, object_hash, questions


def _checked_payload(path, digest_key):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get(digest_key) != object_hash({k:v for k,v in payload.items() if k != digest_key}):
        raise ValueError(f'{digest_key} changed')
    return payload


def apply_gate(rows, corpus):
    """Preserve source rows, changing only non-abstain answers rejected by the gate."""
    result = []
    for original in rows:
        row = deepcopy(original)
        if row['submission']['type'] != 'abstain':
            if row.get('plan') is None or row['plan']['status'] != 'supported':
                raise ValueError('An answered prediction needs a supported validated plan')
            reason = rejection_reason(corpus[row['id']]['question'], row['plan'])
            row['semantic_gate'] = GATE_VERSION
            row['semantic_reason'] = reason
            if reason is not None:
                row.update(previous_submission=row['submission'], previous_status=row['status'],
                    submission={'id':row['id'], 'type':'abstain'},
                    status='semantic_rejected', stage='semantic', diagnostic_reason=reason)
        # Remove diagnostic reasons from abstain submission rows, not the sidecar.
        if row['submission']['type'] == 'abstain':
            row['submission'] = {'id':row['id'], 'type':'abstain'}
        result.append(row)
    return result


def replay(jobs_path, predictions_path, generations_path, out, mode):
    jobs_path, predictions_path, generations_path, out = map(
        Path, (jobs_path, predictions_path, generations_path, out))
    if mode not in ('train', 'public'):
        raise ValueError('Use explicit train or public mode')
    if not out.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Artifacts must remain in ignored reports/')
    jobs = _checked_payload(jobs_path, 'jobs_sha256')
    prior = _checked_payload(predictions_path, 'predictions_sha256')
    if (prior['jobs_sha256'] != jobs['jobs_sha256']
            or prior['jobs_file_sha256'] != file_hash(jobs_path)
            or prior['generations_file_sha256'] != file_hash(generations_path)):
        raise ValueError('Original prediction/job/generation binding changed')
    if mode == 'train':
        if 'protocol_path' not in jobs:
            raise ValueError('Train replay requires a frozen train protocol')
        protocol, records = load_protocol(jobs['protocol_path'])
        if protocol['protocol_sha256'] != jobs['protocol_sha256']:
            raise ValueError('Train protocol changed')
        split = Path(protocol['train_root'])
        assignments = {e['id']: e for e in protocol['entries']}
    else:
        if jobs.get('purpose') != 'public_test_submission_generation':
            raise ValueError('Public replay requires public jobs')
        split = Path(jobs['split_root'])
        if (jobs['sources'] != _source_hashes(split)
                or jobs['cache_sha256'] != _cache_hashes(jobs['cache_root'], jobs['businesses'])):
            raise ValueError('Original public data/cache changed')
        records = questions(split/'questions.jsonl')
        if jobs['selected'] != len(records) or [j['id'] for j in jobs['jobs']] != [q['id'] for q in records]:
            raise ValueError('Public job order/cardinality changed')
        assignments = None
    by_id = {q['id']:q for q in records}
    expected = {j['request_id'] for j in jobs['jobs']}
    if len(expected) != len(jobs['jobs']) or len(expected) != jobs['selected']:
        raise ValueError('Job cardinality/uniqueness changed')
    generations, metadata = generation_index(_read_jsonl(generations_path), expected)
    bound = [m for m in metadata if m.get('record_type') == 'run_metadata']
    if len(bound) != 1 or bound[0].get('jobs_sha256') != jobs['jobs_sha256']:
        raise ValueError('Original inference is not bound to jobs')
    rows = prior['rows']
    if (len(rows) != jobs['selected'] or len({r['id'] for r in rows}) != len(rows)
            or [r['request_id'] for r in rows] != [j['request_id'] for j in jobs['jobs']]):
        raise ValueError('Original prediction order/cardinality changed')
    for row, job in zip(rows, jobs['jobs']):
        question = by_id[job['id']]
        if (row['id'] != job['id'] or row['business_id'] != job['business_id']
                or row['submission']['id'] != job['id']
                or job['question_sha256'] != object_hash(question)
                or question['business_id'] != job['business_id']
                or question['as_of_date'] != job['as_of_date']
                or job['messages_sha256'] != object_hash(job['messages'])):
            raise ValueError('Original question/routing binding changed')
        if assignments is not None and job['role'] != assignments[job['id']]['role']:
            raise ValueError('Original train partition changed')
        attempt = generation_attempt(generations.get(job['request_id']))
        if attempt.plan != row.get('plan'):
            raise ValueError('Frozen plan differs from original raw generation')

    code = {name:file_hash(ROOT/name) for name in
            ('nlu/semantic.py', 'nlu/parser.py', 'nlu/pipeline.py',
             'tools/replay_semantic.py', 'evaluate/evaluate.py')}
    current = apply_gate(rows, by_id)
    submission = [r['submission'] for r in current]
    selected_questions = [by_id[r['id']] for r in current]
    validate_submission(submission, selected_questions)
    payload = dict(purpose='semantic_gate_replay_of_frozen_answers', mode=mode,
        semantic_gate=GATE_VERSION, code_sha256=code,
        original_predictions_file_sha256=file_hash(predictions_path),
        jobs_file_sha256=file_hash(jobs_path), jobs_sha256=jobs['jobs_sha256'],
        generations_file_sha256=file_hash(generations_path),
        original_generation_code_sha256=jobs['code_sha256'],
        gold_opened_this_run=False, rows=current)
    payload['predictions_sha256'] = object_hash(payload)
    write_new(out/'predictions.json', payload)
    with (out/'submission.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
        for row in submission:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
    summary = dict(mode=mode, semantic_gate=GATE_VERSION, total=len(current),
        rejection_reasons=dict(Counter(r.get('semantic_reason') for r in current if r.get('semantic_reason'))),
        submission_types=dict(Counter(r['type'] for r in submission)),
        predictions_file_sha256=file_hash(out/'predictions.json'),
        submission_file_sha256=file_hash(out/'submission.jsonl'),
        source_code_sha256=code, inference_rerun=False, business_reexecuted=False)
    if mode == 'train':
        # This branch alone may open gold, after ALL predictions are immutable.
        from verification.runner import _reference, _scorer
        scorer = _scorer()
        gold = _reference(split/'answers.jsonl', set(by_id), scorer)
        before, after, transitions = Counter(), Counter(), Counter()
        for old, new in zip(rows, current):
            old_outcome = scorer.score_one(gold[old['id']], old['submission'])[0]
            new_outcome = scorer.score_one(gold[new['id']], new['submission'])[0]
            before[old_outcome] += 1
            after[new_outcome] += 1
            transitions[old_outcome+'->'+new_outcome] += 1
        def metrics(counts):
            answered = counts['correct']+counts['wrong']
            return dict(correct=counts['correct'], wrong=counts['wrong'], abstain=counts['abstain'],
                penalized_accuracy=(counts['correct']-counts['wrong'])/len(current),
                coverage=answered/len(current), precision=counts['correct']/answered if answered else None)
        summary.update(evaluation='retrospective_frozen_prediction_ablation', role=jobs['role'],
            total_eligible=jobs['total_eligible'], outside_selection=jobs['outside_selection'],
            before=metrics(before), after=metrics(after), transitions=dict(transitions),
            gold_sha256=file_hash(split/'answers.jsonl'))
    if code != {name:file_hash(ROOT/name) for name in code}:
        raise ValueError('Gate/scoring source changed during replay')
    write_new(out/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--generations', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('train', 'public'), required=True)
    args = parser.parse_args()
    replay(args.jobs, args.predictions, args.generations, args.out, args.mode)


if __name__ == '__main__':
    main()
