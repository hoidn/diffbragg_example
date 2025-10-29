# DBEX Test Suite Index

**Purpose**: Authoritative registry of DBEX test selectors, synchronized with `docs/TESTING_GUIDE.md` §2.

## Implementation Coverage (Active)

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `tests/dbex/test_nanobrag_bridge.py` | active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | [panel, slow, fast], mask polarity, background semantics.
| Config hydration | `tests/dbex/test_nanobrag_bridge_configs.py` | active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector CUSTOM mapping, beam wavelength/polarization, crystal A*.
| Smoke harness | `tests/dbex/test_nanobrag_smoke.py` | active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg, masked MSE, artifacts.

Footnote: DB_AT acceptance remains the canonical parity profile; until marks/selectors are migrated, use these module selectors to drive implementation loops.

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Torch parity | `pytest -v tests -k DB_AT_001` | planned | `docs/spec-db-conformance.md:24` | Uses golden data under `nanoBragg2/tests/golden_data`; validates simple cubic correlation ≥0.99. |
| Determinism | `pytest -v tests -k DB_AT_002` | planned | `docs/development/testing_strategy.md:2.7` | Requires fixtures that lock RNG seeds and check bitwise/tolerance equality. Environment: CPU-only, CUDA_VISIBLE_DEVICES=''. |
| Reflection ingestion | `pytest -v tests -k DB_AT_020` | planned | `docs/spec-db-conformance.md:30` | Exercises bbox exclusivity and panel ordering via DIALS samples. Blocks CLI parity work. |
| Mask semantics | `pytest -v tests -k DB_AT_021` | planned | `docs/spec-db-core.md:51` | Confirms trusted mask polarity (True=include) and simulator masking rules. |
| Background semantics | `pytest -v tests -k DB_AT_022` | planned | `docs/spec-db-conformance.md:38` | Validates −1 sentinel handling around ROIs. |
| Calibration | `pytest -v tests -k DB_AT_023` | planned | `docs/spec-db-core.md` | Ensures ADU vs photons policy behaves per spec. Requires adu_per_photon fixtures. |
| Mapping sanity | `pytest -v tests -k DB_AT_024` | planned | `docs/spec-db-conformance.md` | Confirms zero-iteration forward pass overlaps data within tolerance; logs metrics. |
| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | planned | `docs/pytorch_runtime_checklist.md:31` | Equal-weight source handling and vectorized loops. Currently in `nanoBragg2/tests/`; port to DBEX before marking active. |

**Maintenance Rules**:
- Update this index as new tests are authored; mark selectors `active` once they exist in `tests/`.
- Keep selectors sorted by profile to match `docs/spec-db-conformance.md`.
- Record any skipped selectors and rationale in `docs/fix_plan.md`.
- Cross-reference: This index mirrors `docs/TESTING_GUIDE.md` §2 Test Taxonomy. Keep both in sync when adding/removing selectors.
