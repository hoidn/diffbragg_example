# TOOLING-VIS-001 Loop Summary — Mapping Alignment & HKL Override

**Date:** 2025-11-25T061925Z
**Focus:** TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
**Mode:** Parity
**Branch:** integration

## Problem Statement

Per `input.md`, implement HKL override plumbing to enable scaled.mtz vs refined_structure_factors.mtz comparison for pinpointing the Stage A anti-correlation root cause.

**Quoted SPEC (docs/spec-db-conformance.md:287-315 — DB-AT-028/029):**
> - DB-AT-028: chi²-per-pixel and clamp sanity. Expectations: `chi2_per_pixel_initial ≤ 1e2`, `chi2_per_pixel_final ≤ 1e2`, clamp_fraction < 0.5.
> - DB-AT-029: ROI correlation floor `median(corr_before) ≥ 0.2`, scale_ratio_before ∈ [1e-2, 1e2].

## Implementation

### Files Modified

1. **`plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py`** — Mapping probe
   - Added `--mtz-path` CLI argument (priority: CLI > DBEX_SMOKE_HKL_PATH > scaled.mtz)
   - Separated HKL source path from DataLoad MTZ path (DataLoad always uses scaled.mtz)
   - Fixed diagnostics extraction from nested `hkl_telemetry` dict
   - File pointers: lines 284-289 (CLI arg), 303-317 (path resolution), 368-372 (hkl_source_path attr), 143-144 & 209-210 (diagnostic extraction)

2. **`dbex/nanobrag_bridge.py:2072`** — Flex.double conversion fix
   - Wrapped `hkl_amplitudes.mean()` in `np.asarray()` to handle cctbx flex.double objects
   - File pointer: dbex/nanobrag_bridge.py:2072

3. **`dbex/vis/mapping.py:142-166`** — Mapping context builder
   - Check for `dataload.args.hkl_source_path` attribute
   - Load refined MTZ via `load_refined_mtz` when path contains "refined_structure_factors"
   - Fallback to fixtures directory check for backward compatibility
   - File pointer: dbex/vis/mapping.py:142-166

4. **`tests/dbex/test_torch_refine_smoke.py:96-126`** — Test fixture
   - Updated `refgeom_dataload` to honor `DBEX_SMOKE_HKL_PATH`
   - DataLoad uses scaled.mtz, HKL source path in `hkl_source_path` attribute
   - File pointer: tests/dbex/test_torch_refine_smoke.py:96-126

## Probe Results

### Scaled HKL (`scaled.mtz`)
```
HKL source: raw
HKL count: 69614
ROI CC median: -0.039912
Scale ratio (masked): 8.4506e-01
Scale ratio (unmasked): 2.4114e+00
CPU/GPU parity: mean_abs_diff=5.29e-05, roi_cc_diff=0.000004
```

### Refined HKL (`refined_structure_factors.mtz`)
```
HKL source: refined
HKL count: 69614
ROI CC median: -0.039912
Scale ratio (masked): 2.5872e-01
Scale ratio (unmasked): 1.8052e+00
CPU/GPU parity: mean_abs_diff=4.54e-05, roi_cc_diff=0.000004
```

**Key Observations:**
1. ROI correlation **identical** (-0.040) regardless of HKL source → anti-correlation is **not** HKL-dependent
2. Scale ratios differ significantly: refined HKL yields 3.27× lower masked ratio
3. CPU/GPU parity excellent for both sources (<0.01% relative difference)

## DB-AT-028/029 Test Results (Refined HKL)

**Command:**
```bash
DBEX_SMOKE_HKL_PATH=tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz \
DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
```

**Status:** ❌ FAILED (both tests)

### DB-AT-028 Failure
```
AssertionError: chi²/pixel initial 1.084e+05 exceeds 1e2 bound
Actual: 108367.84 vs Expected: ≤100.0
```

**Metrics:**
- chi²/pixel initial: 1.084e+05 (1000× over bound!)
- chi²/pixel final: 1.090e+05 (no improvement)
- ROI CC before: -0.050
- ROI CC after: -0.051 (regression)
- Clamp fraction: 0.0 (sigma floor not engaged)
- log_scale_baseline: 20.15

### DB-AT-029 Failure
```
AssertionError: median ROI correlation before refinement -0.050 below 0.2 floor
Actual: -0.050 vs Expected: ≥0.2
```

**Metrics:**
- median_corr_before: -0.050 (below 0.2 floor by 0.25!)
- median_corr_after: -0.051 (slight regression)
- scale_ratio_before: 0.011 (within [1e-2, 1e2] spec band but very small)
- n_rois: 91

**Metadata Bug Identified:**
- `hkl_source` and `hkl_path` fields in metrics show "scaled.mtz" despite refined HKL being used (evidenced by scale_ratio_mapping_masked=0.259 matching refined probe)
- Root cause: test extracts from `diagnostics.get("hkl_source")` but field is in `diagnostics["hkl_telemetry"]["hkl_source"]`
- Needs fix: update test_stage_a_smoke_parity.py:99-102 to read from nested dict

## Analysis

### Critical Finding: HKL-Independent Anti-Correlation

The **negative ROI correlation (-0.04 to -0.05)** persists regardless of HKL source:
- Probe (mapping forward only): -0.040 for both scaled and refined
- DB-AT-029 (with refinement): -0.050 before and after

**Conclusion:** The Stage A anti-correlation is **NOT** caused by HKL provenance. The root cause must be:
1. **Geometry miscalibration** — Zero-point U-matrix or detector mapping issue
2. **Calibration mismatch** — spot_scale_override=3.18e17 is extreme and suspicious
3. **Forward model bug** — Systematic error in Bragg simulation independent of HKL

### Chi-Squared Scale Explosion

The chi²/pixel values (1.08e5) are **1000× higher** than the DB-AT-028 spec bound (1e2), indicating:
- Model-data mismatch is catastrophic, not just poor correlation
- log_scale_baseline=20.15 suggests extreme scaling compensation
- spot_scale_override=3.18e17 is physically implausible

## Artifacts

- `mapping_scaled/mapping_forward_cpu_gpu.json` + `probe.log`
- `mapping_refined/mapping_forward_cpu_gpu.json` + `probe.log`
- `db_at_028/db_at_028_metrics.json`
- `db_at_029/db_at_029_metrics.json`
- `pytest_db_at_028_029.log` (2 FAILED, 51.7s runtime)
- `pytest_db_at_028_029_collect.log` (2 tests collected)
- `summary.md` (this file)

## Next Actions

1. **Fix metadata extraction** — Update test_stage_a_smoke_parity.py:99-102 to read `hkl_source`/`hkl_path` from `diagnostics["hkl_telemetry"]` nested dict
2. **Investigate spot_scale_override** — Value 3.18e17 is extreme; check if calibration loading is broken or config_torch.json has bad data
3. **ROI anti-correlation root cause** — Since HKL source doesn't affect correlation, focus on geometry zero-point (U-matrix) or detector mapping issues
4. **Consider canonical HKL** — If refined HKL becomes normative, update DB-AT-028/029 baselines and document in TESTING_GUIDE.md

## Compliance Checklist

- ✓ Acceptance scope: TOOLING-VIS-001 (DB-AT-028/029 diagnostics)
- ✓ Module scope: tools/vis (probe scripts, no core algorithm changes)
- ✓ SPEC alignment: docs/spec-db-conformance.md:280-366 (DB-AT-028/029)
- ✓ Search first: verified no duplicate HKL override implementations
- ✓ Static analysis: N/A (Python scripts with existing patterns)
- ✓ Tests executed: DB-AT-028/029 with refined HKL, both FAILED (expected)
- ✓ Collection verified: 2 tests collected
- ✓ Artifacts saved: mapping probes + DB-AT metrics in reports/2025-11-25T061925Z/
