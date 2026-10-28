"""Offline plan execution. Unexpected implementation failures deliberately propagate."""
from dataclasses import dataclass

from business import Answer, DataError, Periods, SalesMetrics, UnsupportedRule
from business.periods import as_date

from .contract import PlanValidationError, validate_plan
from .resolution import (AmbiguousEntityError, MissingInformation, PeriodResolutionError, ResolutionError,
                         resolve_filters, resolve_period)


class UnsupportedCapability(ValueError):
    pass


def _capability(plan):
    op, filters = plan['operation'], plan['filters']
    if filters['unit_mention'] is not None and op != 'quantity':
        raise UnsupportedCapability('unit_mention chỉ hỗ trợ quantity')
    if op in ('cancellation_rate', 'top_customers') and any(filters[k] is not None
            for k in ('product_mentions', 'product_group_mention')):
        raise UnsupportedCapability(f'{op} chỉ hỗ trợ bộ lọc cấp đơn ở v1')
    if op.startswith('top_'):
        allowed = ('quantity', 'revenue') if op == 'top_products' else ('revenue', 'orders')
        if plan['ranking']['metric'] not in allowed:
            raise UnsupportedCapability(f'Metric không hỗ trợ cho {op}')
    comparison = plan['comparison_period']
    if comparison is not None:
        kind, main = comparison['kind'], plan['period']['kind']
        if kind == 'before_period' and main != 'tet':
            raise UnsupportedCapability('before_period chỉ hỗ trợ so trước Tết')
        if kind == 'previous_month_same_elapsed' and main != 'this_month':
            raise UnsupportedCapability('same_elapsed chỉ hỗ trợ so tháng này')


@dataclass(frozen=True)
class ExecutionResult:
    answer: Answer
    status: str
    stage: str


def _abstain(status, stage, reason):
    return ExecutionResult(Answer('abstain', reason=f'{status}: {reason}'), status, stage)


class QueryExecutor:
    """Caller supplies one business's tables and the correct split's rulebook/calendar.

    The executor neither loads files nor writes logs. Retain status/stage alongside
    Answer when logging locally; submission serialization remains Answer.to_submission.
    """

    def __init__(self, tables: dict, rules, as_of_date, calendar_path=None):
        self.tables, self.rules = tables, rules
        self.as_of = as_date(as_of_date)
        self.calendar_path = calendar_path

    def execute(self, raw_plan: dict) -> ExecutionResult:
        try:
            plan = validate_plan(raw_plan)
        except PlanValidationError as exc:
            return _abstain('invalid_plan', exc.stage, str(exc))
        if plan['status'] == 'unsupported':
            return _abstain('unsupported_plan', 'semantic', plan['unsupported_reason'])
        try:
            _capability(plan)
        except UnsupportedCapability as exc:
            return _abstain('unsupported_capability', 'capability', str(exc))

        stage = 'period'
        try:
            periods = Periods(self.rules, self.as_of, self.calendar_path)
            period = resolve_period(plan['period'], periods)
            comparison = plan['comparison_period']
            if comparison is not None:
                comparison = resolve_period(comparison, periods, period)
            elif plan['operation'] == 'revenue_growth':
                comparison = resolve_period({'kind': 'previous_month_same_elapsed'}, periods)
            stage = 'data'
            engine = SalesMetrics(self.tables, self.rules, self.as_of)
            stage = 'resolve'
            resolved = resolve_filters(plan['filters'], self.tables, self.as_of)
            stage = 'dispatch'
            kwargs = dict(filters=resolved.filters)
            if plan['operation'] == 'quantity':
                kwargs['unit'] = resolved.unit
            if plan['ranking'] is not None:
                kwargs.update(plan['ranking'])
            if plan['operation'] == 'revenue_growth':
                kwargs['comparison'] = comparison
            answer = getattr(engine, plan['operation'])(period, **kwargs)
        except AmbiguousEntityError as exc:
            return _abstain('ambiguous_entity', stage, str(exc))
        except ResolutionError as exc:
            return _abstain('unresolved_entity', stage, str(exc))
        except MissingInformation as exc:
            return ExecutionResult(Answer('unanswerable', reason=str(exc)), 'unanswerable', stage)
        except PeriodResolutionError as exc:
            return _abstain('period_error', stage, str(exc))
        except DataError as exc:
            return _abstain('data_error', stage, str(exc))
        except UnsupportedRule as exc:
            return _abstain('unsupported_rule', stage, str(exc))
        if not isinstance(answer, Answer) or answer.type not in (plan['expected_type'], 'unanswerable'):
            raise RuntimeError('Business API returned an unexpected answer type')
        status = 'unanswerable' if answer.type == 'unanswerable' else 'answered'
        return ExecutionResult(answer, status, 'dispatch')
