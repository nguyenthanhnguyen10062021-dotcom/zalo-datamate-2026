"""Batch frozen child job sets together without outcome-based selection."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from verification.manifest import file_hash, object_hash
from tools.nlu_jobs import write_new


def checked_jobs(payload):
    if payload['jobs_sha256']!=object_hash({k:v for k,v in payload.items() if k!='jobs_sha256'}):
        raise ValueError('Job payload changed')
    ids=[j['request_id'] for j in payload['jobs']]
    if len(ids)!=len(set(ids)) or len(ids)!=payload['selected']:
        raise ValueError('Duplicate or inconsistent job count')
    return set(ids)


def combine(children):
    jobs,parents,seen = [],[],set()
    schema,sampling = children[0]['schema'],children[0]['sampling']
    for child in children:
        ids=checked_jobs(child)
        if seen & ids or child['schema']!=schema or child['sampling']!=sampling:
            raise ValueError('Overlap or generation config mismatch')
        seen |= ids
        jobs.extend(child['jobs'])
        parents.append(dict(jobs_sha256=child['jobs_sha256'],request_ids=sorted(ids)))
    result=dict(version='1.0',purpose='combined frozen job sets; no outcome selection',
                schema=schema,sampling=sampling,jobs=jobs,selected=len(jobs),parents=parents)
    result['jobs_sha256']=object_hash(result)
    return result


def split_records(parent,child,records,source_sha256):
    all_ids,child_ids=checked_jobs(parent),checked_jobs(child)
    declared=[r for r in parent['parents'] if r['jobs_sha256']==child['jobs_sha256']]
    if len(declared)!=1 or set(declared[0]['request_ids'])!=child_ids or not child_ids<=all_ids:
        raise ValueError('Child is not the declared complete frozen subset')
    seen=set()
    metadata=[]
    selected=[]
    bound=False
    for row in records:
        kind=row.get('record_type')
        if kind=='run_metadata':
            if row.get('jobs_sha256')!=parent['jobs_sha256']:
                raise ValueError('Parent generation binding mismatch')
            bound=True
            metadata.append(row)
        elif kind=='worker_metadata':
            metadata.append(row)
        else:
            rid=row.get('request_id')
            if rid not in all_ids or rid in seen:
                raise ValueError('Unknown/duplicate parent generation')
            seen.add(rid)
            if rid in child_ids:
                selected.append(row)
    if not bound:
        raise ValueError('Missing parent run metadata')
    # Missing outputs stay missing and are counted by the downstream runner.
    return [dict(record_type='run_metadata',jobs_sha256=child['jobs_sha256'],
            derived_from_sha256=source_sha256,parent_jobs_sha256=parent['jobs_sha256'],
            parent_metadata=metadata),
            *[r for r in metadata if r.get('record_type')=='worker_metadata'],*selected]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    join=sub.add_parser('combine')
    join.add_argument('--jobs',type=Path,nargs='+',required=True)
    join.add_argument('--out',type=Path,required=True)
    split=sub.add_parser('split')
    split.add_argument('--parent',type=Path,required=True)
    split.add_argument('--child',type=Path,required=True)
    split.add_argument('--generations',type=Path,required=True)
    split.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='combine':
        result=combine([json.loads(p.read_text(encoding='utf-8')) for p in args.jobs])
        write_new(args.out,result)
        print('Frozen combined jobs:',result['selected'])
    else:
        rows=split_records(json.loads(args.parent.read_text(encoding='utf-8')),
            json.loads(args.child.read_text(encoding='utf-8')),
            [json.loads(line) for line in args.generations.read_text(encoding='utf-8').splitlines() if line.strip()],
            file_hash(args.generations))
        if not args.out.resolve().is_relative_to(ROOT/'reports'):
            raise ValueError('Output must remain in reports/')
        with args.out.open('x',encoding='utf-8',newline='\n') as stream:
            for row in rows:
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
        print('Derived fixed-subset output records:',sum('request_id' in r for r in rows))


if __name__=='__main__':
    main()
