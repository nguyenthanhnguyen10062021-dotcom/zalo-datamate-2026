# Loader guidance

Read [architecture](../docs/architecture.md) and the relevant section of [schema/design](../surveys/DESIGN.md).

- Public entrypoint: `loader.load_business`; build mappings from train README descriptions, not gold or public-test fitting.
- This layer may import its own modules and data libraries. It must not import business, evaluator, root runners, verification tools or network clients.
- Treat input files as read-only. Preserve provenance, ambiguity and missingness. Do not invent relationships/amounts to satisfy a known answer or specialize by business ID.
- Maintain raw -> typed -> mapped -> canonical table contracts and downstream API compatibility.
- Targeted tests: `python -m pytest tests/test_parsers.py tests/test_abbrev_infer.py -q`. Then run the root harness full; use data profile for mapping changes when local data/cache exist. Changed loading logic may require rebuilding cache first; disclose that the selected verifier does not validate every mapping.
