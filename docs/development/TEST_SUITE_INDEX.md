# DBEX Test Suite Index

**Purpose**: Authoritative registry of DBEX test selectors, synchronized with `docs/TESTING_GUIDE.md` §2.

## Implementation Coverage (Active)

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `tests/dbex/test_nanobrag_bridge.py` | active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | [panel, slow, fast], mask polarity, background semantics.
| Config hydration | `tests/dbex/test_nanobrag_bridge_configs.py` | active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector CUSTOM mapping, beam wavelength/polarization, crystal A*. Finding refs: CONFIG-001 (pitfalls catalog), GEOMETRY-001 (beam center/pixel pitch), DXTBX-001 (A* tuple handling).
| Smoke harness | `tests/dbex/test_nanobrag_smoke.py` | active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg, masked MSE, artifacts. Finding ref: MASKING-001 (coverage interpretation).
| CLI backend flag | `tests/dbex/test_refine_one_cli.py` | active | `docs/spec-db-interfaces.md:11`, `plans/active/TORCH-CLI-003/implementation.md` | Parser validation, backend dispatch (diffbragg/nanobrag), torch path bridge invocation, diagnostics metadata. Requires `KMP_DUPLICATE_LIB_OK=TRUE`. Collection log: `plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log` (6 tests). Finding refs: TESTING-002 (mocking strategy), DIAGNOSTICS-001 (HDF5 metadata), TESTING-003 (selector compliance).

Footnote: DB_AT acceptance remains the canonical parity profile; until marks/selectors are migrated, use these module selectors to drive implementation loops.

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Torch parity | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001` | planned | `docs/parity_harness_spec.md:17`, `docs/spec-db-conformance.md:24` | Harness: §2 of parity_harness_spec. No canonical dataset is available; selector MUST xfail/skip with reason `parity dataset unavailable` and log attempted manifest lookup. Once data lands, enforce correlation ≥0.99, MSE, RMSE, max\|Δ\|, sum_ratio. Artifacts: parity/ subdirectory with metrics.json, traces, diff heatmaps. Trace workflow: `docs/spec-db-tracing.md:10-26`. |
| Determinism | `CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_002` | planned | `docs/parity_harness_spec.md:252`, `docs/development/testing_strategy.md:2.7` | Harness: §3 of parity_harness_spec. CPU-only (CUDA_VISIBLE_DEVICES=''), torch.compile disabled. Same-seed: bitwise_equal=True, correlation ≥0.9999999, max_abs_diff ≤1e-10. Diff-seed: bitwise_equal=False, correlation ≤0.7, ≥50% pixels differ. Artifacts: determinism/ subdirectory with metrics_same_seed.json, metrics_diff_seed.json, env.json. |
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
