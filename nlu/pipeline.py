"""Keep model generation failures separate from deterministic executor outcomes."""
from queryplan import PlanValidationError, UnsupportedCapability, check_capability

from .contract import Generation, GenerationFailure, PlanAttempt
from .parser import NLUParseError, parse_plan
from .semantic import GATE_VERSION, rejection_reason


def inspect_generation(generation: Generation) -> PlanAttempt:
    if not isinstance(generation, Generation):
        raise TypeError('Backend must return Generation')
    if generation.finish_reason != 'stop':
        return PlanAttempt(None, 'incomplete_generation', 'generation',
                           f'finish_reason={generation.finish_reason}', generation)
    try:
        plan = parse_plan(generation.text)
    except NLUParseError as exc:
        return PlanAttempt(None, 'invalid_json', 'parse', str(exc), generation)
    except PlanValidationError as exc:
        return PlanAttempt(None, 'invalid_plan', exc.stage, str(exc), generation)
    if plan['status'] == 'supported':
        try:
            check_capability(plan)
        except UnsupportedCapability as exc:
            return PlanAttempt(plan, 'unsupported_capability', 'capability', str(exc), generation)
    return PlanAttempt(plan, 'plan_ready', 'semantic', None, generation)


def generate_plan(messages, backend, schema, sampling) -> PlanAttempt:
    try:
        generation = backend.generate(messages, schema, sampling)
    except GenerationFailure as exc:
        return PlanAttempt(None, exc.code, 'generation', str(exc))
    return inspect_generation(generation)


def execute_attempt(attempt: PlanAttempt, executor, question_id: str, *, question: str | None = None) -> dict:
    """Return submission plus sidecar; let unexpected executor failures propagate."""
    if attempt.plan is None or attempt.status != 'plan_ready':
        return dict(submission={'id': question_id, 'type': 'abstain', 'reason': attempt.reason},
                    status=attempt.status, stage=attempt.stage, plan=attempt.plan)
    if question is not None:
        reason = rejection_reason(question, attempt.plan)
        if reason is not None:
            return dict(submission={'id': question_id, 'type': 'abstain', 'reason': reason},
                        status='semantic_rejected', stage='semantic', plan=attempt.plan,
                        semantic_gate=GATE_VERSION, semantic_reason=reason)
    result = executor.execute(attempt.plan)
    return dict(submission=result.answer.to_submission(question_id),
                status=result.status, stage=result.stage, plan=attempt.plan)
