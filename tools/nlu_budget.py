"""Conservative pre-dispatch cost reservations; no SDK or cloud calls."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


PROFILE = 'vuonghungnguyen07'
LIMIT_USD = 25.0
RESERVE_USD = 5.0
SETUP_ENVELOPE_USD = 3.0
CALL_ENVELOPE_USD = 4.0
MAX_CALLS = 4
PUBLIC_LIMIT_USD = 5.0
PUBLIC_MARGIN_USD = 1.0
PUBLIC_CALL_ENVELOPE_USD = 4.0
PUBLIC_MAX_CALLS = 1
# Pinned public rates, conservative requested maxima; no warm pool/persistent volume.
RATE_PER_SECOND = 0.000306 + 4 * 0.0000131 + 32 * 0.00000222
EXECUTION_SECONDS = 3600
STARTUP_SECONDS = 900
SCALEDOWN_SECONDS = 5


def _reserve(path, stage, profile, *, initial, expected, fixed_usd, call_envelope,
             max_calls, total_key, require_new=False):
    path = Path(path)
    if profile != PROFILE:
        raise ValueError('Wrong Modal profile')
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    with lock.open('x', encoding='utf-8') as stream:
        stream.write('exclusive cost reservation\n')
    try:
        if path.exists():
            if require_new:
                raise ValueError('Public budget ledger already exists; reservation exhausted')
            ledger = json.loads(path.read_text(encoding='utf-8'))
            if any(ledger.get(key) != value for key,value in expected.items()):
                raise ValueError('Budget ledger/profile changed')
        else:
            ledger = dict(initial)
        if type(ledger.get('calls')) is not list:
            raise ValueError('Budget ledger/profile changed')
        projected = fixed_usd + (len(ledger['calls'])+1)*call_envelope
        if len(ledger['calls']) >= max_calls or projected > ledger['limit_usd']:
            raise ValueError('Trial cost reservation exhausted; no dispatch permitted')
        if RATE_PER_SECOND * (EXECUTION_SECONDS+STARTUP_SECONDS+SCALEDOWN_SECONDS) * 2 > call_envelope:
            raise ValueError('Resource/time bound exceeds conservative per-call envelope')
        reservation = dict(id=uuid.uuid4().hex,stage=stage,envelope_usd=call_envelope,
            reserved_at_utc=datetime.now(timezone.utc).isoformat(),
            maximum_compute_usd=RATE_PER_SECOND*(EXECUTION_SECONDS+STARTUP_SECONDS+SCALEDOWN_SECONDS),
            status='reserved_before_dispatch')
        ledger['calls'].append(reservation)
        ledger[total_key] = projected
        temporary = path.with_suffix('.pending')
        with temporary.open('x',encoding='utf-8') as stream:
            json.dump(ledger,stream,indent=2)
        temporary.replace(path)
        return reservation
    finally:
        lock.unlink()


def reserve_call(path, stage, profile):
    """Reserve one original baseline call without changing its ledger contract."""
    initial = dict(profile=PROFILE,limit_usd=LIMIT_USD,reserve_usd=RESERVE_USD,
                   setup_envelope_usd=SETUP_ENVELOPE_USD,calls=[])
    expected = {key:value for key,value in initial.items() if key != 'calls'}
    return _reserve(path,stage,profile,initial=initial,expected=expected,
        fixed_usd=SETUP_ENVELOPE_USD+RESERVE_USD,call_envelope=CALL_ENVELOPE_USD,
        max_calls=MAX_CALLS,total_key='total_reserved_with_setup_and_margin_usd')


def reserve_public_submission_call(path, stage, profile):
    """Reserve the separately authorized single public-test generation call."""
    initial = dict(profile=PROFILE,authorization='public_submission_v1',
                   limit_usd=PUBLIC_LIMIT_USD,margin_usd=PUBLIC_MARGIN_USD,calls=[])
    expected = {key:value for key,value in initial.items() if key != 'calls'}
    return _reserve(path,stage,profile,initial=initial,expected=expected,
        fixed_usd=PUBLIC_MARGIN_USD,call_envelope=PUBLIC_CALL_ENVELOPE_USD,
        max_calls=PUBLIC_MAX_CALLS,total_key='total_reserved_with_margin_usd',require_new=True)


def reserve_policy_call(root, policy, stage, profile):
    """Map a CLI policy name to its fixed ignored ledger; no arbitrary reset path."""
    root = Path(root)
    if policy == 'baseline_v1':
        return reserve_call(root/'reports/nlu_baseline/v1/budget.json',stage,profile)
    if policy == 'public_submission_v1':
        return reserve_public_submission_call(
            root/'reports/public_submission/v1/budget.json',stage,profile)
    if policy == 'semantic_safety_v1':
        # New user authorization after the negative public score: Modal reruns
        # allowed without a requested cost cap. Bound this experiment to three
        # calls anyway, independently of the exhausted historical ledgers.
        initial = dict(profile=PROFILE,authorization='semantic_safety_v1',
            limit_usd=13.0,margin_usd=1.0,calls=[])
        expected = {key:value for key,value in initial.items() if key != 'calls'}
        return _reserve(root/'reports/semantic_safety/v1/budget.json',stage,profile,
            initial=initial,expected=expected,fixed_usd=1.0,call_envelope=4.0,
            max_calls=3,total_key='total_reserved_with_margin_usd')
    raise ValueError('Unknown budget policy; no dispatch permitted')


def reserve_semantic_parallel_call(root, workers, profile, *, recovery=False):
    """New max-10-GPU authorization; leave every previous experiment ledger alone."""
    if type(workers) is not int or not 1 <= workers <= 10:
        raise ValueError('Parallel workers must be between 1 and 10')
    maximum = workers * RATE_PER_SECOND * (900 + 900 + SCALEDOWN_SECONDS)
    if maximum * 2 > 16.0:
        raise ValueError('Parallel resource/time bound exceeds envelope')
    if type(recovery) is not bool:
        raise ValueError('Recovery must be boolean')
    policy = 'semantic_safety_parallel_recovery_v1' if recovery else 'semantic_safety_parallel_v1'
    filename = 'parallel-recovery-budget.json' if recovery else 'parallel-budget.json'
    initial = dict(profile=PROFILE,authorization=policy,
        limit_usd=17.0,margin_usd=1.0,workers=workers,calls=[])
    expected = {key:value for key,value in initial.items() if key != 'calls'}
    reservation = _reserve(Path(root)/'reports/semantic_safety/v1'/filename,
        policy,profile,initial=initial,expected=expected,
        fixed_usd=1.0,call_envelope=16.0,max_calls=1,
        total_key='total_reserved_with_margin_usd',require_new=True)
    # _reserve's original bound describes one historical worker; expose the
    # actual new pool bound in the returned receipt as a separate quantity.
    return reservation | {'workers':workers,'parallel_maximum_compute_usd':maximum}
