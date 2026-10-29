# Public Submission File Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the public cache, run the fixed NLU v2 model once on Modal, execute all 1,000 questions locally, and produce a validated `submission.jsonl` for a public leaderboard test.

**Architecture:** A public-only job builder fingerprints the public split, corrected cache, prompt/schema and sampling config without reading gold. The existing private Modal generator receives only request IDs and messages, with a new one-call 5 USD budget policy. A separate local runner validates every binding, executes QueryPlans by business, writes a diagnostic sidecar, and emits a sanitized submission with one ordered row per public question.

**Tech Stack:** Python 3.14 core venv, pandas/pyarrow cache, existing `nlu` and `queryplan` packages, Modal SDK 1.6.3 in the ignored Python 3.12 environment, Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28`.

**Spec:** `docs/superpowers/specs/2026-10-29-public-submission-file-design.md`

## Global Constraints

- Output only a public-test `submission.jsonl`; no Docker, portal upload, leaderboard feedback loop, public-test tuning, commit or push.
- Preserve all unrelated dirty-worktree changes. Before editing each Python file, run `python scripts/harness.py context <path>` and read `tools/AGENTS.md` or `nlu/AGENTS.md` as applicable.
- Public artifacts and row-level data stay under ignored `reports/public_submission/v1/`; do not track BTC data, credentials, generations or submission files.
- Use exactly the frozen model revision, prompt/schema v2, temperature `0.0`, seed `20261029`, and max tokens `768`.
- New authorization is a separate hard cap: profile `vuonghungnguyen07`, one Modal call, 4 USD call envelope plus 1 USD margin, total at most 5 USD. Do not mutate/reset the completed baseline ledger.
- Missing, duplicate, truncated, invalid, unsupported, unresolved, data and unexpected per-question failures remain visible in the sidecar and become abstain in the upload file; never repair or drop them.

## Review Focus

- A partial Modal artifact with missing records must still produce exactly 1,000 ordered submission rows, with missing IDs abstained.
- Duplicate or unknown generation IDs must abort before any submission artifact is written.
- Changes to questions, rulebook, calendar, cache, prompt/schema or job payload after freeze must be rejected.
- NaN/Infinity, internal fields, invalid answer shapes and duplicate/out-of-order submission IDs must fail validation.
- A pre-existing, tampered or second-call public budget ledger must hard-stop dispatch and must not affect the old baseline ledger.

---

### Task 1: Add the isolated one-call public budget policy

**Files:**
- Modify: `tools/nlu_budget.py`
- Modify: `tools/modal_nlu.py`
- Modify: `tests/test_nlu_jobs.py`

**Interfaces:**
- Produces: `reserve_public_submission_call(path, stage, profile) -> dict`
- Produces: Modal entrypoint `main(jobs: str, out: str, stage: str, budget_policy: str = 'baseline_v1')`
- Keeps: `reserve_call(path, stage, profile)` and the existing baseline ledger format/behavior unchanged.

- [ ] **Step 1: Run context and read scoped guidance**

Run: `python scripts/harness.py context tools/nlu_budget.py` and `python scripts/harness.py context tools/modal_nlu.py`.

- [ ] **Step 2: Write failing budget tests**

Add tests proving public policy creates a ledger with `limit_usd=5`, `margin_usd=1`, one 4 USD reservation, rejects a second call, rejects the wrong profile/policy fields, removes its lock on failure, and leaves a separate baseline ledger byte-identical.

- [ ] **Step 3: Run the targeted test and confirm RED**

Run: `python -m pytest tests/test_nlu_jobs.py -q`.

Expected: FAIL because `reserve_public_submission_call` does not exist.

- [ ] **Step 4: Implement the minimal isolated policy**

Share only atomic lock/write and resource-cost calculation internally. Keep public and baseline constants/validation distinct. In `modal_nlu.py`, map `baseline_v1` to `reports/nlu_baseline/v1/budget.json` and `public_submission_v1` to `reports/public_submission/v1/budget.json`; reject every other value before dispatch.

- [ ] **Step 5: Run tests and review checkpoint**

Run: `python -m pytest tests/test_nlu_jobs.py -q` and `git diff --check`.

Expected: PASS; no commit per repository instruction.

### Task 2: Freeze public jobs without gold or routing leakage

**Files:**
- Create: `tools/public_jobs.py`
- Create: `tests/test_public_submission.py`
- Modify: `docs/context-index.json`

**Interfaces:**
- Produces: `prepare_public_jobs(split_root: Path, cache_root: Path, out: Path) -> dict`
- Produces: `load_public_jobs(path: Path) -> tuple[dict, list[dict]]`
- Produces: `load_cache(cache_dir: Path) -> tuple[dict, dict]`
- CLI: `python tools/public_jobs.py --split public_test --cache <cache> --out <jobs.json>`

- [ ] **Step 1: Run context before creating the adjacent tool**

Run: `python scripts/harness.py context tools/nlu_jobs.py`; re-read `tools/AGENTS.md` and `nlu/AGENTS.md`.

- [ ] **Step 2: Write failing synthetic prepare/integrity tests**

Use a temporary split with three questions and two cache businesses. Assert exact input order, unique deterministic request IDs, `prompt_version='nlu-baseline-2'`, fixed sampling/schema, source/cache/code hashes, no question/business ID in model messages, and no access to `answers.jsonl`. Add negative tests for duplicate question IDs, missing cache files, invalid business component, and source/cache/code drift after freeze.

- [ ] **Step 3: Run the targeted tests and confirm RED**

Run: `python -m pytest tests/test_public_submission.py -q`.

Expected: import failure for `tools.public_jobs`.

- [ ] **Step 4: Implement public job preparation**

Reuse the existing strict question/hash conventions and bounded table context, but do not create train roles, sample/limit, references or gold paths. Require all split questions and all five canonical parquet files plus `cua_hang.json` for each referenced business. Use exclusive writes under `reports/`.

- [ ] **Step 5: Add context routing and run GREEN**

Add a `public-submission-file` entry touching the new tools/runner/tests and pointing to the approved spec, plan, `docs/nlu.md` and `tools/AGENTS.md`.

Run: `python -m pytest tests/test_public_submission.py tests/test_nlu_jobs.py -q`.

Expected: PASS.

### Task 3: Build the gold-free local submission runner and validator

**Files:**
- Create: `run_public_submission.py`
- Modify: `tests/test_public_submission.py`

**Interfaces:**
- Consumes: `load_public_jobs(path)` and `load_cache(cache_dir)` from Task 2.
- Produces: `generation_index(records, expected_ids) -> tuple[dict, list[dict]]`
- Produces: `validate_submission(rows: list[dict], questions: list[dict]) -> None`
- Produces: `run(jobs_path: Path, generations_path: Path, out_dir: Path) -> dict`
- CLI: `python run_public_submission.py --jobs <jobs.json> --generations <raw.jsonl> --out <revision-dir>`

- [ ] **Step 1: Run context for the analogous diagnostic runner**

Run: `python scripts/harness.py context run_nlu.py` and read its source spans. Do not import `_reference`, `_scorer`, `evaluate` or `answers.jsonl` in the new runner.

- [ ] **Step 2: Write failing end-to-end synthetic tests**

Build synthetic cache/rulebook/calendar and frozen jobs for at least five questions: valid answer, missing generation, `finish_reason=length`, backend error, and unexpected executor exception. Assert the runner first exclusive-writes `predictions.json`, then writes exactly five ordered submission rows; only the valid answer is retained and every failure is `{"id": ..., "type": "abstain"}` with detailed status/reason solely in the sidecar.

- [ ] **Step 3: Add validator edge tests from Review Focus**

Reject unknown/duplicate generation IDs, missing run metadata binding, wrong jobs hash, duplicate/out-of-order submission IDs, non-finite numbers, wrong type/value shape, internal keys, alias and malformed table/list payloads. Accept the nine official output types and optional reason only for unanswerable.

- [ ] **Step 4: Run tests and confirm RED**

Run: `python -m pytest tests/test_public_submission.py -q`.

Expected: FAIL because `run_public_submission` does not exist.

- [ ] **Step 5: Implement the runner with per-question containment**

Process one business cache at a time. Use strict `generation_attempt`, `QueryExecutor`, the public split rulebook/calendar and input order. Catch unexpected exceptions only in the outer per-question diagnostic boundary, record `execution_error`, and emit sanitized abstain. Write artifacts with `x`/exclusive semantics; validate all rows in memory before creating `submission.jsonl`.

- [ ] **Step 6: Run GREEN and review artifact ordering**

Run: `python -m pytest tests/test_public_submission.py tests/test_nlu_core.py tests/test_nlu_jobs.py tests/test_nlu_scoring.py -q`.

Expected: PASS.

### Task 4: Add repository guards for the public submission path

**Files:**
- Modify: `scripts/harness.py`
- Modify: `tests/test_harness.py`
- Modify: `docs/README.md`

**Interfaces:**
- Keeps: `check_source(path: str, source: str) -> list[str]`
- Adds: submission-runtime checks for `run_public_submission.py` and `tools/public_jobs.py` without changing lower-layer rules.

- [ ] **Step 1: Run context before harness edits**

Run: `python scripts/harness.py context scripts/harness.py`.

- [ ] **Step 2: Write failing guard tests**

Assert submission runtime rejects imports of evaluator/network clients, literal `answers.jsonl`, and output paths outside ignored reports; assert allowed imports of nlu/queryplan/business/tools and public split literals remain valid.

- [ ] **Step 3: Run RED**

Run: `python -m pytest tests/test_harness.py -q`.

Expected: new submission-runtime violation cases are not detected.

- [ ] **Step 4: Implement narrow guards and documentation routing**

Add explicit path-based checks rather than treating all root/tools scripts as runtime layers. Update the docs map with prepare/run/validate commands and the no-Docker/no-upload scope.

- [ ] **Step 5: Run GREEN and full pre-cloud verification**

Run: `python -m pytest tests/test_harness.py tests/test_public_submission.py -q`, then `python scripts/harness.py check`.

Expected: all tests PASS; no public data/report enters Git inventory.

### Task 5: Rebuild and freeze the real public input revision

**Files:**
- Create ignored artifacts only: `reports/public_submission/v1/cache/`, `load_report.md`, `jobs.json`
- Modify tracked task record: `docs/tasks/2026-10-29-public-submission-file.md`

**Interfaces:**
- Consumes: Task 2 CLI and current loader via `load_all.py`.
- Produces: frozen `jobs.json` with exactly 1,000 jobs and 14 cache businesses.

- [ ] **Step 1: Create the task record before long-running work**

Record approved scope, dirty baseline, acceptance, 5 USD authorization and commands. Do not include row-level BTC data.

- [ ] **Step 2: Rebuild corrected public cache to a new ignored revision**

Run `python load_all.py --only dev_001,...,dev_014 --workers 6 --cache reports/public_submission/v1/cache --report reports/public_submission/v1/load_report.md` using the exact 14 directory names discovered from `public_test/data`.

Expected: 14 businesses, 0 crashes; root `cache/` and train revision unchanged.

- [ ] **Step 3: Freeze the 1,000 public jobs**

Run: `python tools/public_jobs.py --split public_test --cache reports/public_submission/v1/cache --out reports/public_submission/v1/jobs.json`.

Expected: selected1000, businesses14, unique IDs1000, prompt v2, fixed sampling and immutable source/cache/code fingerprints.

- [ ] **Step 4: Run data/profile and integrity gates before spending**

Run: `python scripts/harness.py check --profile data` plus a read-only jobs/cache/source integrity load.

Expected: PASS. Stop before Modal on any crash, drift, missing business, test failure or pre-existing public budget call.

### Task 6: Run the single Modal batch and produce the upload file

**Files:**
- Create ignored artifacts only: `generations.jsonl`, receipt, `predictions.json`, `summary.json`, `submission.jsonl`
- Modify: `docs/validation.md`
- Modify: `docs/PROGRESS.md`
- Modify: `docs/tasks/2026-10-29-public-submission-file.md`

**Interfaces:**
- Consumes: frozen jobs from Task 5 and public budget policy from Task 1.
- Produces final: `reports/public_submission/v1/submission.jsonl`.

- [ ] **Step 1: Read-only Modal preflight**

Confirm profile `vuonghungnguyen07`, public ledger absent/empty, old baseline ledger unchanged, and all prior apps stopped/tasks0. Do not print tokens.

- [ ] **Step 2: Dispatch exactly one private batch**

Run with the Python3.12 Modal environment:

`python -m modal run --profile vuonghungnguyen07 tools/modal_nlu.py --jobs reports/public_submission/v1/jobs.json --out reports/public_submission/v1/generations.jsonl --stage public-submission-v1 --budget-policy public_submission_v1`

Expected: at most one reservation/call; bounded one-container lifecycle. Monitor progress and preserve partial output on failure.

- [ ] **Step 3: Confirm cloud cleanup before local execution**

Verify the app is completed/stopped with tasks0. Confirm the public ledger total reservation is at most5USD and the baseline ledger hash is unchanged.

- [ ] **Step 4: Execute and validate all 1,000 rows locally**

Run: `python run_public_submission.py --jobs reports/public_submission/v1/jobs.json --generations reports/public_submission/v1/generations.jsonl --out reports/public_submission/v1`.

Expected: `reports/public_submission/v1/submission.jsonl` contains exactly1,000 parseable UTF-8 JSON lines, IDs unique and in question order, no aliases/internal fields/non-finite values; summary totals sum to1,000. No PA claim because gold is hidden.

- [ ] **Step 5: Final verification and documentation**

Run targeted tests, `python scripts/harness.py check`, `git diff --check`, and read-only status/integrity checks. Update validation/progress/task record with generation count, status/type distributions, timings, app cleanup, hashes, reservation versus observed-cost limitation, and no-public-tuning/no-upload caveats.

- [ ] **Step 6: Deliver only the validated file and concise limitations**

Link `reports/public_submission/v1/submission.jsonl`. State that it has not been uploaded, contains no public score, is not Docker-ready, and that tracked/unrelated working-tree changes were preserved. Do not commit or push.
