"""Merge user-authorized GPU pools by fixed primary precedence, never by answers."""
import argparse
import json
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0,str(_ROOT))

from run_public_submission import generation_index
from tools.public_jobs import ROOT, load_public_jobs
from verification.manifest import file_hash


def merge(jobs_path, primary, secondary, out):
    jobs,_ = load_public_jobs(Path(jobs_path))
    expected = {row['request_id'] for row in jobs['jobs']}
    selected,metadata,sources = {},[],[]
    overlaps = 0
    for path in (Path(primary),Path(secondary)):
        # A concurrently-flushed file may end with a partial line: retain only
        # newline-terminated records, and reject every malformed complete line.
        text = path.read_bytes()
        complete = text[:text.rfind(b'\n')+1]
        raw = [json.loads(line) for line in complete.decode('utf-8').splitlines() if line.strip()]
        index,details = generation_index(raw,expected)
        binding = [row for row in details if row.get('record_type') == 'run_metadata']
        if len(binding) != 1 or binding[0].get('jobs_sha256') != jobs['jobs_sha256']:
            raise ValueError('Source artifact is not bound to frozen public jobs')
        overlaps += len(set(selected) & set(index))
        for request_id,row in index.items():
            selected.setdefault(request_id,row)
        metadata.extend(row for row in details if row.get('record_type') == 'worker_metadata')
        sources.append(dict(path=str(path),sha256=file_hash(path),records=len(index),
                            run_metadata=binding[0]))
    if set(selected) != expected:
        return dict(ready=False,received=len(selected),expected=len(expected))
    out = Path(out)
    if not out.resolve().is_relative_to((ROOT/'reports').resolve()):
        raise ValueError('Merged artifact must remain under ignored reports/')
    with out.open('x',encoding='utf-8',newline='\n') as stream:
        rows = [dict(record_type='run_metadata',jobs_sha256=jobs['jobs_sha256'],
                     merge_policy='primary precedence independent of answer',
                     overlap_records=overlaps,sources=sources),*metadata,
                *(selected[row['request_id']] for row in jobs['jobs'])]
        for row in rows:
            stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    return dict(ready=True,received=len(selected),expected=len(expected),overlaps=overlaps)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('jobs','primary','secondary','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(merge(args.jobs,args.primary,args.secondary,args.out)))


if __name__ == '__main__':
    main()
