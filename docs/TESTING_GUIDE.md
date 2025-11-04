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
| Forward equivalence smoke | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` | Generates DiffBragg and torch forward passes (no refinement) on identical inputs and reports coarse ROI metrics/overlays (`docs/spec-db-conformance.md:20`). | Active | Mirrors `plans/nanobrag_integration_plan.md` Phase 1 thresholds (median ROI correlation ≥0.2, ≥90% ROIs localize peak). Uses parity harness utilities (`tests/fixtures/parity_loader.py`) to load `bragg_diffbragg.npy` and `bragg_torch.npy` baselines. Enforces thresholds: correlation ≥0.2 (canonical: 0.988), localization ≥0.90 (canonical: 1.0). Artifacts: `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/` (metrics.json, first_divergence.json, parity_harness/). Findings: CONFORMANCE-001, TESTING-003, PARITY-001, MANIFEST-001, SCALE-001/002. |
| Determinism | `CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_002` | Bitwise reproducibility (same seed) and statistical independence (different seeds) validation. | Active | See `docs/spec-db-conformance.md` (Determinism Profile) and `docs/development/testing_strategy.md` §2.7. Environment: CPU-only (CUDA_VISIBLE_DEVICES=''), torch.compile disabled. Same-seed (canonical): bitwise_equal=True, correlation=1.0, max_abs_diff=0.0, n_valid_pixels=13086. Diff-seed (canonical): bitwise_equal=False, correlation≈-0.0035 (excellent independence), differing_pixels=100%. Artifacts: `plans/active/DB-AT-002/reports/2025-11-04T050000Z/determinism/` (metrics_same_seed.json, metrics_diff_seed.json, env.json, commands.txt). Collection log: `plans/active/DB-AT-002/reports/2025-11-04T050000Z/collect_db_at_002.log` (2 tests collected). Test log: `plans/active/DB-AT-002/reports/2025-11-04T050000Z/pytest_db_at_002.log` (2 passed). Finding refs: CONFORMANCE-001, TESTING-003, RUNTIME-001, PARITY-001, MANIFEST-001. |
| Reflection ingestion | `pytest -v tests -k DB_AT_020` | DIALS reflection ingestion + bbox semantics (`docs/spec-db-conformance.md:28-30`). Validates bbox exclusivity (x1 > x0, y1 > y0), slice shape consistency, panel alignment, and detector bounds for all ROIs. | Active | Tests: `tests/dbex/test_reflection_ingestion.py` (2 tests collected, 2 passed). Canonical: 92 ROIs, 1 panel, sample bbox=(582,594,0,12). Artifacts: `plans/active/DB-AT-020/reports/2025-11-04T052000Z/` (pytest_db_at_020.log, collect_db_at_020.log, reflection_metrics.json). Findings: CONFORMANCE-001, TESTING-003, CONFIG-001. |
| Mask semantics | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_021` | Trusted-mask polarity, shape alignment, and loss-mask consistency per `docs/spec-db-core.md:29-55`. Validates DataLoad mask hydration (True=include polarity guard, >50% coverage), loss mask computation `(background >= 0) & trusted_mask`, and target zeroing outside loss mask. | Active | Tests: `tests/dbex/test_mask_semantics.py` (3 tests collected, 3 passed). Canonical: trusted_fraction=91.5%, loss_mask_fraction=0.21%, mean_roi_loss_coverage=98.8%, 92 ROIs. Skip guard active when `747_mask.pkl` absent. Artifacts: `plans/active/DB-AT-021/reports/2025-11-04T060900Z/` (pytest_db_at_021.log, collect_db_at_021.log, mask_metrics.json, mask_shape_polarity_metrics.json). Findings: CONFORMANCE-001, TESTING-003, MASKING-001, CONFIG-001. |
| Background semantics | `pytest -v tests -k DB_AT_022` | Validates −1 sentinel handling around ROIs. | Planned | Per `docs/spec-db-conformance.md:38`. |
| Calibration | `pytest -v tests -k DB_AT_023` | Ensures ADU vs photons policy behaves per spec. | Planned | Requires adu_per_photon fixtures. |
| Mapping sanity | `pytest -v tests -k DB_AT_024` | Zero-iteration forward pass overlaps data within tolerance. | Planned | Logs metrics for validation. |
| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | Equal-weight source handling and vectorized loops (`docs/pytorch_runtime_checklist.md:31`). | Planned | Currently in `nanoBragg2/tests/`; port to DBEX. |

**Note**: Tests marked "Planned" must be authored before declaring their parent fix-plan items complete. Record TODO entries in `docs/fix_plan.md` with the relevant selector. See also `docs/development/TEST_SUITE_INDEX.md` for synchronized selector registry.
**Registry updates are conditional:** Run `pytest --collect-only` and update the registry **only when you add or rename tests** in this loop. Do not block implementation on registry updates.

### 2.1 Active Implementation Coverage (module selectors)

Until DB_AT acceptance marks/selectors are fully migrated, use these concrete module selectors to drive implementation loops. Keep this list synchronized with `docs/development/TEST_SUITE_INDEX.md`.

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `pytest -v tests/dbex/test_nanobrag_bridge.py` | Active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | Verifies [panel, slow, fast], mask polarity, background semantics.
| Config hydration | `pytest -v tests/dbex/test_nanobrag_bridge_configs.py` | Active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector CUSTOM mapping, beam wavelength/polarization, crystal A*. Finding refs: CONFIG-001 (pitfalls catalog), GEOMETRY-001 (beam center/pixel pitch), DXTBX-001 (A* tuple handling).
| Smoke harness | `pytest -v tests/dbex/test_nanobrag_smoke.py` | Active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg, masked MSE, artifacts. Finding ref: MASKING-001 (coverage interpretation).
| CLI backend flag | `pytest -v tests/dbex/test_refine_one_cli.py` | Active | `docs/spec-db-interfaces.md:11`, `plans/active/TORCH-CLI-003/implementation.md` | Parser validation, backend dispatch (diffbragg/nanobrag), torch path bridge invocation, diagnostics metadata. Requires `KMP_DUPLICATE_LIB_OK=TRUE`. Collection log: `plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log` (6 tests). Finding refs: TESTING-002 (mocking strategy), DIAGNOSTICS-001 (HDF5 metadata), TESTING-003 (selector compliance).
| Forward equivalence (DB_AT_001) | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` | Active | `docs/forward_equivalence.md:1-98`, `docs/spec-db-conformance.md:18-33` | DiffBragg vs torch forward-only comparison with ROI correlation, RMSE, peak localization metrics. xfails with stub simulators (median_corr=nan, localization=0.0%). Collection log: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/collect_db_at_001_forward.log` (1 test collected, per TESTING-003). Artifacts: `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/` (metrics.json, roi_metrics.csv, legacy/torch tensors). Finding refs: CONFORMANCE-001, CONFIG-001, MASKING-001, TESTING-003.
| Parity harness (DB_AT_001) | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001` | Active | `docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:30-53`, `docs/spec-db-tracing.md:10-24` | Parity metrics helper (correlation, RMSE, MSE, max\|Δ\|, sum ratio, localization), first-divergence capture (pixel-level mismatch metadata), artifact writers (JSON/CSV/NPY), golden data loader with checksum validation from canonical 2025-11-04 capture. 14 tests total: 3 manifest integrity, 8 metrics unit tests, 2 artifact emission, 1 DB_AT_001 parity smoke (canonical DiffBragg vs nanobrag_torch comparison) with hardened manifest checksum assertion (2d1f8d671a6b051b23dd7a059f9fd8ff5605389bbe9a8e72cb44cbd7a8567aee). Collection log: `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/collect_db_at_001_parity.log` (14 tests collected). Test log: `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/pytest_db_at_001.log` (1 passed). Artifacts: `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/parity_harness/` (metrics.json: correlation=0.988, localization=1.0, RMSE=180.4; predicted.npy, target.npy, first_divergence.json). Finding refs: CONFORMANCE-001 (thresholds/xfail), GEOMETRY-001 (pixel pitch guards), MASKING-001 (coverage), DIAGNOSTICS-001 (first-divergence workflow), TESTING-003 (compliance), PARITY-001 (deterministic scan, numpy serialization), MANIFEST-001 (checksum validation), SCALE-001/002 (structure-factor/global-scale handling).

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
