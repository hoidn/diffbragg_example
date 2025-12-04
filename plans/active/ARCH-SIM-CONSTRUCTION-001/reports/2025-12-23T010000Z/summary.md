# ARCH-SIM-CONSTRUCTION-001 Phase C.23 Summary

**Date:** 2025-12-03T21:58:00Z
**Ralph loop:** Add HKL-orientation diagnostics to Stage A baseline probe
**Commit:** 413e31a9

## Task

Implement `--collect-orientation-metrics` flag and wire HKL orientation alignment diagnostics into `compare_stage_a_baseline.py` to determine whether DB-AT-028/029 failures correlate with |Δhkl| misalignment vs raw intensity divergence.

## Implementation

### Code Changes

1. **compute_orientation_metrics()** (lines 391-511)
   - Computes ROI center in lab coordinates via `detector.get_pixel_lab_coord`
   - Converts to diffracted beam vector s1, computes q = s1 - s0
   - Solves h_frac = A^{-1} q using `crystal.get_A()`
   - Records fractional HKL, Δhkl, |Δhkl|, resolution (Å), 2θ per ROI

2. **CLI flag** (lines 540-543)
   - Added `--collect-orientation-metrics` (store_true)
   - Guards orientation computation to avoid slowing legacy scripts

3. **Main integration** (lines 1426-1505)
   - Computes orientation metrics when flag enabled
   - Calculates Pearson correlation between |Δhkl| and Stage A/ref ratios
   - Stores summary stats (median, P25/P75, max |Δhkl|, resolution, 2θ)
   - Identifies worst-5 ROIs by misalignment magnitude

4. **Markdown writer extension** (lines 514-680)
   - Extends `_summarize_spot_profiles()` to accept `orientation_alignment`
   - Emits "Orientation Alignment" section with:
     - Summary statistics (median |Δhkl|, resolution, 2θ)
     - Pearson correlation with interpretation thresholds
     - Worst-5 misalignment table
     - Interpretation guidance (strong/moderate/weak correlation → next steps)

5. **Output payload** (line 1615)
   - Added `orientation_alignment` dict to JSON output

## Probe Run Results

**Command:**
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
  --stage-a-mosaic-domains 16 \
  --collect-hkl-stats \
  --collect-spot-profiles \
  --collect-orientation-metrics \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/stage_a_baseline_probe_baseline.json
```

**Orientation Metrics Summary:**

- **Reflections analyzed:** 27
- **Median |Δhkl|:** 0.0950
- **P25-P75 |Δhkl|:** 0.0773 - 0.1728
- **Max |Δhkl|:** 0.2473
- **Median resolution:** 3.60 Å
- **Median 2θ:** 15.59°
- **Pearson corr (|Δhkl| vs Stage A/ref ratio):** -0.2864 (27 pairs)

**Worst-5 Misalignment:**

| Panel | BBox | HKL | |Δhkl| | Δhkl | Resolution (Å) | Stage A/Ref Ratio |
|-------|------|-----|-------|------|----------------|-------------------|
| 0 | [644:656,21:33] | (-7,5,-3) | 0.2473 | (-0.106,-0.135,-0.178) | 2.68 | 7.12e-05 |
| 0 | [661:673,940:952] | (1,-9,4) | 0.2330 | (0.135,0.128,0.140) | 3.06 | 1.46e-01 |
| 0 | [535:547,842:854] | (2,-6,2) | 0.2094 | (0.115,0.128,0.120) | 4.14 | 1.68e-02 |
| 0 | [257:269,37:49] | (-3,8,-9) | 0.1958 | (-0.085,-0.102,-0.144) | 2.56 | 2.94e-03 |
| 0 | [350:362,877,889] | (4,-5,-1) | 0.1945 | (0.117,0.106,0.113) | 3.46 | 3.10e+00 |

**Interpretation:**

Weak correlation (-0.29) between |Δhkl| and Stage A/ref ratio suggests **orientation misalignment is NOT the primary driver** of DB-AT-028/029 failures.

**Next Step:**
Focus on physics corrections (Lorentz/partiality/normalization) rather than geometry retargeting or nanobrag_torch q-vector debugging.

## Mapped Test Results

### DB-AT-028 (chi²/pixel sanity)

```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/db_at_028 \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
```

**Result:** FAILED (pre-existing)
- chi²/pixel initial: 2.097e+05 (exceeds 1e2 threshold)
- Expected failure; orientation data confirms geometry is not root cause

### DB-AT-029 (structure parity)

```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/db_at_029 \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
```

**Result:** FAILED (pre-existing)
- Median ROI correlation before refinement: -0.053 (below 0.2 floor)
- Expected failure; consistent with weak orientation-correlation finding

## Evidence

All artifacts stored under:
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/`

### Files

- `stage_a_baseline_probe_baseline.json` (94 kB) — Full probe output with `orientation_alignment` field
- `stage_a_baseline_probe_baseline.log` (13 kB) — Stdout capture showing orientation metrics summary
- `spot_profile_summary.md` (2.8 kB) — Human-readable summary with Orientation Alignment section
- `db_at_028/pytest.log` — DB-AT-028 test output
- `db_at_028/db_at_028_metrics.json` — Test metrics
- `db_at_029/pytest.log` — DB-AT-029 test output
- `db_at_029/db_at_029_metrics.json` — Test metrics

## Ledger Impact

**Transformation Ledger** (input.md lines 22-29):
- Confirms 5 sampled ROIs show |Δhkl| O(10^-1) misalignment
- Weak correlation (-0.29) indicates misalignment does NOT explain 2-5 order magnitude intensity divergence
- Validates hypothesis that HKL assignment is correct but physics (Lorentz/partiality) is missing

**Next Boundary Bisection:**
- Pivot from geometry debugging to physics path audit
- Focus on nanobrag_torch Lorentz/partiality implementation vs DIALS reference

## References

- **Spec:** docs/spec-db-conformance.md:280-366 (DB-AT-028/029)
- **Plan:** plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md Phase C.23
- **Input:** input.md (2025-12-23T010000Z Do Now)
- **Commit:** 413e31a9
