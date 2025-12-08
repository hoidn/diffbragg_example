# RUNTIME-VEC-001 — Source Weight Runtime Guard

## Phase A — Evidence & Scope Definition (COMPLETE — Loop i=164)
- [x] A1: Confirm `nanobrag_torch` CLI is accessible from the DBEX environment (baseline command, version banner) and capture spec references for source-weight handling (`docs/architecture/pytorch_design.md` §1.1.5, `docs/pytorch_runtime_checklist.md` item #4).
  - **Result:** v0.1.0 accessible; spec refs documented in `reports/2025-12-08T140000Z/a1_spec_refs.md`
- [x] A2: Inventory the existing `nanoBragg/tests/test_cli_scaling.py::TestSourceWeights*` cases, identify which assertions map directly to DBEX needs (equal weighting, divergence parity), and note required fixtures/artifacts to port.
  - **Result:** 9 tests inventoried; 1 already ported to DBEX; documented in `reports/2025-12-08T140000Z/a2_test_inventory.md`
- [x] A3: Define artifact policy for the ported tests (e.g., write metrics JSON into `$RUNTIME_VEC_ARTIFACT_DIR` on failure) and document planned pytest selectors + environment flags.
  - **Result:** Policy defined with `RUNTIME_VEC_ARTIFACT_DIR` env var; documented in `reports/2025-12-08T140000Z/a3_artifact_policy.md`

## Phase B — Implementation & Tests (COMPLETE — Loop i=165)
- [x] B1: Test already exists in `tests/dbex/test_runtime_vectorization.py` (ported in prior loop). Validated 1 test collected via `pytest --collect-only`.
- [x] B2: Test PASSED via mapped selector with env vars `RUNTIME_VEC_ARTIFACT_DIR`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`. Metrics: correlation=1.0 (≥0.999 ✓), sum_ratio=1.0 (|Δ|=0.0 ≤5e-3 ✓). Artifacts: `reports/2025-12-08T160000Z/` (pytest_runtime_vec.log, collect_runtime_vec.log, artifacts/mapping_metrics.json).
- [ ] B3: Deferred — remaining `TestSourceWeights*` coverage (divergence correlation checks, CLI parity metrics). Current test validates exit criterion #1 (smoke selector mapped with validated metrics). Additional coverage documented as optional enhancement.

## Phase C — Validation & Documentation (COMPLETE — Loop i=165)
- [x] C1: Updated `docs/TESTING_GUIDE.md` §2 (Runtime vectorization row) and `docs/development/TEST_SUITE_INDEX.md` with fresh artifacts path, runtime, environment, and findings refs.
- [x] C2: fix_plan Attempts History updated with Loop i=165 entry (correlation/sum_ratio metrics, artifact paths, exit criterion #1 satisfied).
- [x] C3: Artifacts archived: `plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/` (pytest_runtime_vec.log, collect_runtime_vec.log, artifacts/mapping_metrics.json, artifacts/source_weight_test_summary.txt, summary.md).
