# QueryPlan guidance

Read [contract and examples](../docs/queryplan.md) and [business API](../docs/business.md).

- Runtime direction: caller -> queryplan -> business -> Answer. Never import loader, evaluator, verifier, tests or network clients here; caller supplies canonical tables and the correct split's Rulebook/calendar/as_of_date.
- Strict JSON contract, no natural-language parsing/model/gold or logic keyed to business/question IDs. Preserve input bytes/tables.
- Resolve names conservatively using catalog evidence. Unknown, ambiguous and missing information are separate outcomes; never turn an unknown label into a zero by sending it unchanged to business.
- Keep status/stage alongside Answer in local logs. DataError/UnsupportedRule/plan/resolve errors cause classified abstain; unexpected implementation exceptions propagate. Missing information and business unanswerable require evidence, not catch-all conversion.
- Keep same_elapsed, partial-period, whole-shop share denominator, unit and filter semantics from business. Do not validate unrelated catalogs when counting orders.
- Run `python scripts/harness.py context <file.py>` before editing, then `python -m pytest tests/test_queryplan_contract.py tests/test_queryplan_executor.py -q`, full harness and data profile when local inputs exist. The legacy gold verifier does not measure executor or NLU accuracy.
