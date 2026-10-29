"""Generation and plan-attempt records; no model, transport or file access."""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Generation:
    text: str
    finish_reason: str = 'stop'
    metadata: dict = field(default_factory=dict)


class GenerationFailure(RuntimeError):
    """An expected backend failure, distinct from an implementation exception."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Backend(Protocol):
    def generate(self, messages: list[dict], schema: dict, sampling: dict) -> Generation: ...


@dataclass(frozen=True)
class PlanAttempt:
    plan: dict | None
    status: str
    stage: str
    reason: str | None
    generation: Generation | None = None
