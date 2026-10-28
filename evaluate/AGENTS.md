# Evaluator guidance

- `evaluate.py` is the local scoring implementation; stdlib only. Do not add pandas, model, loader or business dependencies.
- Gold may be read here and in dedicated verification tooling; never introduce a dependency from submission/runtime calculation back to scoring.
- Preserve answer type/format checking, abstain score, aliases, ordering and denominator semantics unless a task explicitly changes them with evidence from competition rules.
- Run `python -m pytest evaluate/ -q` then the full harness. Mark only tests that need actual competition downloads as `local_data`.
- The real-file self-score helper has a known historical skip due to its lookup path. Do not claim full official evaluator equivalence from synthetic tests or silently remove the skip.
