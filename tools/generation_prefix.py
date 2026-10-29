"""Freeze a complete transport prefix and retry only missing request IDs."""
import json


def pending_jobs(payload, raw):
    complete = raw[:raw.rfind(b'\n')+1]
    records = [json.loads(line) for line in complete.decode('utf-8').splitlines() if line.strip()]
    metadata = [r for r in records if r.get('record_type') == 'run_metadata']
    if len(metadata) != 1 or metadata[0].get('jobs_sha256') != payload['jobs_sha256']:
        raise ValueError('Existing prefix is not bound to frozen jobs')
    expected = {j['request_id'] for j in payload['jobs']}
    seen = set()
    for row in records:
        if row.get('record_type') in ('run_metadata','worker_metadata'):
            continue
        rid = row.get('request_id')
        if rid not in expected or rid in seen:
            raise ValueError('Unknown/duplicate prefix request')
        seen.add(rid)
    # Even an error output is complete: do not retry based on its content.
    return complete, [j for j in payload['jobs'] if j['request_id'] not in seen]
