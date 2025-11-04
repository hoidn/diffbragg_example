# FORWARD-EQUIV-002 Implementation Summary

**Date**: 2025-11-04T041500Z  
**Initiative**: FORWARD-EQUIV-002 — Promote forward equivalence smoke to canonical parity  
**Status**: ✅ Complete (all exit criteria met)

## Problem Statement

Modernize `test_forward_equivalence_complete.py` to use canonical DiffBragg and nanobrag_torch forward passes from golden data, replacing stub fixtures with parity harness utilities and enforcing DB-AT-001 thresholds without xfail.

**SPEC lines implemented**:
- `docs/spec-db-conformance.md:23-26`: DB-AT-001 forward equivalence smoke thresholds
  - Median ROI correlation ≥ 0.2
  - ≥90% ROIs with localized peaks (central half-box)
- `docs/forward_equivalence.md:46-52`: Acceptance thresholds and artifact layout

**ADR alignment**:
- Parity harness utilities (`tests/fixtures/parity_loader.py`) reused to avoid duplicate metric/artifact logic
- Artifact path updated to FORWARD-EQUIV-002 initiative per `docs/TESTING_GUIDE.md:64`

## Implementation

### Changes Made

1. **Removed stub fixtures** (`tests/dbex/test_forward_equivalence_complete.py`):
   - `stub_diffbragg`: Random Gaussian generator (replaced with canonical `bragg_diffbragg.npy`)
   - `stub_torch`: ROI Gaussian generator (replaced with canonical `bragg_torch.npy`)
   - `compute_roi_metrics`: Custom metric function (replaced with `compute_parity_metrics`)

2. **Added canonical parity loader**:
   - `golden_dir` fixture: Path to `tests/fixtures/golden_data/simple_cubic/`
   - `simple_cubic_golden` fixture: Loads golden data with checksum validation per MANIFEST-001
   - Consumes `bragg_diffbragg.npy`, `bragg_torch.npy`, `target_panel_0.npy`, `loss_mask_panel_0.npy`

3. **Reused parity harness utilities**:
   - `compute_parity_metrics`: Correlation, RMSE, MSE, max|Δ|, sum ratio, localization
   - `find_first_divergence`: First pixel-level mismatch per PARITY-001
   - `write_parity_artifacts`: Metrics JSON, CSV, diff overlay stubs, tensor NPY files

4. **Updated artifact routing**:
   - Changed from `plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/`
   - To `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/`

5. **Removed xfail and enforced thresholds**:
   - Removed `pytest.xfail()` for stub simulator scenario
   - Added hard assertions: `correlation >= 0.2`, `localization >= 0.9`

### Search Evidence

- Found golden data files: `bragg_diffbragg.npy`, `bragg_torch.npy`, `target_panel_0.npy`, `loss_mask_panel_0.npy`
- Reused parity loader pattern from `tests/dbex/test_db_at_001_parity.py:42-82`
- Confirmed `tests/fixtures/parity_loader.py:31-39` utilities match parity harness spec

## Test Results

### Targeted Test

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/dbex/test_forward_equivalence_complete.py::TestForwardEquiv::test_DB_AT_001_forward_equiv
```

**Result**: ✅ 1 passed

### Full Test Suite

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/
```

**Result**: ✅ 47 passed, 1 skipped

### Metrics

Per `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/parity_harness/metrics.json`:

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Correlation | 0.988 | ≥ 0.2 | ✅ Pass |
| Localization | 1.0 | ≥ 0.9 | ✅ Pass |
| RMSE | 180.4 | — | — |
| Max \|Δ\| | 9808.2 | — | — |
| Valid pixels | 13,086 | — | — |
| Manifest checksum | `2d1f8d67...` | MANIFEST-001 | ✅ Validated |

## Artifacts

Directory: `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/`

```
forward_equiv/
├── parity_harness/
│   ├── metrics.json              # Parity metrics (correlation, RMSE, localization)
│   ├── first_divergence.json     # First pixel-level mismatch metadata
│   ├── metrics.csv               # CSV summary
│   ├── diff_overlay_stub.txt     # Diff statistics (future: PNG heatmap)
│   ├── predicted.npy             # nanobrag_torch baseline [slow, fast]
│   └── target.npy                # DiffBragg baseline [slow, fast]
├── legacy/
│   └── bragg_diffbragg.npy       # DiffBragg forward pass
├── torch/
│   └── bragg_torch.npy           # nanobrag_torch forward pass
├── target.npy                    # Background-subtracted targets
├── loss_mask.npy                 # Loss mask [slow, fast] bool
pytest_forward_equiv.log          # Targeted test run log
collect_db_at_001_forward.log     # pytest --collect-only output (1 test)
```

## Documentation Updates

1. **docs/TESTING_GUIDE.md §2** (line 64):
   - Updated artifact path to FORWARD-EQUIV-002
   - Removed "xfails with stub simulators" language
   - Added canonical metrics: correlation=0.988, localization=1.0
   - Listed findings: CONFORMANCE-001, TESTING-003, PARITY-001, MANIFEST-001, SCALE-001/002

2. **docs/development/TEST_SUITE_INDEX.md** (line 20):
   - Updated collection/test logs to FORWARD-EQUIV-002
   - Added canonical metrics and artifact paths
   - Cross-referenced parity harness utilities

3. **docs/fix_plan.md**:
   - Marked FORWARD-EQUIV-002 status: `in_progress` → `done`
   - Added Attempts History entry with metrics, artifacts, and next actions

## Exit Criteria Validation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 1. Consumes canonical DiffBragg/torch tensors via parity loader | ✅ | `simple_cubic_golden` fixture, `bragg_diffbragg.npy`/`bragg_torch.npy` loaded |
| 2. Artifacts target FORWARD-EQUIV-002 with parity harness outputs | ✅ | `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/` |
| 3. Selector docs reference new artifact path and canonical metrics | ✅ | Updated `docs/TESTING_GUIDE.md:64`, `docs/development/TEST_SUITE_INDEX.md:20` |
| 4. Attempts History records pytest + collect-only runs | ✅ | `pytest_forward_equiv.log`, `collect_db_at_001_forward.log` captured |

## Findings Applied

- **CONFORMANCE-001**: DB_AT selector env flag (`KMP_DUPLICATE_LIB_OK=TRUE`) + thresholds (correlation ≥0.2, localization ≥0.90)
- **TESTING-003**: Sync testing docs with collect-only evidence (`1 test collected`)
- **PARITY-001**: Capture first divergence metadata alongside metrics (`first_divergence.json`)
- **MANIFEST-001**: Checksum validation for golden data (`2d1f8d671a6b051b23dd7a059f9fd8ff5605389bbe9a8e72cb44cbd7a8567aee`)
- **SCALE-001/SCALE-002**: Honor canonical structure-factor scaling and √spot_scale when consuming tensors

## Next Steps

**FORWARD-EQUIV-002 is complete.** Recommended next items from `docs/fix_plan.md`:

1. **DB_AT_002 Determinism selector scaffold** — Once forward equivalence passes, author determinism tests (same-seed bitwise, diff-seed statistical independence)
2. **CLI end-to-end smoke with nanobrag backend artifacts** — Integrate forward equivalence into full CLI workflow validation

## Commit

```
FORWARD-EQUIV-002 test_forward_equivalence_complete: modernize to canonical parity (tests: DB_AT_001)

Replaced stub fixtures with parity loader utilities from tests/fixtures/parity_loader.py,
consuming canonical golden data (bragg_diffbragg.npy, bragg_torch.npy) from
tests/fixtures/golden_data/simple_cubic/.

Test results: pytest -v tests/ → 47 passed, 1 skipped
Metrics: correlation=0.988, localization=1.0, RMSE=180.4
Artifacts: plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/

Findings applied: CONFORMANCE-001, TESTING-003, PARITY-001, MANIFEST-001, SCALE-001/002

🤖 Generated with Claude Code
```

**Git hash**: `1e7a294`  
**Pushed**: ✅ `origin/integration`
