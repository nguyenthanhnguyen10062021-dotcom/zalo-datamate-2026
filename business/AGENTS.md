# Business guidance

Read [API and error contract](../docs/business.md). Use current source, not a patch embedded in a Gemini response.

- Pure deterministic calculation over canonical tables. No loader, gold, question parsing, evaluator, verifier or network imports.
- Public API: `Rulebook`, `Periods`, `DateRange`, `SalesMetrics`, `Filters`, `Answer`, `DataError`, `UnsupportedRule`.
- Caller supplies the correct split's rulebook/calendar and question's as_of_date. Preserve same_elapsed comparisons, partial-period behavior, rounding, filter scope and tie-break semantics.
- Preserve dependency-scoped validation, orphan-line protections and cancel/return filtering order. Never coerce missing/invalid amounts to zero or catch errors as unanswerable.
- Add synthetic regression cases for behavioral fixes; preserve positional API compatibility.
- Targeted tests: `python -m pytest tests/test_business_periods.py tests/test_business_sales.py tests/test_business_verification.py -q`. Then full harness and, when local inputs exist, data profile. The selected gold verifier covers a subset, not all 10 APIs or NLU.
