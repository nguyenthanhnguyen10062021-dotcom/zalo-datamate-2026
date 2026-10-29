"""Freeze all public-test NLU jobs without opening gold or scoring outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from nlu.prompt import PROMPT_VERSION, build_messages
from nlu.schema import plan_schema
from tools.nlu_jobs import table_context
from verification.manifest import file_hash, object_hash, questions


TABLES = ('don_hang','dong_hang','mat_hang','quy_doi_don_vi','khach_hang')
CACHE_FILES = tuple(f'{name}.parquet' for name in TABLES)+('cua_hang.json',)


def code_paths():
    return [*ROOT.joinpath('nlu').glob('*.py'),Path(__file__)]


def _write_new(path, payload):
    path = Path(path)
    if not path.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Artifacts must remain in ignored reports/')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def load_cache(cache_dir: Path) -> tuple[dict,dict]:
    import pandas as pd

    cache_dir = Path(cache_dir)
    missing = [name for name in CACHE_FILES if not (cache_dir/name).is_file()]
    if missing:
        raise ValueError(f'Missing canonical cache files: {", ".join(missing)}')
    tables = {name:pd.read_parquet(cache_dir/f'{name}.parquet') for name in TABLES}
    metadata = json.loads((cache_dir/'cua_hang.json').read_text(encoding='utf-8'))
    if type(metadata) is not dict:
        raise ValueError('cua_hang.json must contain one object')
    return tables,metadata


def _cache_hashes(cache_root, businesses):
    result = {}
    for bid in businesses:
        business_cache = Path(cache_root)/bid
        missing = [name for name in CACHE_FILES if not (business_cache/name).is_file()]
        if missing:
            raise ValueError(f'Missing canonical cache files for {bid}: {", ".join(missing)}')
        result[bid] = {name:file_hash(business_cache/name) for name in CACHE_FILES}
    return result


def _source_hashes(split_root):
    return {name:file_hash(Path(split_root)/name)
            for name in ('questions.jsonl','rulebook.md','calendar.csv')}


def _code_hashes():
    result = {}
    for path in code_paths():
        path = Path(path).resolve()
        try:
            name = path.relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            name = path.name
        if name in result:
            raise ValueError('Duplicate code fingerprint name')
        result[name] = file_hash(path)
    return result


def prepare_public_jobs(split_root: Path, cache_root: Path, out: Path) -> dict:
    split_root,cache_root = Path(split_root).resolve(),Path(cache_root).resolve()
    records = questions(split_root/'questions.jsonl')
    businesses = sorted({row['business_id'] for row in records})
    sources = _source_hashes(split_root)
    caches = _cache_hashes(cache_root,businesses)
    loaded = {bid:load_cache(cache_root/bid)[0] for bid in businesses}
    jobs = []
    for row in records:
        qhash = object_hash(row)
        messages = build_messages(row['question'],row['as_of_date'],
                                  table_context(loaded[row['business_id']],row['as_of_date']))
        jobs.append(dict(id=row['id'],business_id=row['business_id'],as_of_date=row['as_of_date'],
            question_sha256=qhash,
            request_id=object_hash({'questions':sources['questions.jsonl'],'question':qhash}),
            messages=messages,messages_sha256=object_hash(messages)))
    payload = dict(version='1.0',purpose='public_test_submission_generation',
        split_root=str(split_root),cache_root=str(cache_root),sources=sources,
        businesses=businesses,cache_sha256=caches,prompt_version=PROMPT_VERSION,
        schema=plan_schema(),sampling={'temperature':0.0,'seed':20261029,'max_tokens':768},
        code_sha256=_code_hashes(),selected=len(jobs),jobs=jobs)
    payload['jobs_sha256'] = object_hash(payload)
    _write_new(out,payload)
    return payload


def load_public_jobs(path: Path) -> tuple[dict,list[dict]]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('jobs_sha256') != object_hash(
            {key:value for key,value in payload.items() if key != 'jobs_sha256'}):
        raise ValueError('Job payload fingerprint changed')
    if payload.get('version') != '1.0' or payload.get('purpose') != 'public_test_submission_generation':
        raise ValueError('Unsupported public job envelope')
    split_root,cache_root = Path(payload['split_root']),Path(payload['cache_root'])
    if payload.get('sources') != _source_hashes(split_root):
        raise ValueError('Public source fingerprint changed')
    records = questions(split_root/'questions.jsonl')
    businesses = sorted({row['business_id'] for row in records})
    if payload.get('businesses') != businesses or payload.get('cache_sha256') != _cache_hashes(cache_root,businesses):
        raise ValueError('Public cache fingerprint changed')
    if payload.get('code_sha256') != _code_hashes():
        raise ValueError('Public generation code fingerprint changed')
    jobs = payload.get('jobs')
    if type(jobs) is not list or payload.get('selected') != len(records) or len(jobs) != len(records):
        raise ValueError('Public job cardinality changed')
    seen = set()
    for row,job in zip(records,jobs):
        qhash = object_hash(row)
        expected_request = object_hash({'questions':payload['sources']['questions.jsonl'],
                                        'question':qhash})
        if (set(job) != {'id','business_id','as_of_date','question_sha256','request_id',
                         'messages','messages_sha256'}
                or job['id'] != row['id'] or job['business_id'] != row['business_id']
                or job['as_of_date'] != row['as_of_date'] or job['question_sha256'] != qhash
                or job['request_id'] != expected_request
                or job['messages_sha256'] != object_hash(job['messages'])
                or job['request_id'] in seen):
            raise ValueError('Public job input/order/routing fingerprint changed')
        seen.add(job['request_id'])
    return payload,records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=prepare_public_jobs(args.split,args.cache,args.out)
    print(json.dumps({'selected':result['selected'],'businesses':len(result['businesses']),
                      'jobs_sha256':result['jobs_sha256']}))


if __name__=='__main__':
    main()
