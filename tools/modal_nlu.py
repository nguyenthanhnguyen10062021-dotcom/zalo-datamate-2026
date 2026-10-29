"""Private, bounded Modal generation worker; never imports runtime data/scorer."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import modal


PROFILE = 'vuonghungnguyen07'
if modal.is_local():
    from modal.config import _profile
    if _profile != PROFILE:
        raise ValueError('Invoke with --profile vuonghungnguyen07 before app initialization')
MODEL = 'Qwen/Qwen2.5-7B-Instruct'
REVISION = 'a09a35458c702b33eeacc393d103063234e8bc28'
VLLM_IMAGE = 'nvidia/cuda:12.9.0-devel-ubuntu22.04 + Python3.12 + vllm0.21.0'
# Follow Modal's tested vLLM image recipe: an explicit Python avoids registry
# images whose Python installation the platform cannot identify.
image = (modal.Image.from_registry('nvidia/cuda:12.9.0-devel-ubuntu22.04',add_python='3.12')
         .entrypoint([]).uv_pip_install('vllm==0.21.0').env({
    'HF_HUB_DISABLE_TELEMETRY':'1', 'VLLM_LOGGING_LEVEL':'WARNING',
    'DO_NOT_TRACK':'1', 'VLLM_NO_USAGE_STATS':'1', 'HF_HOME':'/tmp/datamate-hf',
}))
app = modal.App('datamate-nlu-baseline-v1')


@app.function(image=image,gpu=['A10','L4'],cpu=(4,4),memory=(32768,32768),
    timeout=3600,startup_timeout=900,max_containers=1,min_containers=0,
    buffer_containers=0,scaledown_window=5,
    serialized=True,include_source=False)
def generate_batch(jobs, schema, sampling):
    # Dependencies stay in the pinned Linux image, never the local core venv.
    import platform
    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    import torch
    import vllm

    started = time.monotonic()
    snapshot = Path(snapshot_download(MODEL,revision=REVISION,cache_dir='/tmp/datamate-hf',
        allow_patterns=['*.json','*.txt','*.safetensors','LICENSE','README.md']))
    hashes = {}
    for path in sorted(snapshot.iterdir()):
        if path.is_file():
            with path.open('rb') as stream:
                hashes[path.name] = hashlib.file_digest(stream,'sha256').hexdigest()
    engine = LLM(model=str(snapshot),tokenizer=str(snapshot),trust_remote_code=False,
        dtype='bfloat16',max_model_len=4096,max_num_seqs=16,max_num_batched_tokens=4096,
        gpu_memory_utilization=0.86,enforce_eager=True,seed=sampling['seed'])
    tokenizer = engine.get_tokenizer()
    params = SamplingParams(temperature=sampling['temperature'],max_tokens=sampling['max_tokens'],
        seed=sampling['seed'],structured_outputs=StructuredOutputsParams(json=schema))
    yield json.dumps(dict(record_type='worker_metadata',model=MODEL,revision=REVISION,
        model_files_sha256=hashes,vllm_version=vllm.__version__,python=platform.python_version(),
        torch_version=str(torch.__version__),gpu=torch.cuda.get_device_name(),
        vram_bytes=torch.cuda.get_device_properties(0).total_memory,
        model_load_seconds=time.monotonic()-started,image=VLLM_IMAGE),ensure_ascii=False,allow_nan=False)
    for start in range(0,len(jobs),16):
        active = []
        for job in jobs[start:start+16]:
            tokens = tokenizer.apply_chat_template(job['messages'],tokenize=True,add_generation_prompt=True)
            if len(tokens) + sampling['max_tokens'] > 4096:
                yield json.dumps(dict(request_id=job['request_id'],error='context_overflow',prompt_tokens=len(tokens)))
            else:
                active.append(job)
        if not active:
            continue
        tick = time.monotonic()
        outputs = engine.chat([j['messages'] for j in active],sampling_params=params,use_tqdm=False)
        elapsed = time.monotonic()-tick
        if len(outputs) != len(active):
            raise RuntimeError('Backend output cardinality changed')
        for job,result in zip(active,outputs):
            output = result.outputs[0]
            yield json.dumps(dict(request_id=job['request_id'],text=output.text,finish_reason=output.finish_reason,
                prompt_tokens=len(result.prompt_token_ids),completion_tokens=len(output.token_ids),
                batch_seconds=elapsed,batch_size=len(active),
                peak_vram_bytes=torch.cuda.max_memory_allocated()),ensure_ascii=False,allow_nan=False)


@app.local_entrypoint()
def main(jobs: str, out: str, stage: str, budget_policy: str = 'baseline_v1'):
    """Use --profile explicitly; no detached deployment or persistent model volume."""
    from modal.config import _profile
    if _profile != PROFILE:
        raise ValueError('Invoke with --profile vuonghungnguyen07')
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    from tools.nlu_budget import reserve_policy_call
    target = Path(out).resolve()
    if not target.is_relative_to(root/'reports'):
        raise ValueError('Output must remain in ignored reports/')
    payload = json.loads(Path(jobs).read_text(encoding='utf-8'))
    content = {k:v for k,v in payload.items() if k!='jobs_sha256'}
    digest = hashlib.sha256(json.dumps(content,ensure_ascii=False,sort_keys=True,
                          separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if payload['jobs_sha256'] != digest:
        raise ValueError('Job payload changed')
    if target.exists():
        raise ValueError('Generation artifact already exists; never overwrite')
    reservation = reserve_policy_call(root,budget_policy,stage,PROFILE)
    sanitized = [dict(request_id=j['request_id'],messages=j['messages']) for j in payload['jobs']]
    # Modal's local_entrypoint already owns app.run; this watchdog only stops this app.
    app_id = app.app_id
    def stop_own_app():
        if app_id and app_id.startswith('ap-'):
            subprocess.run([sys.executable,'-m','modal','app','stop',app_id,'--yes','--profile',PROFILE],
                           capture_output=True,timeout=60)
    watchdog = threading.Timer(4560,stop_own_app)
    watchdog.daemon = True
    started = time.monotonic()
    target.parent.mkdir(parents=True,exist_ok=True)
    count = 0
    watchdog.start()
    try:
        with target.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps(dict(record_type='run_metadata',jobs_sha256=digest,
                reservation=reservation,app_id=app_id,profile=PROFILE),ensure_ascii=False)+'\n')
            stream.flush()
            for wire in generate_batch.remote_gen(sanitized,payload['schema'],payload['sampling']):
                row = json.loads(wire)
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                stream.flush()
                if row.get('request_id'):
                    count += 1
                    if count % 16 == 0 or count == len(sanitized):
                        print(f'Generated {count}/{len(sanitized)} requests',flush=True)
    finally:
        watchdog.cancel()
        receipt = dict(app_id=app_id,profile=PROFILE,stage=stage,generated=count,
                       total=len(sanitized),local_elapsed_seconds=time.monotonic()-started,
                       reservation=reservation,cleanup='non-detached app context must stop on exit')
        with target.with_suffix('.receipt.json').open('x',encoding='utf-8') as stream:
            json.dump(receipt,stream,indent=2)
