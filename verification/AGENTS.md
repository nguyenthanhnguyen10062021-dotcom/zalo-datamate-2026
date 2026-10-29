# Verification tools

Read [contract](../docs/superpowers/specs/2026-10-29-capability-verifier.md).

- Development only; never import this package into loader/business/queryplan.
- Selector consumes question text only. No gold, answer type, cache results or IDs to select/construct plans. Freeze manifest before scoring; no mismatch-driven exclusions or public-test tuning.
- Keep legacy regression separate. Use QueryExecutor and the real local evaluator; preserve status/stage, denominators and all errors. Unexpected failures are reported, never converted to unanswerable.
- Row-level inputs/manifests/reports stay in reports/ ignored; tracked tests contain synthetic data only. Do not overwrite source data, frozen manifests or cache with reports.
- Run harness context before Python edits, targeted tests, full harness and local verification. Results are retrospective grammar+executor diagnostics, not model PA or unseen-fold performance.
