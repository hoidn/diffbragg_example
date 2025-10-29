# DBEX Test Suite Index

**Purpose**: Authoritative registry of DBEX test selectors, synchronized with `docs/TESTING_GUIDE.md` §2.

## Implementation Coverage (Active)

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `tests/dbex/test_nanobrag_bridge.py` | active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | [panel, slow, fast], mask polarity, background semantics.
| Config hydration | `tests/dbex/test_nanobrag_bridge_configs.py` | active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector CUSTOM mapping, beam wavelength/polarization, crystal A*. Finding refs: CONFIG-001 (pitfalls catalog), GEOMETRY-001 (beam center/pixel pitch), DXTBX-001 (A* tuple handling).
| Smoke harness | `tests/dbex/test_nanobrag_smoke.py` | active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg, masked MSE, artifacts. Finding ref: MASKING-001 (coverage interpretation).
| CLI backend flag | `tests/dbex/test_refine_one_cli.py` | active | `docs/spec-db-interfaces.md:11`, `plans/active/TORCH-CLI-003/implementation.md` | Parser validation, backend dispatch (diffbragg/nanobrag), torch path bridge invocation, diagnostics metadata. Requires `KMP_DUPLICATE_LIB_OK=TRUE`. Collection log: `plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log` (6 tests). Finding refs: TESTING-002 (mocking strategy), DIAGNOSTICS-001 (HDF5 metadata), TESTING-003 (selector compliance).
| Forward equivalence (DB_AT_001) | `tests/dbex/test_forward_equivalence_complete.py` | active | `docs/forward_equivalence.md`, `docs/spec-db-conformance.md:18-33` | Forward-only comparison (DiffBragg vs torch). ROI correlation, RMSE, peak localization metrics. xfails with stub simulators. Artifacts: `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/` (metrics.json, roi_metrics.csv, legacy/torch tensors). Collection log: `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/collect_db_at_001.log` (1 test). Finding refs: CONFORMANCE-001, CONFIG-001, MASKING-001, TESTING-003.
| Parity harness (DB_AT_001) | `tests/dbex/test_db_at_001_parity.py` | active | `docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:30-53`, `docs/spec-db-tracing.md:10-24` | Parity metrics helper (correlation, RMSE, MSE, max\|Δ\|, sum ratio, localization), artifact writers (JSON/CSV/NPY), golden data loader with checksum validation. Includes 14 tests: 3 manifest integrity, 8 metrics unit tests, 2 artifact emission, 1 DB_AT_001 parity smoke (xfails with synthetic data). Requires `KMP_DUPLICATE_LIB_OK=TRUE`. Collection log: `plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/collect_db_at_001.log` (14 tests). Artifacts: `plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/parity_harness/` (metrics.json, metrics.csv, predicted.npy, target.npy, diff_overlay_stub.txt). Finding refs: CONFORMANCE-001 (thresholds/xfail), GEOMETRY-001 (pixel pitch guards), MASKING-001 (coverage interpretation), TESTING-003 (selector compliance).

Footnote: DB_AT acceptance remains the canonical parity profile; until selectors are implemented, use the module harnesses to drive incremental work.

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Forward equivalence smoke (DB_AT_001) | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` | active | `docs/spec-db-conformance.md:20`, `docs/forward_equivalence.md` | Run DiffBragg and torch forward passes (no refinement) on the same inputs and report coarse ROI metrics/overlays. Selector xfails with stub simulators to attach diagnostics. Artifacts: `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/` (metrics.json, roi_metrics.csv, overlays, legacy/torch tensors). Collection log artifact: `collect_db_at_001.log` (1 test).
| Determinism | `CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_002` | planned | `docs/spec-db-conformance.md:20`, `docs/development/testing_strategy.md:2.7` | CPU-only (CUDA_VISIBLE_DEVICES=''), torch.compile disabled. Same-seed: bitwise_equal=True, correlation ≥0.9999999, max_abs_diff ≤1e-10. Diff-seed: bitwise_equal=False, correlation ≤0.7, ≥50% pixels differ. Artifacts: determinism/ subdirectory with metrics_same_seed.json, metrics_diff_seed.json, env.json. |
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
