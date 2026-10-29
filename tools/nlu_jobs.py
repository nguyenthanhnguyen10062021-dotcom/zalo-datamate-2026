"""Freeze train-only evaluation protocol and bounded model jobs; never opens gold."""
from collections import Counter, defaultdict, deque
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nlu.prompt import PROMPT_VERSION, build_messages
from nlu.schema import plan_schema
from verification.manifest import file_hash, object_hash, questions


def write_new(path, payload):
    path = Path(path)
    if not path.resolve().is_relative_to((ROOT / 'reports').resolve()):
        raise ValueError('Artifacts must remain in ignored reports/')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def cache_hashes(cache, businesses):
    return {bid: {name: file_hash(Path(cache) / bid / name) for name in
                  ('don_hang.parquet', 'dong_hang.parquet', 'mat_hang.parquet', 'cua_hang.json')}
            for bid in sorted(businesses)}


def make_protocol(records, seed):
    businesses = sorted({r['business_id'] for r in records},
        key=lambda bid: sha256((seed + '\0' + bid).encode()).hexdigest())
    if len(businesses) < 3:
        raise ValueError('Need at least three businesses for dev/calibration/evaluation')
    n_dev, n_cal = max(1, len(businesses) * 3 // 5), max(1, len(businesses) // 5)
    roles = {bid: ('development' if i < n_dev else
                   'calibration' if i < n_dev + n_cal else 'evaluation')
             for i, bid in enumerate(businesses)}
    if len({r['id'] for r in records}) != len(records):
        raise ValueError('Duplicate question ids')
    return dict(version='1.0', seed=seed, partition_unit='business_id',
        exposure='retrospective; global train README mapping; not blind or fold-clean',
        businesses=roles, entries=[dict(id=r['id'], business_id=r['business_id'],
            role=roles[r['business_id']], question_sha256=object_hash(r)) for r in records])


def freeze_protocol(train, cache, out, seed='datamate-nlu-v1'):
    train, cache = Path(train).resolve(), Path(cache).resolve()
    records = questions(train / 'questions.jsonl')
    payload = make_protocol(records, seed)
    payload.update(train_root=str(train), cache_root=str(cache),
        sources={name: file_hash(train/name) for name in ('questions.jsonl', 'rulebook.md', 'calendar.csv')},
        cache_sha256=cache_hashes(cache, payload['businesses']))
    payload['protocol_sha256'] = object_hash(payload)
    write_new(out, payload)
    return payload


def load_protocol(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload['protocol_sha256'] != object_hash({k:v for k,v in payload.items() if k != 'protocol_sha256'}):
        raise ValueError('Protocol payload changed')
    train, cache = Path(payload['train_root']), Path(payload['cache_root'])
    if any(file_hash(train/name) != value for name,value in payload['sources'].items()):
        raise ValueError('Corpus/rulebook/calendar changed')
    if cache_hashes(cache, payload['businesses']) != payload['cache_sha256']:
        raise ValueError('Cache snapshot changed')
    records = questions(train/'questions.jsonl')
    if make_protocol(records, payload['seed'])['entries'] != payload['entries']:
        raise ValueError('Protocol assignment changed')
    return payload, records


def balanced_sample(entries, limit=None):
    groups = defaultdict(list)
    for entry in entries:
        groups[entry['business_id']].append(entry)
    queues = [deque(sorted(rows, key=lambda r: r['question_sha256']))
              for _,rows in sorted(groups.items())]
    selected = []
    while queues and (limit is None or len(selected) < limit):
        remaining = []
        for queue in queues:
            if limit is not None and len(selected) == limit:
                break
            selected.append(queue.popleft())
            if queue:
                remaining.append(queue)
        queues = remaining
    return selected


def table_context(tables, as_of_date, limit=24):
    """Only bounded labels/structure, not transactions, amounts or reference answers."""
    import pandas as pd
    orders, products = tables['don_hang'], tables['mat_hang']
    known = orders[pd.to_datetime(orders['ngay_dat']).dt.normalize() <= pd.Timestamp(as_of_date)]
    labels = {}
    for name,frame,column in (
        ('channels',known,'kenh_ban'), ('payments',known,'hinh_thuc_tt'),
        ('customer_groups',known,'nhom_khach'), ('product_groups',products,'nhom_hang'),
        ('base_units',products,'don_vi_co_ban')):
        values = frame[column].dropna().unique().tolist() if column in frame else []
        valid = sorted(v for v in values if isinstance(v,str) and v.strip())
        labels[name] = dict(values=valid[:limit], complete=len(valid) <= limit,
                            invalid_label_types=len(values)-len(valid))
    return dict(available_columns={name: sorted(frame.columns.tolist())
                for name,frame in tables.items() if isinstance(frame,pd.DataFrame)},
                known_labels=labels, catalog_policy='static canonical catalog; order labels <= as_of_date')


def prepare_jobs(protocol_path, role, out, limit=None):
    from verification.runner import _load_cache
    protocol, records = load_protocol(protocol_path)
    by_id = {r['id']:r for r in records}
    eligible = [e for e in protocol['entries'] if role == 'all' or e['role'] == role]
    selected = balanced_sample(eligible, limit)
    groups = defaultdict(list)
    for entry in selected:
        groups[entry['business_id']].append(entry)
    jobs = []
    for bid,entries in sorted(groups.items()):
        tables,_ = _load_cache(Path(protocol['cache_root']) / bid)
        for entry in entries:
            row = by_id[entry['id']]
            messages = build_messages(row['question'],row['as_of_date'],table_context(tables,row['as_of_date']))
            jobs.append(dict(id=row['id'], business_id=bid, as_of_date=row['as_of_date'],
                role=entry['role'], question_sha256=entry['question_sha256'],
                request_id=object_hash({'protocol':protocol['protocol_sha256'],'question':entry['question_sha256']}),
                messages=messages, messages_sha256=object_hash(messages)))
        del tables
    paths = [*ROOT.joinpath('nlu').glob('*.py'), Path(__file__)]
    payload = dict(version='1.0', protocol_path=str(Path(protocol_path).resolve()),
        protocol_sha256=protocol['protocol_sha256'], role=role, total_eligible=len(eligible),
        selected=len(jobs), outside_selection=len(eligible)-len(jobs), prompt_version=PROMPT_VERSION,
        schema=plan_schema(), sampling={'temperature':0.0,'seed':20261029,'max_tokens':768},
        code_sha256={str(p.relative_to(ROOT)).replace('\\','/'):file_hash(p) for p in paths}, jobs=jobs)
    payload['jobs_sha256'] = object_hash(payload)
    write_new(out,payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    freeze = sub.add_parser('freeze')
    freeze.add_argument('--train',type=Path,default=Path('train'))
    freeze.add_argument('--cache',type=Path,required=True)
    freeze.add_argument('--out',type=Path,required=True)
    jobs = sub.add_parser('jobs')
    jobs.add_argument('--protocol',type=Path,required=True)
    jobs.add_argument('--role',choices=('development','calibration','evaluation','all'),required=True)
    jobs.add_argument('--limit',type=int)
    jobs.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        result = freeze_protocol(args.train,args.cache,args.out)
        print(json.dumps({'total':len(result['entries']),'business_partitions':dict(Counter(result['businesses'].values()))}))
    else:
        if args.limit is not None and args.limit <= 0:
            parser.error('limit must be positive')
        result = prepare_jobs(args.protocol,args.role,args.out,args.limit)
        print(json.dumps({k:result[k] for k in ('role','total_eligible','selected','outside_selection','jobs_sha256')}))


if __name__ == '__main__':
    main()
