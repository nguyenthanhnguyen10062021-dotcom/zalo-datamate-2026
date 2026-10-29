"""Run frozen public jobs on up to ten GPUs with no outcome-based selection."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import inspect
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import modal
from tools.modal_nlu import generate_batch, image, PROFILE


app = modal.App('datamate-semantic-public-parallel-v1')
parallel_batch = app.function(image=image,gpu=['A10','L4'],cpu=(4,4),
    memory=(32768,32768),timeout=900,startup_timeout=900,max_containers=10,
    min_containers=0,buffer_containers=0,scaledown_window=5,
    serialized=True,is_generator=True,include_source=False)(inspect.unwrap(generate_batch._raw_f_))


@app.local_entrypoint()
def main(jobs: str, out: str, workers: int = 10, existing: str = ''):
    from modal.config import _profile
    from tools.nlu_budget import reserve_semantic_parallel_call
    from tools.generation_prefix import pending_jobs
    if _profile != PROFILE or not 1 <= workers <= 10:
        raise ValueError('Profile/worker limit mismatch')
    root = Path(__file__).resolve().parents[1]
    target = Path(out).resolve()
    if not target.is_relative_to(root/'reports') or target.exists():
        raise ValueError('Use a new ignored reports artifact')
    # Full data/source integrity runs in the existing core environment, before
    # any GPU dispatch. Only allowlisted inference inputs reach the workers.
    subprocess.run([str(root/'.venv/Scripts/python.exe'),'-c',
        'from pathlib import Path; import sys; from tools.public_jobs import load_public_jobs; '
        'load_public_jobs(Path(sys.argv[1]))',str(Path(jobs).resolve())],cwd=root,check=True)
    payload = json.loads(Path(jobs).read_text(encoding='utf-8'))
    retained = None
    selected = payload['jobs']
    if existing:
        complete,selected = pending_jobs(payload,Path(existing).read_bytes())
        retained = target.with_suffix('.retained.jsonl')
        with retained.open('xb') as stream:
            stream.write(complete)
        retained = dict(path=str(retained),sha256=hashlib.sha256(complete).hexdigest(),
                        completed=len(payload['jobs'])-len(selected))
    sanitized = [dict(request_id=j['request_id'],messages=j['messages']) for j in selected]
    if not sanitized:
        raise ValueError('No inference jobs')
    workers = min(workers,len(sanitized))
    reservation = reserve_semantic_parallel_call(root,workers,PROFILE,recovery=bool(existing))
    shards = [sanitized[index::workers] for index in range(workers)]
    expected = {j['request_id'] for j in sanitized}
    seen = set()
    lock = threading.Lock()
    app_id = app.app_id
    def stop_own_app():
        subprocess.run([sys.executable,'-m','modal','app','stop',app_id,'--yes',
            '--profile',PROFILE],capture_output=True,timeout=30)
    watchdog = threading.Timer(1840,stop_own_app)
    watchdog.daemon = True
    started = time.monotonic()
    target.parent.mkdir(parents=True,exist_ok=True)
    watchdog.start()
    try:
        with target.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps(dict(record_type='run_metadata',
                jobs_sha256=payload['jobs_sha256'],app_id=app_id,profile=PROFILE,
                workers=workers,reservation=reservation,retained_prefix=retained))+'\n')
            stream.flush()
            def consume(shard):
                for wire in parallel_batch.remote_gen(shard,payload['schema'],payload['sampling']):
                    row = json.loads(wire)
                    with lock:
                        rid = row.get('request_id')
                        if rid is not None:
                            if rid not in expected or rid in seen:
                                raise ValueError('Unexpected/duplicate generation')
                            seen.add(rid)
                        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                        stream.flush()
                        if rid is not None and (len(seen)%50 == 0 or len(seen)==len(expected)):
                            print(f'Generated {len(seen)}/{len(expected)} across {workers} shards',flush=True)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for future in as_completed([pool.submit(consume,shard) for shard in shards]):
                    future.result()
    finally:
        watchdog.cancel()
        with target.with_suffix('.receipt.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(app_id=app_id,profile=PROFILE,workers=workers,generated=len(seen),
                total=len(expected),local_elapsed_seconds=time.monotonic()-started,
                reservation=reservation,cleanup='non-detached app stops on exit'),stream,indent=2)
