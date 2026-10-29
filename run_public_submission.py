"""Execute frozen public generations locally and emit a validated upload file."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
from pathlib import Path
import re
import time

from business import Rulebook
from nlu import Generation, PlanAttempt, execute_attempt, inspect_generation
from queryplan import QueryExecutor
from tools.public_jobs import load_cache, load_public_jobs
from verification.manifest import file_hash, object_hash


ROOT = Path(__file__).resolve().parent
DATE_RE = re.compile(r"\d{4}-\d{2}(?:-\d{2})?",re.ASCII)
ANSWER_TYPES = frozenset({'number','percent','date','boolean','string','list','table'})


def _write_new(path: Path, payload: dict) -> None:
    path = Path(path)
    if not path.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Public artifacts must remain under ignored reports/')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def _read_jsonl(path: Path) -> list[dict]:
    def reject_constant(value):
        raise ValueError(f'Non-finite JSON constant: {value}')

    records = []
    for number,line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():
            continue
        try:
            row = json.loads(line,parse_constant=reject_constant)
        except (json.JSONDecodeError,ValueError) as exc:
            raise ValueError(f'Invalid generation JSON at line {number}: {exc}') from exc
        if type(row) is not dict:
            raise ValueError(f'Generation line {number} must be an object')
        records.append(row)
    return records


def generation_index(records, expected_ids):
    result,metadata = {},[]
    for row in records:
        if row.get('record_type') in ('run_metadata','worker_metadata'):
            metadata.append(row)
            continue
        request_id = row.get('request_id')
        if request_id not in expected_ids or request_id in result:
            raise ValueError('Unknown/duplicate generation request id')
        result[request_id] = row
    return result,metadata


def generation_attempt(row):
    if row is None:
        return PlanAttempt(None,'missing_generation','generation','No output for frozen job')
    if row.get('error'):
        return PlanAttempt(None,str(row['error']),'generation',
                           str(row.get('reason',row['error'])))
    return inspect_generation(Generation(row['text'],row['finish_reason'],
        {key:value for key,value in row.items() if key not in ('text','request_id')}))


def _is_number(value) -> bool:
    return type(value) in (int,float) and (type(value) is int or math.isfinite(value))


def _is_scalar(value) -> bool:
    return value is not None and (type(value) in (str,bool) or _is_number(value))


def _validate_answer(row: dict) -> None:
    answer_type = row['type']
    answer = row['answer']
    if answer_type in ('number','percent'):
        valid = _is_number(answer)
    elif answer_type == 'date':
        valid = type(answer) is str and DATE_RE.fullmatch(answer) is not None
    elif answer_type == 'boolean':
        valid = type(answer) is bool
    elif answer_type == 'string':
        valid = type(answer) is str
    elif answer_type == 'list':
        valid = type(answer) is list and all(_is_scalar(value) for value in answer)
    else:
        valid = (type(answer) is dict and set(answer) == {'columns','rows'}
                 and type(answer['columns']) is list
                 and all(type(column) is str for column in answer['columns'])
                 and len(set(answer['columns'])) == len(answer['columns'])
                 and type(answer['rows']) is list
                 and all(type(data_row) is list
                         and len(data_row) == len(answer['columns'])
                         and all(_is_scalar(value) for value in data_row)
                         for data_row in answer['rows']))
    if not valid:
        raise ValueError(f'Invalid {answer_type} answer shape for {row["id"]}')


def validate_submission(rows: list[dict], questions: list[dict]) -> None:
    if type(rows) is not list or type(questions) is not list:
        raise ValueError('Submission rows and questions must be lists')
    expected = [question.get('id') for question in questions]
    if any(type(question) is not dict or type(question.get('id')) is not str for question in questions):
        raise ValueError('Every question must have a string id')
    if len(set(expected)) != len(expected):
        raise ValueError('Question ids must be unique')
    if len(rows) != len(expected) or [row.get('id') if type(row) is dict else None for row in rows] != expected:
        raise ValueError('Submission ids must be unique, complete and in question order')
    for row in rows:
        answer_type = row.get('type')
        if answer_type == 'abstain':
            if set(row) != {'id','type'}:
                raise ValueError('Abstain rows may contain only id and type')
        elif answer_type == 'unanswerable':
            if not set(row).issubset({'id','type','reason'}) or set(row) < {'id','type'}:
                raise ValueError('Invalid unanswerable fields')
            if 'reason' in row and type(row['reason']) is not str:
                raise ValueError('Unanswerable reason must be a string')
        elif answer_type in ANSWER_TYPES:
            if set(row) != {'id','type','answer'}:
                raise ValueError('Answered rows require only id, type and answer')
            _validate_answer(row)
        else:
            raise ValueError(f'Unknown submission type: {answer_type!r}')


def _sanitize_submission(submission: dict, question_id: str) -> dict:
    if type(submission) is not dict or submission.get('id') != question_id:
        raise ValueError('Executor returned a mismatched submission row')
    if submission.get('type') == 'abstain':
        return {'id':question_id,'type':'abstain'}
    return dict(submission)


def _execute_business(business_id, group, generations, split_root, cache_root):
    rules = Rulebook.from_path(Path(split_root)/'rulebook.md')
    results = {}
    try:
        tables,business_metadata = load_cache(Path(cache_root)/business_id)
        tables['cua_hang'] = business_metadata
        cache_error = None
    except Exception as exc:
        tables,cache_error = None,f'{type(exc).__name__}: {exc}'
    for job in group:
        started = time.perf_counter()
        attempt = None
        try:
            attempt = generation_attempt(generations.get(job['request_id']))
            if tables is None:
                result = dict(submission={'id':job['id'],'type':'abstain'},
                              status='cache_error',stage='cache',plan=attempt.plan,
                              diagnostic_reason=cache_error)
            else:
                executor = QueryExecutor(tables,rules,job['as_of_date'],
                                         Path(split_root)/'calendar.csv')
                result = execute_attempt(attempt,executor,job['id'],question=job['question'])
                result['diagnostic_reason'] = (result['submission'].get('reason')
                    if type(result.get('submission')) is dict else None) or attempt.reason
            result['submission'] = _sanitize_submission(result['submission'],job['id'])
            result.update(input_status=attempt.status,
                json_valid=attempt.status not in ('invalid_json','missing_generation',
                                                   'incomplete_generation')
                    and attempt.stage != 'generation',
                plan_contract_valid=attempt.plan is not None)
        except Exception as exc:
            result = dict(submission={'id':job['id'],'type':'abstain'},
                status='execution_error',stage='execution',
                plan=attempt.plan if attempt else None,
                diagnostic_reason=f'{type(exc).__name__}: {exc}',
                input_status=attempt.status if attempt else 'execution_error',
                json_valid=bool(attempt and attempt.stage != 'generation'
                                and attempt.status != 'invalid_json'),
                plan_contract_valid=bool(attempt and attempt.plan is not None))
        results[job['request_id']] = dict(id=job['id'],business_id=business_id,
            request_id=job['request_id'],local_execution_ms=(time.perf_counter()-started)*1000,
            **result)
    return results


def run(jobs_path: Path, generations_path: Path, out_dir: Path, workers: int = 1) -> dict:
    jobs_path,generations_path,out_dir = map(Path,(jobs_path,generations_path,out_dir))
    if not out_dir.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Public artifacts must remain under ignored reports/')
    if type(workers) is not int or not 1 <= workers <= 10:
        raise ValueError('Local workers must be between 1 and 10')
    jobs,questions = load_public_jobs(jobs_path)
    expected = {job['request_id'] for job in jobs['jobs']}
    if len(expected) != len(jobs['jobs']):
        raise ValueError('Frozen jobs contain duplicate request ids')
    generations,metadata = generation_index(_read_jsonl(generations_path),expected)
    run_metadata = [row for row in metadata if row.get('record_type') == 'run_metadata']
    if len(run_metadata) != 1 or run_metadata[0].get('jobs_sha256') != jobs['jobs_sha256']:
        raise ValueError('Generation artifact metadata is not bound to frozen jobs')

    groups = defaultdict(list)
    for job,question in zip(jobs['jobs'],questions):
        groups[job['business_id']].append(dict(job,question=question['question']))
    results = {}
    if workers == 1:
        for index,(business_id,group) in enumerate(groups.items(),1):
            results.update(_execute_business(business_id,group,generations,
                                             jobs['split_root'],jobs['cache_root']))
            print(f'Executed {index}/{len(groups)} cache groups; {len(results)} predictions',flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_execute_business,bid,group,
                {job['request_id']:generations[job['request_id']] for job in group
                 if job['request_id'] in generations},jobs['split_root'],jobs['cache_root'])
                for bid,group in groups.items()]
            for index,future in enumerate(as_completed(futures),1):
                results.update(future.result())
                print(f'Executed {index}/{len(groups)} cache groups; {len(results)} predictions',flush=True)

    sidecar_rows = [results[job['request_id']] for job in jobs['jobs']]
    submission_rows = [row['submission'] for row in sidecar_rows]
    validate_submission(submission_rows,questions)
    predictions = dict(jobs_sha256=jobs['jobs_sha256'],jobs_file_sha256=file_hash(jobs_path),
        generations_file_sha256=file_hash(generations_path),metadata=metadata,
        gold_opened_this_run=False,rows=sidecar_rows)
    predictions['predictions_sha256'] = object_hash(predictions)
    summary = dict(total=len(submission_rows),generated=len(generations),
        missing_generations=len(submission_rows)-len(generations),
        execution_statuses=dict(Counter(row['status'] for row in sidecar_rows)),
        submission_types=dict(Counter(row['type'] for row in submission_rows)),
        jobs_sha256=jobs['jobs_sha256'])
    _write_new(out_dir/'predictions.json',predictions)
    _write_new(out_dir/'summary.json',summary)
    with (out_dir/'submission.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for row in submission_rows:
            stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=Path,required=True)
    parser.add_argument('--generations',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=1)
    args = parser.parse_args()
    run(args.jobs,args.generations,args.out,args.workers)


if __name__ == '__main__':
    main()
