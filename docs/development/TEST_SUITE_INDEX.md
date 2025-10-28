# DBEX Test Suite Index (Seed)

| Module / Area | Selector | Status | Notes |
| --- | --- | --- | --- |
| Parity harness | `pytest -v tests -k DB_AT_001` | planned | Uses golden data under `nanoBragg2/tests/golden_data`; validates simple cubic correlation ≥0.99 (`docs/spec-db-conformance.md:24`).
| Determinism | `pytest -v tests -k DB_AT_002` | planned | Requires fixtures that lock RNG seeds and check bitwise/tolerance equality.
| Reflection ingestion | `pytest -v tests -k DB_AT_020` | planned | Exercises bbox exclusivity and panel ordering via DIALS samples (`docs/spec-db-conformance.md:30`).
| Mask semantics | `pytest -v tests -k DB_AT_021` | planned | Confirms trusted mask polarity and simulator masking rules (`docs/spec-db-core.md:51`).
| Background semantics | `pytest -v tests -k DB_AT_022` | planned | Validates −1 sentinel handling around ROIs (`docs/spec-db-conformance.md:38`).
| Calibration | `pytest -v tests -k DB_AT_023` | planned | Ensures ADU vs photons policy behaves per spec.
| Mapping sanity | `pytest -v tests -k DB_AT_024` | planned | Confirms zero-iteration forward pass overlaps data within tolerance; logs metrics.
| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | active | Protects source equal-weight handling (`docs/pytorch_runtime_checklist.md:31`).

- Update this index as new tests are authored; mark selectors `active` once they exist in `tests/`.
- Keep selectors sorted by profile to match `docs/spec-db-conformance.md`.
- Record any skipped selectors and rationale in `docs/fix_plan.md`.

