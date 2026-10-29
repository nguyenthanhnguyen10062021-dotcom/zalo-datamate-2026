# NLU baseline contract

Baseline M1–M3 is complete under [the accepted Modal plan](tasks/2026-10-29-nlu-modal-baseline-plan.md). Core `nlu/` is model-independent and has no network/Modal dependency. Root/dev tooling supplies generation artifacts and canonical context; QueryExecutor owns business execution.

Generation produces exactly one complete QueryPlan1.0 object, optionally enclosed by one whole-output JSON fence. Missing keys, unknown enums, ambiguous multiple objects, duplicate keys, non-finite numbers, trailing text and truncated generations are rejected, never repaired. Python `validate_plan` remains authoritative; JSON schema constrains structure only, not real dates, capability or business truth.

## Semantic safety — 2026-10-29

Both production runners now pass the original corpus question into `execute_attempt(..., question=...)`. The offline `nlu/semantic.py` gate checks intent, literal time slots, answer shape, mentioned filters, shifts, top-k/metric and unaccounted wording before dispatch. Rejected plans remain in the sidecar with `semantic_rejected` and a stable reason; they are never repaired. Legacy direct calls without `question` preserve their API behavior but do not perform this question/plan check. This is a conservative supported-language gate, not a calibrated confidence probability or a complete semantic verifier.

Unknown wording may reject a correct answer. Zero and executor-supported unanswerable are preserved when the question/plan passes; neither emptiness nor resolver failure is automatically evidence of unanswerability. Calendar arithmetic and implicit years remain owned by QueryPlan/business.

Immutable old inference can be compared using `tools/replay_semantic.py`: original prediction/job/generation/corpus/cache hashes and raw parsed plans are checked, gate hashes are recorded separately, new predictions freeze before train scoring. This is explicitly a replay of existing answers, not regenerated inference or reexecuted business logic. Public mode never opens gold/scoring. Do not weaken normal job source checks to reuse old jobs after source changes.

On the existing evaluation632 frozen predictions, safety gate v1 changes303correct/182wrong/147abstain to203/0/429: PA19.15%→32.12%, precision100% at32.12%coverage. It rejects100previously correct answers as well as182wrong answers. This is retrospective diagnostic evidence with prior train/question/source exposure, not a blind holdout or a public accuracy guarantee. Public replay v2 keeps97/1000answers; the maximum possible score of that conservative file is0.097.

Prompt `nlu-safety-3` adds explicit whole-question support criteria and synthetic intent/time/ranking contrasts. Its results are a separate experiment using the unchanged7B model/schema/sampling/gate; see [task and execution evidence](tasks/2026-10-29-semantic-safety.md). The user's new authorization allows Modal reruns; the separate `semantic_safety_v1` ledger bounds this experiment to3calls/13USDreservation, preserving historical ledgers. Reservation is not an observed invoice.

Fresh prompt3 evaluation produced233correct/0wrong/399abstain on the same632partition, PA36.87%, after a90-question development pilot with36correct/0wrong/54abstain. There were632generations,0backend errors and1truncated output, retained as abstain. These are retrospective measurements, not public predictions of accuracy. The user's subsequent maximum-GPU instruction changes the public generation resource policy to10fixed shards via `tools/modal_semantic_parallel.py`; it has a separate one-call17USDreservation ledger and does not reuse/reset previous allowances. Model/prompt/schema/sampling and the frozen gate are identical across shards.

Publicv3 is ready at `reports/public_submission/v3/submission.jsonl`:1000rows,128answers/872abstain, validated, maximum possible score0.128. Two primary workers timed out while loading weights; one bounded8GPUrecovery pool ran only missing request IDs, using a frozen transport prefix and a separate receipt/ledger. Total concurrent GPUs remained<=10; merge uses fixed primary precedence, never answer content. All apps stopped/tasks0. Full688passed/2deselected; selected data regression409/409. Public accuracy remains unknown; expanding train-grounded capability/coverage is still necessary.

Use the corrected cache explicitly. Status/stage and raw generation metadata stay beside submission output. Generation failure/parse failure/invalid plan/unsupported capability cause classified agent abstention; executor unanswerable is retained as an answer requiring evidence. Unexpected implementation errors are explicit in outer reports, not silently recast as unavailable data.

Train split/protocol is frozen before prompt/model tuning; existing audits are retrospective diagnostics. Model sees neither gold nor routing IDs. SDK/image dependencies, paid GPU workers and account credentials are dev-only, outside runtime core. Submission remains a separate offline integration gate; Modal generation does not certify it.

## Baseline result — 2026-10-29

The private Modal batch completed on profile `vuonghungnguyen07` with Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28`, vLLM 0.21.0, Python 3.12.1 and one NVIDIA A10. The v2 constrained schema binds operation/expected type/ranking/filter scope and nullability implied by each period kind. It remains a generation aid: Python validation, capability checks, resolution and execution are authoritative.

The fixed evaluation partition produced 632/632 records with no backend errors: 632 JSON-valid, 627 plan-contract-valid, 303 correct, 182 wrong and 147 abstain. Penalized accuracy `(correct-wrong)/632` is 19.15%, coverage 76.74%, and precision on answered questions 62.47%. Five invalid plans were revenue-share plans without a filter. The frozen 12-question semantic subset has 6 literal plan matches; equivalence was not adjudicated. This retrospective split has prior train/source exposure and is not blind or fold-clean.

Modal app `ap-JlVK91P8vjr6OD7v5Cbe4D` completed and was verified stopped with zero tasks. The local ledger reserves 24 USD including setup and a 5 USD margin inside the authorized 25 USD cap; that reservation is not an observed invoice. The four-call trial allowance is exhausted. This is a private development batch, not a public endpoint or an offline submission deployment.

## Development commands

Use the existing core venv for prepare/execute/score and a separate ignored Modal environment for generation. New paths/revisions are required: artifacts are exclusive writes, never overwritten.

```powershell
.\.venv\Scripts\python.exe tools/nlu_jobs.py freeze --cache reports/loader_fixes_20261029/cache --out reports/nlu_baseline/<revision>/protocol.json
.\.venv\Scripts\python.exe tools/nlu_jobs.py jobs --protocol reports/nlu_baseline/<revision>/protocol.json --role development --limit 90 --out reports/nlu_baseline/<revision>/development_jobs.json
.\reports\dev_envs\modal312\Scripts\python.exe -m modal run --profile vuonghungnguyen07 tools/modal_nlu.py --jobs reports/nlu_baseline/<revision>/development_jobs.json --out reports/nlu_baseline/<revision>/development_generations.jsonl --stage development-pilot
.\.venv\Scripts\python.exe run_nlu.py --jobs reports/nlu_baseline/<revision>/development_jobs.json --generations reports/nlu_baseline/<revision>/development_generations.jsonl --out reports/nlu_baseline/<revision>/development_result
```

The first trial ledger lives in `reports/nlu_baseline/v1/budget.json`, independent of output revision. It reserves failed/partial calls too; switching output paths cannot reset the budget. Never reset the ledger to bypass its cap. All four calls are now reserved: setup3USD,4calls×4USD,reserve5USD,total24USD inside the25USD authorization. A CPU-only disk probe and image provisioning count under setup; actual billing is distinct from reservations/estimates. Worker resources are fixed to one eligible A10/L4,4physical cores,32GiBmemory,3600sexecution+900sstartup,5sscaledown; bounded watchdog and non-detached cleanup.

`run_nlu.py` binds generations to jobs hashes and request IDs, validates source/corpus/cache/partition integrity, freezes all predictions before opening gold, and reports missing outputs as explicit abstains with sidecar. Parse/contract/capability validity is reported separately from answer score. Reference-plan literal match is a diagnostic, not automatically semantic equivalence.
