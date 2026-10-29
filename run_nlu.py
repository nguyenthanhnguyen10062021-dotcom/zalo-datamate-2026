"""Execute frozen model generations locally, freeze predictions, then score gold."""
from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path
import time

from business import Rulebook
from nlu import Generation, PlanAttempt, execute_attempt, inspect_generation
from queryplan import QueryExecutor
from tools.nlu_jobs import ROOT, load_protocol, write_new
from verification.manifest import file_hash, object_hash
from verification.runner import _load_cache, _reference, _scorer


def generation_index(records, expected_ids):
    result, metadata = {}, []
    for row in records:
        if row.get('record_type') in ('run_metadata','worker_metadata'):
            metadata.append(row)
            continue
        rid = row.get('request_id')
        if rid not in expected_ids or rid in result:
            raise ValueError('Unknown/duplicate generation request id')
        result[rid] = row
    return result, metadata


def generation_attempt(row):
    if row is None:
        return PlanAttempt(None,'missing_generation','generation','No output for frozen job')
    if row.get('error'):
        return PlanAttempt(None,str(row['error']),'generation',str(row.get('reason',row['error'])))
    return inspect_generation(Generation(row['text'],row['finish_reason'],
        {k:v for k,v in row.items() if k not in ('text','request_id')}))


def run(jobs_path, generations_path, out, references=None):
    jobs_path,generations_path,out = map(Path,(jobs_path,generations_path,out))
    if not out.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Reports must remain under ignored reports/')
    jobs = json.loads(jobs_path.read_text(encoding='utf-8'))
    if jobs['jobs_sha256'] != object_hash({k:v for k,v in jobs.items() if k!='jobs_sha256'}):
        raise ValueError('Job payload changed')
    protocol, corpus = load_protocol(jobs['protocol_path'])
    if protocol['protocol_sha256'] != jobs['protocol_sha256']:
        raise ValueError('Protocol changed')
    if any(file_hash(ROOT/path)!=digest for path,digest in jobs['code_sha256'].items()):
        raise ValueError('Prompt/parser/schema source changed; use a new jobs revision')
    expected = {j['request_id'] for j in jobs['jobs']}
    if len(expected)!=len(jobs['jobs']) or jobs['selected']!=len(expected):
        raise ValueError('Duplicate/missing frozen jobs')
    by_id = {q['id']:q for q in corpus}
    assignments = {e['id']:e for e in protocol['entries']}
    for job in jobs['jobs']:
        q = by_id[job['id']]
        if (job['business_id']!=q['business_id'] or job['as_of_date']!=q['as_of_date']
                or job['question_sha256']!=object_hash(q) or job['messages_sha256']!=object_hash(job['messages'])):
            raise ValueError('Job input/provenance mismatch')
        if (job['role']!=assignments[job['id']]['role']
                or job['request_id']!=object_hash({'protocol':protocol['protocol_sha256'],
                                                  'question':job['question_sha256']})):
            raise ValueError('Job routing/partition assignment mismatch')
    raw = [json.loads(line) for line in generations_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    generations,metadata = generation_index(raw,expected)
    if not any(m.get('record_type')=='run_metadata' and m.get('jobs_sha256')==jobs['jobs_sha256'] for m in metadata):
        raise ValueError('Generation artifact is not bound to frozen jobs')
    groups = defaultdict(list)
    for job in jobs['jobs']:
        groups[job['business_id']].append(job)
    rules = Rulebook.from_path(Path(protocol['train_root'])/'rulebook.md')
    rows = []
    for index,(bid,group) in enumerate(sorted(groups.items()),1):
        try:
            tables,_ = _load_cache(Path(protocol['cache_root'])/bid)
        except Exception as exc:
            tables,cache_error = None,f'{type(exc).__name__}: {exc}'
        for job in group:
            tick = time.perf_counter()
            attempt = None
            try:
                attempt = generation_attempt(generations.get(job['request_id']))
                if tables is None:
                    result = dict(submission={'id':job['id'],'type':'abstain','reason':cache_error},
                                  status='cache_error',stage='cache',plan=attempt.plan)
                else:
                    executor = QueryExecutor(tables,rules,job['as_of_date'],Path(protocol['train_root'])/'calendar.csv')
                    result = execute_attempt(attempt,executor,job['id'],question=by_id[job['id']]['question'])
                result.update(input_status=attempt.status,
                    json_valid=attempt.status not in ('invalid_json','missing_generation','incomplete_generation')
                        and attempt.stage!='generation',
                    plan_contract_valid=attempt.plan is not None)
            except Exception as exc:
                result = dict(submission={'id':job['id'],'type':'abstain','reason':f'{type(exc).__name__}: {exc}'},
                    status='execution_error',stage='execution',plan=attempt.plan if attempt else None,
                    input_status=attempt.status if attempt else 'execution_error',
                    json_valid=bool(attempt and attempt.stage!='generation' and attempt.status!='invalid_json'),
                    plan_contract_valid=bool(attempt and attempt.plan is not None))
            rows.append(dict(id=job['id'],business_id=bid,role=job['role'],request_id=job['request_id'],
                             local_execution_ms=(time.perf_counter()-tick)*1000,**result))
        print(f'Executed {index}/{len(groups)} cache groups; {len(rows)} predictions',flush=True)
    # Preserve every frozen job, including missing generations, before opening gold.
    payload = dict(jobs_sha256=jobs['jobs_sha256'],jobs_file_sha256=file_hash(jobs_path),
        generations_file_sha256=file_hash(generations_path),protocol_sha256=protocol['protocol_sha256'],
        code_sha256={p:file_hash(ROOT/p) for p in ('run_nlu.py','nlu/parser.py','nlu/pipeline.py','queryplan/executor.py','business/sales.py')},
        metadata=metadata,gold_opened_this_run=False,rows=rows)
    payload['predictions_sha256'] = object_hash(payload)
    write_new(out/'predictions.json',payload)
    scorer = _scorer()
    gold = _reference(Path(protocol['train_root'])/'answers.jsonl',set(by_id),scorer)
    counts,by_role = Counter(),defaultdict(Counter)
    for row in rows:
        outcome,reason = scorer.score_one(gold[row['id']],row['submission'])
        row.update(outcome=outcome,score_reason=reason)
        counts[outcome]+=1
        by_role[row['role']][outcome]+=1
    semantic = None
    if references is not None:
        reference = json.loads(Path(references).read_text(encoding='utf-8'))
        if reference['reference_sha256']!=object_hash({k:v for k,v in reference.items() if k!='reference_sha256'}):
            raise ValueError('Semantic reference digest changed')
        refs = {r['id']:r for r in reference['entries']}
        evaluated = [r for r in rows if r['id'] in refs]
        for row in evaluated:
            if refs[row['id']]['question_sha256']!=object_hash(by_id[row['id']]):
                raise ValueError('Semantic reference question changed')
        semantic = dict(reference_total=len(refs),present=len(evaluated),
            literal_plan_matched=sum(r['plan']==refs[r['id']]['plan'] for r in evaluated),
            equivalence_adjudicated=False,source_sha256=file_hash(references),
            prior_exposure=reference['annotator'])
    assert len(rows)==sum(counts.values())==jobs['selected']
    answered=counts['correct']+counts['wrong']
    summary = dict(evaluation='retrospective_model_nlu',role=jobs['role'],
        total=len(rows),total_eligible=jobs['total_eligible'],outside_selection=jobs['outside_selection'],
        correct=counts['correct'],wrong=counts['wrong'],abstain=counts['abstain'],
        penalized_accuracy=(counts['correct']-counts['wrong'])/len(rows) if rows else None,
        coverage=answered/len(rows) if rows else None,
        precision=counts['correct']/answered if answered else None,
        json_valid=sum(r['json_valid'] for r in rows),
        plan_contract_valid=sum(r['plan_contract_valid'] for r in rows),
        execution_statuses=dict(Counter(r['status'] for r in rows)),
        by_role={k:dict(v) for k,v in by_role.items()},semantic_reference=semantic,
        predictions_file_sha256=file_hash(out/'predictions.json'),
        gold_sha256=file_hash(Path(protocol['train_root'])/'answers.jsonl'),
        scoring_code_sha256=file_hash(ROOT/'evaluate/evaluate.py'))
    write_new(out/'scoring.json',summary|{'rows':rows})
    with (out/'submission.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row['submission'],ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=Path,required=True)
    parser.add_argument('--generations',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--references',type=Path)
    args=parser.parse_args()
    run(args.jobs,args.generations,args.out,args.references)


if __name__=='__main__':
    main()
