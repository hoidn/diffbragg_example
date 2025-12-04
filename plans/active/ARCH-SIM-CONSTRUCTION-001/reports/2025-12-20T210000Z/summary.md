# ARCH-SIM-CONSTRUCTION-001 Phase C.17: HKL Amplitude Ledger Implementation

**Date**: 2025-12-20T210000Z
**Initiative**: ARCH-SIM-CONSTRUCTION-001 (Simulator Construction Convention Alignment)
**Engineer**: Ralph
**Status**: COMPLETE (implementation + validation runs)

## Problem Restatement

DB-AT-028/029 show chi²/pixel = 9.8e5 (baseline) to 2.1e5 (perturbed), indicating a deterministic parity crisis. The supervisor requested adding an HKL-amplitude ledger to the Stage A baseline probe to determine whether the mismatch originates:
- **Before** nanobrag_torch squares |F| (HKL ingestion problem), or
- **Inside** the simulator before Stage A baseline logic executes

The key boundary to bisect: `|F|^2 / n_masked_pixels` vs `reflection intensity sum / n_masked_pixels` vs `Stage A mean per ROI`.

## Source Inspection

Traced HKL data flow from `mapping_context` to reflection matching logic:

- **dbex/vis/mapping.py:165-252**: `hkl_indices` and `hkl_amplitudes` loaded from DataLoad.F.indices()/data() or refined MTZ via `load_refined_mtz()`
- **compare_stage_a_baseline.py:236-241**: HKL grid built from mapping_context indices/amplitudes
- **compare_stage_a_baseline.py:642-747**: Reflection table loaded from refGeom_small.refl, with `miller_index` column extracted per reflection

## Changes Implemented

Modified `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`:

1. **Built HKL lookup dict** (lines 611-622):
   - Convert `mapping_context.hkl_indices` (shape `(n_refl, 3)`) to tuples for deterministic dict keys
   - Map Miller index tuples → amplitudes from `mapping_context.hkl_amplitudes`
   - Result: 69,614 HKL entries from refined MTZ

2. **Extended reflection matching** (lines 650-658, 707-746):
   - Extract `miller_index` from reflection table per ROI
   - Look up HKL amplitude from dict; **fail fast** if missing (ValueError with context)
   - Compute `amp_sq_per_pixel = |F|^2 / n_masked_pixels`
   - Compute ratios: `amp_sq_vs_ref_ratio`, `stagea_vs_amp_sq_ratio`
   - Store HKL index, amplitude, and derived fields in `reflection_roi_matches`

3. **Added percentile stats** (lines 765-807):
   - `amp_sq_vs_ref`: |F|^2/pix vs reference intensity ratio
   - `stagea_vs_amp_sq`: Stage A vs |F|^2/pix ratio
   - Median, P25/P75, min/max across all matched ROIs

4. **Threaded into probe_metadata** (lines 842-847):
   - `hkl_ledger.n_hkl_entries`: 69614
   - `hkl_ledger.failfast_enabled`: True (per input.md requirement)
   - Updated timestamp to 2025-12-20T210000Z, phase to C.17

5. **Updated console output** (lines 1093-1109, 1115-1132):
   - Print HKL ledger stats section with median |F|^2/pix vs Refl and StgA vs |F|^2 ratios
   - Show HKL source MTZ path and columns
   - Updated bottom/top-N tables to include HKL index, |F|^2/pix, StgA/|F|^2, StgA/Refl columns

## Tests Run

### 1. Baseline Probe (`--geometry-mode baseline`)

**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \
  --geometry-mode baseline \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/stage_a_baseline_probe_baseline.json
```

**Outcome**: PASS (DB-AT-027 parity), FAIL (DB-AT-028 chi²/pixel = 9.8e5)

**Key Metrics**:
- HKL lookup entries: 69,614
- Reflections matched: 27/29 (2 ROI mismatches)
- `|F|^2/pix / Refl (intensity)` median: **1.1447** (range 0.29 - 6872)
- `Stage A / |F|^2/pix` median: **0.0934** (range 0.0001 - 10.4)
- Chi²/pixel: 9.8e5 (exceeds 1e2 threshold)

**Decision-Carrying Evidence**:
- Median `amp_sq_vs_ref` ≈ 1.14 → HKL amplitudes-squared per pixel are **comparable** to reflection intensities per pixel, suggesting HKL ingestion is plausible
- Median `stagea_vs_amp_sq` ≈ 0.093 → Stage A produces ~9% of expected intensity from |F|^2, pointing to **simulator underproduction**
- Extreme outliers:
  - ROI 0:[431,443,434,446] HKL=(0,2,-2): StgA/|F|^2 = 10.4 (overestimating)
  - ROI 0:[350,362,877,889] HKL=(4,-5,-1): StgA/|F|^2 = 0.0005 (0.05% of expected)

### 2. Perturbed Probe (`--geometry-mode perturbed`)

**Command**: Same as baseline but with `--geometry-mode perturbed`

**Outcome**: FAIL (DB-AT-027 non-normative, DB-AT-028 chi²/pixel = 1.9e6)

**Key Metrics**:
- `|F|^2/pix / Refl (intensity)` median: **1.1447** (unchanged, geometry-independent)
- `Stage A / |F|^2/pix` median: **0.0043** (dropped from 0.093 in baseline)
- Chi²/pixel: 1.9e6 (worse than baseline, as expected for perturbed geometry)

**Interpretation**:
- Perturbed geometry exacerbates the underproduction: Stage A produces ~0.4% of |F|^2/pix expectation
- ROI 0:[431,443,434,446] HKL=(0,2,-2) explodes to StgA/|F|^2 = 54.6

### 3. DB-AT-028/029 Smoke Tests

**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/db_at_028 \
DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/db_at_029 \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
```

**Outcome**: FAIL (both tests)
- DB-AT-028: chi²/pixel = 2.1e5 (exceeds 1e2 bound)
- DB-AT-029: median ROI correlation = -0.053 (below 0.2 floor)

**Artifacts Written**:
- `db_at_028_metrics.json`: chi2_per_pixel_initial = 209,714.75
- `db_at_029_metrics.json`: median_corr_before = -0.053
- `mapping_context_fixture.json`: emitted per TOOLING-VIS-001

## Artifacts Written

All artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/`:

1. **stage_a_baseline_probe_baseline.json**: Full ledger with 27 reflection entries, each containing HKL index, amplitude, amp_sq_per_pixel, and ratios
2. **stage_a_baseline_probe_perturbed.json**: Same structure for perturbed geometry
3. **baseline_probe.log**: Console output with HKL ledger stats tables
4. **perturbed_probe.log**: Console output for perturbed run
5. **pytest_db_at_028_029.log**: Test execution log
6. **db_at_028/db_at_028_metrics.json**: Chi² metrics
7. **db_at_029/db_at_029_metrics.json**: ROI correlation metrics
8. **db_at_028/mapping_context_fixture.json**: Mapping diagnostics
9. **db_at_029/mapping_context_fixture.json**: Mapping diagnostics

## Next Step (Supervisor Decision)

**Boundary Bisection Result**:
- `|F|^2/pix` vs `Refl intensity/pix` median ratio = 1.14 → HKL ingestion likely correct
- `Stage A` vs `|F|^2/pix` median ratio = 0.093 (baseline) / 0.0043 (perturbed) → **Simulator underproduction** is the dominant mismatch

**Hypothesis**: The parity crisis originates **inside the simulator** after HKL ingestion but before Stage A baseline logic. The extreme ROI variance (0.0001 to 10.4 StgA/|F|^2 ratio) suggests:
1. Possible axis/frame/normalization mismatch in how |F| grids are interpolated or sampled
2. Potential ROI mask definition divergence between simulator and reference
3. Spot shape or beam profile modeling error that redistributes energy non-uniformly

**Recommended Next Action**:
1. Audit `dbex/nanobrag_bridge.py::build_structure_factor_grid` for axis-order/normalization conventions
2. Inspect ROI 0:[431,443,434,446] HKL=(0,2,-2) (extreme overestimate) vs ROI 0:[350,362,877,889] HKL=(4,-5,-1) (extreme underestimate) for shared properties (d-spacing, resolution, proximity to panel edge)
3. Compare simulator construction parameters (N_cells, spot_scale, mosaic spread) against contract in docs/architecture-simulator.md

**No Code Fixes Implemented**: Per input.md, this turn only added diagnostic instrumentation. Production semantic changes await supervisor directive after reviewing ledger evidence.

---

## Turn Summary

- **Added HKL-amplitude ledger** to Stage A baseline probe with 69,614 entries from refined MTZ
- **Computed amp_sq_per_pixel** = |F|^2 / n_masked_pixels for all 27 matched ROIs
- **Fail-fast validation** ensures ROI/HKL mismatches are detected immediately
- **Re-ran baseline + perturbed probes** with full ledger artifacts
- **Re-ran DB-AT-028/029 tests** to confirm parity crisis persists (chi²/pixel = 2.1e5)
- **Ledger reveals**: HKL ingestion likely correct; simulator underproduces ~9% of expected intensity in baseline mode

**Artifacts**: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/` (9 files: 2 JSON probes, 2 logs, 1 pytest log, 4 test artifacts)
