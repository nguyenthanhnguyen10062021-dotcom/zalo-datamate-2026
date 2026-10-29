# NLU guidance

Read [contract](../docs/nlu.md) and [QueryPlan](../docs/queryplan.md).

- Pure model-independent parsing/prompting/orchestration: stdlib and queryplan only. No loader, business direct imports, evaluator, verification, Modal SDK, network or gold.
- Model emits QueryPlan, never a calculated answer or executable code. Public validate_plan/check_capability/QueryExecutor own semantics; do not duplicate business/time rules.
- Parse exactly one object or one whole-output JSON fence. Reject multiple blocks, trailing prose, duplicate keys, NaN/Infinity and truncated output. No enum/default/number/last-block repair.
- Keep generation/parse/validation/capability/resolve/data/dispatch outcomes distinct. Unexpected implementation exceptions propagate to the outer diagnostic runner; never silently turn them into unanswerable or zero.
- Raw generation/provenance and failures belong in ignored reports; no IDs/gold/answer type from gold in prompts. Label context comes from eligible input to as_of_date, not answers or scoring.
- Real inference backends and credentials stay outside this package. Tests use synthetic backend/fixtures; a fake backend is not evidence that NLU works.
- Before Python edits run harness context. Run targeted NLU tests then full harness. Real backend smoke and resource/cost checks are separate from synthetic tests.
