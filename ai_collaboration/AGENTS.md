# AI review and handoff guidance

Read [workflow](README.md); current project state is [PROGRESS](../docs/PROGRESS.md).

- Old prompts, responses, handoffs and diffs are immutable historical evidence. Do not bulk-load them for an unrelated task or mistake a proposed patch for current code.
- User-provided responses are review input. Verify suggestions against current source and tests; distinguish proposal, technical conclusion and applied implementation.
- Keep [DECISIONS](DECISIONS.md) as the decision ledger. The [context index](../docs/context-index.json) only routes files to this evidence; it does not replace the ledger.
- New packets need source revision/dirty state, UTF-8 source fingerprints, explicit question and reproducible validation. Include synthetic fixtures and aggregate results; keep BTC rows/questions/answers and secrets out.
- Active round: [003](rounds/003_three_ai_restart/README.md), with Codex, Gemini Web and Antigravity as separate participants. Antigravity is not the historical Argon attribution. Use the shared BRIEF and participant prompts; number each participant's replies separately.
- Prepare files locally. External transfer remains manual unless the user explicitly authorizes a connected send operation. Never invent a reply, consensus or delivery. A review invitation does not authorize runtime edits; follow the round scope.
- Request web replies as downloadable Markdown UTF-8 files, with fenced fallback per the workflow. Keep received responses intact and record actual source access, revision and commands for every reviewer.
