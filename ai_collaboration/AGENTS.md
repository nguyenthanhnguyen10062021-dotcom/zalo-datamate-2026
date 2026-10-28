# AI review and handoff guidance

Read [workflow](README.md); current project state is [PROGRESS](../docs/PROGRESS.md).

- Old prompts, responses, handoffs and diffs are immutable historical evidence. Do not bulk-load them for an unrelated task or mistake a proposed patch for current code.
- User-provided responses are review input. Verify suggestions against current source and tests; distinguish proposal, technical conclusion and applied implementation.
- Keep [DECISIONS](DECISIONS.md) as the decision ledger. The [context index](../docs/context-index.json) only routes files to this evidence; it does not replace the ledger.
- New packets need source revision/dirty state, UTF-8 source fingerprints, explicit question and reproducible validation. Include synthetic fixtures and aggregate results; keep BTC rows/questions/answers and secrets out.
- Prepare files locally. Gemini web transfer remains manual unless the user explicitly authorizes a connected send operation. Do not invent a response or claim delivery.
- Request the next Gemini response as a downloadable Markdown UTF-8 file, with fenced fallback per the workflow. Keep earlier responses intact.
