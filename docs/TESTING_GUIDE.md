# DBEX Testing Guide

This guide standardizes how agents run and author tests for the DiffBragg → `nanobrag_torch` integration work.

## 1. Environments & Flags

### 1.1 Required Environment Variables

**All PyTorch-based tests require:**

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

- **Rationale**: Prevents conflicts when PyTorch loads both MKL and system BLAS libraries. Without this flag, tests may fail with "OMP: Error #15: Initializing libiomp5.so, but found libiomp5.so already initialized."
- **Spec Reference**: `docs/spec-db-runtime.md:18-21`, `docs/spec-db-conformance.md:28`
- **Scope**: Export before any `pytest` invocation that imports torch or dbex modules

**Gradient/gradcheck tests additionally require:**

```bash
export NANOBRAGG_DISABLE_COMPILE=1
```

- **Rationale**: `torch.compile` creates donated buffers that interfere with `torch.autograd.gradcheck` numerical gradient computation. Symptoms include non-deterministic failures or incorrect gradient values.
- **Spec Reference**: `docs/pytorch_runtime_checklist.md:26`, `docs/development/testing_strategy.md:1.6`
- **Scope**: Only required for tests using `torch.autograd.gradcheck` or marked `@pytest.mark.gradcheck`
- **See Also**: `docs/development/testing_strategy.md` §4.1 for full gradient test execution requirements
- **Finding Reference**: RUNTIME-001 (`docs/findings.md`)

### 1.2 Environment Assumptions (Freeze)

- The environment is pre-provisioned. Do not install or upgrade packages (pip/conda/apt/brew) during test loops.
- Editable installs (`pip install -e .`) should only be performed when explicitly directed by a plan. Assume the project is already importable in agent loops.
- Verify environment before running tests (read-only check):
  ```bash
  python -c "import dbex; import torch; print(f'dbex loaded, torch {torch.__version__}')"
  ```
  If imports fail, treat it as a blocker and record the error in `docs/fix_plan.md` rather than attempting environment changes.

### 1.3 Quick Reference Commands

**Standard test run (smoke/integration):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/
```

**Gradient tests:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k gradcheck
```

**Determinism tests (CPU-only, see §2.7 in testing_strategy.md):**
```bash
CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
  KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_013
```

## 2. Test Taxonomy

| Scope | Selector | Purpose | Status | Notes |
| --- | --- | --- | --- | --- |
| Smoke | `python -m dbex.refine_one --help` | Verifies legacy CLI loads after environment changes. | Active | Run before/after backend refactors. |
| Forward equivalence smoke | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` | Generates DiffBragg and torch forward passes (no refinement) on identical inputs and reports coarse ROI metrics/overlays (`docs/spec-db-conformance.md:20`). | Active | Mirrors `plans/nanobrag_integration_plan.md` Phase 1 thresholds (median ROI correlation ≥0.2, ≥90% ROIs localize peak). Selector xfails with stub simulators to attach diagnostics instead of hard failing. Capture overlays/metrics under `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/`; optional traces/config dumps follow `docs/forward_equivalence.md`. |
| Determinism | `CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_002` | Bitwise reproducibility (same seed) and statistical independence (different seeds) validation. | Planned | See `docs/spec-db-conformance.md` (Determinism Profile) and `docs/development/testing_strategy.md` §2.7. Environment: CPU-only (CUDA_VISIBLE_DEVICES=''), torch.compile disabled. Same-seed: bitwise_equal=True, correlation ≥0.9999999, max_abs_diff ≤1e-10. Diff-seed: bitwise_equal=False, correlation ≤0.7, ≥50% pixels differ. Artifacts: `plans/active/<initiative>/reports/<timestamp>/determinism/` (metrics_same_seed.json, metrics_diff_seed.json, env.json). |
| Reflection ingestion | `pytest -v tests -k DB_AT_020` | DIALS reflection ingestion + bbox semantics (`docs/spec-db-conformance.md:30`). | Planned | Blocks CLI parity work. |
| Mask semantics | `pytest -v tests -k DB_AT_021` | Trusted-mask polarity per `docs/spec-db-core.md:51`. | Planned | Author targeted fixtures when masks land. |
| Background semantics | `pytest -v tests -k DB_AT_022` | Validates −1 sentinel handling around ROIs. | Planned | Per `docs/spec-db-conformance.md:38`. |
| Calibration | `pytest -v tests -k DB_AT_023` | Ensures ADU vs photons policy behaves per spec. | Planned | Requires adu_per_photon fixtures. |
| Mapping sanity | `pytest -v tests -k DB_AT_024` | Zero-iteration forward pass overlaps data within tolerance. | Planned | Logs metrics for validation. |
| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | Equal-weight source handling and vectorized loops (`docs/pytorch_runtime_checklist.md:31`). | Planned | Currently in `nanoBragg2/tests/`; port to DBEX. |

**Note**: Tests marked "Planned" must be authored before declaring their parent fix-plan items complete. Record TODO entries in `docs/fix_plan.md` with the relevant selector. See also `docs/development/TEST_SUITE_INDEX.md` for synchronized selector registry.

### 2.1 Active Implementation Coverage (module selectors)

Until DB_AT acceptance marks/selectors are fully migrated, use these concrete module selectors to drive implementation loops. Keep this list synchronized with `docs/development/TEST_SUITE_INDEX.md`.

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `pytest -v tests/dbex/test_nanobrag_bridge.py` | Active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | Verifies [panel, slow, fast], mask polarity, background semantics.
| Config hydration | `pytest -v tests/dbex/test_nanobrag_bridge_configs.py` | Active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector CUSTOM mapping, beam wavelength/polarization, crystal A*. Finding refs: CONFIG-001 (pitfalls catalog), GEOMETRY-001 (beam center/pixel pitch), DXTBX-001 (A* tuple handling).
| Smoke harness | `pytest -v tests/dbex/test_nanobrag_smoke.py` | Active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg, masked MSE, artifacts. Finding ref: MASKING-001 (coverage interpretation).
| CLI backend flag | `pytest -v tests/dbex/test_refine_one_cli.py` | Active | `docs/spec-db-interfaces.md:11`, `plans/active/TORCH-CLI-003/implementation.md` | Parser validation, backend dispatch (diffbragg/nanobrag), torch path bridge invocation, diagnostics metadata. Requires `KMP_DUPLICATE_LIB_OK=TRUE`. Collection log: `plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log` (6 tests). Finding refs: TESTING-002 (mocking strategy), DIAGNOSTICS-001 (HDF5 metadata), TESTING-003 (selector compliance).
| Forward equivalence (DB_AT_001) | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` | Active | `docs/forward_equivalence.md:1-98`, `docs/spec-db-conformance.md:18-33` | DiffBragg vs torch forward-only comparison with ROI correlation, RMSE, peak localization metrics. xfails with stub simulators (median_corr=nan, localization=0.0%). Collection log: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/collect_db_at_001_forward.log` (1 test collected, 0.99s, per TESTING-003). Artifacts: `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/` (metrics.json, roi_metrics.csv, legacy/torch tensors). Finding refs: CONFORMANCE-001, CONFIG-001, MASKING-001, TESTING-003.
| Parity harness (DB_AT_001) | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001` | Active | `docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:30-53`, `docs/spec-db-tracing.md:10-24` | Parity metrics helper (correlation, RMSE, MSE, max\|Δ\|, sum ratio, localization), first-divergence capture (pixel-level mismatch metadata), artifact writers (JSON/CSV/NPY), golden data loader with checksum validation. 14 tests total: 3 manifest integrity, 8 metrics unit tests, 2 artifact emission, 1 DB_AT_001 parity smoke (xfails with synthetic data). Collection log: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/collect_db_at_001_parity.log` (14 tests, 0.23s). Artifacts: `plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/parity_harness/` (metrics.json, metrics.csv, predicted.npy, target.npy, diff_overlay_stub.txt, first_divergence.json). Finding refs: CONFORMANCE-001 (thresholds/xfail), GEOMETRY-001 (pixel pitch guards), MASKING-001 (coverage), DIAGNOSTICS-001 (first-divergence workflow), TESTING-003 (compliance), PARITY-001 (deterministic scan, numpy serialization).

### 2.2 Artifact Policy

- Store `pytest` logs, forward-equivalence metrics, and trace overlays in a documented location per initiative (e.g., `plans/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/forward_equiv/`).
- Determinism tests write to `determinism/` subdirectories with separate artifacts for same-seed vs diff-seed runs.
- Smoke and module selectors may share the top-level timestamped directory but should still capture logs (`pytest -v ... | tee ...`).

### 2.3 Runtime Guardrails

- Always export the environment variables listed in §1.1/1.3 before running PyTorch tests.
- Use editable installs so CLI entry points import correctly.
- Respect existing findings (e.g., GEOMETRY-001, DIAGNOSTICS-001, TESTING-003) when adding new tests or modifying fixtures.

## 3. Running Tests in CI vs Local

(unchanged ...)
