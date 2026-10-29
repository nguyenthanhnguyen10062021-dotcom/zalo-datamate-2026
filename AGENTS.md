# DataMate: working agreement for coding agents

Vietnamese offline data QA for Zalo AI Challenge 2026. Communicate with the user in Vietnamese. Work from the repository root using the existing Python environment.

## Start with the right context

1. Check `git status --short` and read [current progress](docs/PROGRESS.md).
2. Use [the documentation map](docs/README.md) to read only the task's references.
3. Run `python scripts/harness.py map` for orientation; before changing a Python file, run `python scripts/harness.py context business/sales.py` with that file's path. Results include current signatures, import dependents, and related decisions. Read the returned source spans as needed.
4. Read the scoped AGENTS.md before editing [loader](loader/AGENTS.md), [business](business/AGENTS.md), [evaluate](evaluate/AGENTS.md), or [AI collaboration](ai_collaboration/AGENTS.md). Do this explicitly when the client starts at root; do not assume every nested file was auto-loaded.

Current source + the relevant split's rulebook + fresh checks take precedence over historical proposals. `ai_collaboration/GEMINI_HANDOFF.md`, old reviews, diffs, and old plans are historical snapshots. Open them only when the task needs that history. QueryPlan executor/NLU remains unimplemented until source and checks establish otherwise.

## Commands

Use `python` from the active project venv; on Windows without activation use `.\.venv\Scripts\python.exe`. See [setup](README.md) and [harness guide](docs/harness-engineering.md).

Modal development: the user prefers maximum GPU parallelism to minimize waiting; this account allows **10 GPUs total**. Default to up to 10 nonempty shards, account for active jobs, and stop task-owned apps afterward. Use the existing Python 3.12 Modal env.

| Command | Meaning |
|---|---|
| `python scripts/harness.py doctor` | Interpreter, pinned packages, optional local data readiness |
| `python scripts/harness.py map --limit 30` | Bounded current Python import map |
| `python scripts/harness.py context business/sales.py` | API, transitive import dependents, relevant decisions |
| `python scripts/harness.py check --profile fast` | Repository hygiene, AST boundaries, current doc links, instruction budgets, diff whitespace |
| `python scripts/harness.py check` | fast + synthetic tests; same command as CI, no BTC data needed |
| `python scripts/harness.py check --profile data` | full + local-data tests + nonempty selected gold regression; needs train/cache |

Navigation is an import graph, not a complete call graph. It always reads working-tree bytes. Output counts reveal truncation; raise `--limit` (up to 200) or use `rg` for exhaustive searches. Never treat missing edges as proof a change is safe.

## Boundaries that matter

- Runtime direction: files -> loader -> canonical tables -> business -> Answer. Root scripts compose layers. Follow [architecture](docs/architecture.md); keep gold/verifiers out of loader/business and external network clients out of runtime.
- Competition inference must remain offline with eligible open-weight models <=15B. Development tools and web research are separate from submission runtime.
- No logic keyed to a particular business/question ID. Mapping dictionaries derive from train READMEs only. Public test is for checking, never fitting/tuning.
- Keep BTC data, questions/answers, cache, row-level reports, credentials and environments local. Use synthetic fixtures in tests. Do not include them in Gemini packets or CI.
- Preserve `DataError`, `UnsupportedRule`, `unanswerable`, and agent abstain as distinct outcomes. Do not silently turn failures into zero/unanswerable.
- Preserve unrelated user edits. Avoid mass reformatting, new dependencies, new frameworks, duplicate status files, or unrelated refactors.

## Work and finish

State the scope and acceptance checks; proceed with authorized reversible work. For a multi-session task, use [task template](docs/tasks/TEMPLATE.md) or an existing plan, record evidence and the next action. Tiny fixes need no extra task document.

Run targeted tests while editing, then `check` before claiming completion. For changes affecting loading/business correctness, run `data` when local inputs are available; otherwise state precisely what could not run. Never infer whole-train PA from the selected verifier. Preserve the reported denominator and skip reasons.

Review the final diff, update the relevant docs, and update PROGRESS only when project status changes. Report what changed, commands/results, limitations, and next action. Keep generated artifacts in ignored locations; do not auto-commit, push, publish, install global hooks, or message other services without task authorization.

## Code Review Rules

Flag gold leakage, public-test fitting, ID-specific logic, silent error conversion, changed rulebook/time/filter semantics, and unsupported claims about coverage/PA. Check API compatibility and fixture coverage. Let the harness handle mechanical rules.
