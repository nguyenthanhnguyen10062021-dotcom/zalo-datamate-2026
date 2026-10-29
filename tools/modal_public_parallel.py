"""User-authorized acceleration of the remaining frozen public requests."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import modal
from tools.modal_nlu import generate_batch, image, PROFILE

app = modal.App('datamate-public-parallel-v1')
# Same exact frozen worker implementation, with a bounded 7-container pool.
parallel_batch = app.function(name='generate_public_shard',image=image,
    gpu=['A10','L4'],cpu=(4,4),memory=(32768,32768),
    timeout=480,startup_timeout=120,max_containers=7,min_containers=0,
    buffer_containers=0,scaledown_window=5,
    serialized=True,is_generator=True,include_source=False)(inspect.unwrap(generate_batch._raw_f_))


@app.local_entrypoint()
def accelerate(jobs: str, existing: str, out: str, workers: int = 7):
    from modal.config import _profile
    from tools.nlu_budget import RATE_PER_SECOND

    if _profile != PROFILE or not 1 <= workers <= 7:
        raise ValueError('Profile/worker limit mismatch')
    root = Path(__file__).resolve().parents[1]
    # Integrity uses the existing core venv; the Modal SDK env is intentionally minimal.
    subprocess.run([str(root/'.venv/Scripts/python.exe'),'-c',
        'from pathlib import Path; import sys; from tools.public_jobs import load_public_jobs; '
        'load_public_jobs(Path(sys.argv[1]))',str(Path(jobs).resolve())],cwd=root,check=True)
    payload = json.loads(Path(jobs).read_text(encoding='utf-8'))
    target = Path(out).resolve()
    if not target.is_relative_to(root/'reports') or target.exists():
        raise ValueError('Use a new ignored reports artifact')
    budget_path = root/'reports/public_submission/v1/budget.json'
    budget = json.loads(budget_path.read_text(encoding='utf-8'))
    if (budget.get('authorization') != 'public_submission_v1'
            or budget.get('profile') != PROFILE or len(budget.get('calls',[])) != 1):
        raise ValueError('Original public authorization ledger mismatch')
    original_bound = budget['calls'][0]['maximum_compute_usd']
    parallel_bound = workers*RATE_PER_SECOND*(480+120+5)
    prior_failed_bound = 7*RATE_PER_SECOND*30
    if original_bound + parallel_bound + prior_failed_bound + 1.0 > 5.0:
        raise ValueError('Combined original + parallel + margin exceeds 5 USD cap')
    # Exclusive extension receipt prevents a second acceleration launch.
    with target.with_suffix('.budget.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(authorization='user requested up to 10 GPUs',workers=workers,
            original_maximum_compute_usd=original_bound,
            parallel_maximum_compute_usd=parallel_bound,margin_usd=1.0,
            prior_failed_maximum_usd=prior_failed_bound,
            combined_maximum_usd=original_bound+parallel_bound+prior_failed_bound+1.0,
            limit_usd=5.0,baseline_ledger_unchanged=True),stream,indent=2)
    # Snapshot the completed prefix; the original worker keeps making progress.
    records = [json.loads(line) for line in Path(existing).read_text(encoding='utf-8').splitlines()
               if line.strip()]
    completed = {row['request_id'] for row in records if 'request_id' in row}
    remaining = [dict(request_id=row['request_id'],messages=row['messages'])
                 for row in payload['jobs'] if row['request_id'] not in completed]
    shards = [remaining[index::workers] for index in range(workers)]
    function = parallel_batch
    app_id = app.app_id
    def stop():
        subprocess.run([sys.executable,'-m','modal','app','stop',app_id,'--yes',
                        '--profile',PROFILE],capture_output=True,timeout=30)
    watchdog = threading.Timer(570,stop)
    watchdog.daemon = True
    lock = threading.Lock()
    count = 0
    started = time.monotonic()
    watchdog.start()
    try:
        with target.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps(dict(record_type='run_metadata',
                jobs_sha256=payload['jobs_sha256'],app_id=app_id,profile=PROFILE,
                authorization='user requested up to 10 GPUs',workers=workers,
                retained_prefix=len(completed),selected=len(remaining)))+'\n')
            stream.flush()
            def consume(shard):
                nonlocal count
                if not shard:
                    return
                for wire in function.remote_gen(shard,payload['schema'],payload['sampling']):
                    row = json.loads(wire)
                    with lock:
                        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                        stream.flush()
                        if 'request_id' in row:
                            count += 1
                            if count % 16 == 0 or count == len(remaining):
                                print(f'Parallel generated {count}/{len(remaining)}; '
                                      f'prefix {len(completed)} retained',flush=True)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for future in as_completed([pool.submit(consume,shard) for shard in shards]):
                    future.result()
    finally:
        watchdog.cancel()
        with target.with_suffix('.receipt.json').open('x',encoding='utf-8') as stream:
            with target.open('rb') as artifact:
                digest = hashlib.file_digest(artifact,'sha256').hexdigest()
            json.dump(dict(app_id=app_id,workers=workers,generated=count,
                total=len(remaining),elapsed_seconds=time.monotonic()-started,
                jobs_sha256=payload['jobs_sha256'],artifact_sha256=digest),stream,indent=2)
