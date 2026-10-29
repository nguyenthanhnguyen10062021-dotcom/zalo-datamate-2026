"""Deterministic QueryPlan v1 validation and execution above the business API."""
from .contract import PlanValidationError, validate_plan
from .executor import ExecutionResult, QueryExecutor, UnsupportedCapability, check_capability

__all__ = ['ExecutionResult', 'PlanValidationError', 'QueryExecutor', 'validate_plan',
           'UnsupportedCapability', 'check_capability']
