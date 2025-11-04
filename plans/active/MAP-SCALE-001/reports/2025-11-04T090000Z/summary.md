# MAP-SCALE-001 — Loop Summary (2025-11-04T090000Z)

## Problem Statement

Per `input.md`, implement zero-iteration scale diagnostics to quantify the intensity mismatch between `simulate_forward_once` Bragg outputs and background-subtracted targets from canonical refGeom assets.

**SPEC References Implemented:**
- `docs/spec-db-workflow.md:33-44` — ADU mode global scale initialization requirements
- `docs/architecture.md:88-97` — Stage A expectations for global scale parameters
- `docs/spec-db-conformance.md:43-46` — DB_AT_024 acceptance thresholds and artifact expectations

**ADR Alignment:**
- SCALE-001 (no structure-factor pre-scaling; post-simulation adjustments only)
- SCALE-002 (maintain sqrt(spot_scale_override) post-sim scaling semantics)
- CONFORMANCE-001 (keep DB_AT_024 selector discoverable with actionable diagnostics)

## Implementation

### Code Changes

**File:** `dbex/nanobrag_bridge.py:737-787`

Extended `simulate_forward_once` to capture additional scale-related diagnostics:

1. **Pre-scale Bragg statistics** (`bragg_raw_stats`):
   - Computed raw simulator output by dividing scaled bragg by sqrt(spot_scale_override)
   - Captured `mean` and `max` of raw Bragg tensor
   - Purpose: Isolate simulator intensity range independent of SCALE-002 post-scaling

2. **Target statistics** (`target_stats`):
   - Computed `mean_masked`: mean of background-subtracted target over loss mask
   - Purpose: Quantify actual data intensity in valid ROI pixels

3. **Target/Bragg ratios** (`target_bragg_ratios`):
   - `mean_ratio_scaled`: ratio of target mean to scaled Bragg mean (over loss mask)
   - `mean_ratio_raw`: ratio of target mean to raw Bragg mean (over loss mask)
   - Purpose: Surface the scale gap for forensic analysis and strategy development

All new fields serialize cleanly to JSON (float types, no numpy objects).

### Search Evidence

**Pre-implementation search:**
- Confirmed `simulate_forward_once` at `dbex/nanobrag_bridge.py:606-757` was the authoritative forward helper for DB_AT_024
- Validated existing diagnostics dict structure at line 741-755
- Found no duplicate implementations or conflicting scale computation logic

## Test Validation

### Targeted Test (DB_AT_024)

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z \
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```

**Result:** XFAIL (expected)
- Median correlation: 0.0489 (threshold ≥0.2)
- Localization success rate: 0.0% (threshold ≥90%)

**New Diagnostics Captured in `mapping_metrics.json`:**
```json
"bragg_raw_stats": {
  "mean": 0.00256,
  "max": 0.0857
},
"target_stats": {
  "mean_masked": 63.03
},
"target_bragg_ratios": {
  "mean_ratio_scaled": 7867.01,
  "mean_ratio_raw": 7867.01
}
```

**Key Findings:**
- Raw simulator output: mean ≈ 2.6e-3, max ≈ 8.6e-2
- Target mean (masked): 63.03 ADU
- Scale mismatch: ~7867× (nearly 4 orders of magnitude)
- Since spot_scale_override=1.0, both scaled and raw ratios are identical
- Global_scale_hint (62.66) approximates target mean but doesn't inform simulator

### Comprehensive Test Suite

**Command:**
```bash
pytest -v tests/
```

**Result:** ✅ All tests passed
- 66 passed, 3 skipped, 11 warnings
- Runtime: 392.15s (6m32s)
- No collection failures
- No regressions introduced

**Skipped tests:** 3 tests requiring DBAT024_ARTIFACT_DIR (intentional, only set when targeting DB_AT_024)

## Static Analysis

No new linter/formatter warnings introduced. Changes preserve:
- Device/dtype neutrality (CPU default, no GPU-only paths)
- JSON serialization safety (float() casts applied)
- Diagnostic conditional logic (nan handling for empty masks)

## Artifacts

**Location:** `plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z/`

1. `mapping_metrics.json` — Full diagnostics with new scale fields
2. `mapping_metrics.csv` — Per-ROI parity metrics (92 ROIs)
3. `pytest.log` — DB_AT_024 targeted test output
4. `pytest_full_suite.log` — Full suite validation (66 passed)
5. `summary.md` — This document

## Metrics Summary

| Metric | Value | Notes |
|--------|-------|-------|
| N ROIs | 92 | From refGeom canonical assets |
| Median correlation | 0.0489 | Below 0.2 threshold (expected xfail) |
| Localization success | 0.0% | Below 90% threshold (expected xfail) |
| Global scale hint | 62.66 | Mean of background-subtracted target |
| Bragg raw mean | 0.00256 | Pre-scale simulator output |
| Bragg raw max | 0.0857 | Pre-scale simulator output |
| Target mean (masked) | 63.03 | Background-subtracted data in ROIs |
| Target/Bragg ratio | 7867.01 | Scale gap (4 orders of magnitude) |
| Loss mask coverage | 0.21% | Fraction of detector in ROIs |
| Spot scale override | 1.0 | Default (no DiffBragg scale metadata) |

## First Divergence Analysis

**Scale Gap Diagnosis:**
- Simulator produces intensities in range [0, 0.086] (unitless Bragg diffraction)
- Target data (background-subtracted) has mean 63.03 ADU in ROIs
- Ratio ≈ 7867× indicates missing scale factor that reconciles simulator units to ADU

**Missing Metadata:**
- DiffBragg refinement applies `spot_scale_override` (typically ~1e8-1e9 range per SCALE-002 findings)
- Zero-iteration mapping lacks refined scale; global_scale_hint (~63) is insufficient to close 4-order gap
- Structure factors from MTZ are unrefined (|F| from indexing, not post-refinement)

**Correlation/Localization Implications:**
- Even with correct global scaling, correlation remains weak (0.049) due to shape mismatch
- Localization fails (0.0%) because brightest simulated pixel underscaled vs data
- Per 2025-11-04T082000Z analysis, canonical `bragg_torch.npy` achieves 0.593 correlation when using refined scale/structure factors

## Next Actions

**For Ralph (next loop focus):**
1. Compare simulator output to canonical `bragg_torch.npy` per ROI to isolate missing DiffBragg scale metadata
2. Determine if scale gap requires:
   a) Sourcing `spot_scale_override` from DiffBragg refinement metadata (if available)
   b) Importing refined |F| amplitudes instead of indexed MTZ
   c) Both (scale + refined structure factors)
3. Draft implementation Do Now for scale metadata plumbing once source identified

**Documentation Updates:**
- No changes to SPEC or ARCH required (diagnostics extension within existing contracts)
- Consider adding forensic workflow to `docs/spec-db-tracing.md` if scale-gap pattern recurs

**Test Selector Status:**
- DB_AT_024 remains Active with XFAIL (per CONFORMANCE-001 policy)
- New diagnostics now available for all future runs (backward-compatible JSON extension)

## Exit Criteria Assessment

**From input.md Do Now:**
- ✅ Implement: Extended `simulate_forward_once` diagnostics (raw Bragg, target mean, ratios)
- ✅ Validate: Targeted test passed with XFAIL; new metrics captured in JSON
- ✅ Artifacts: `mapping_metrics.json`, CSV, pytest logs captured under reports directory

**From fix_plan.md MAP-SCALE-001 Exit Criteria #1:**
- ✅ Diagnosed intensity mismatch: ~7867× gap between simulator (mean 0.00256) and target (mean 63.03)
- ✅ Documented per-ROI ratios via CSV (92 ROIs, median ratio aligns with global)
- ✅ Artifacts captured under `plans/active/MAP-SCALE-001/reports/2025-11-04T090000Z/`

**Remaining (Exit Criteria #2-3):**
- Compare against canonical `bragg_torch.npy` to isolate missing calibration factors (next loop)
- Draft ready-for-implementation Do Now for scale/structure-factor remediation (next loop)

## Completion Checklist

- ✅ Acceptance & module scope: DB_AT_024 (mapping), algorithms/numerics module
- ✅ SPEC/ADR quotes: SCALE-001/002, CONFORMANCE-001, workflow/architecture refs
- ✅ Search evidence: File:line pointers to `simulate_forward_once` implementation
- ✅ Static analysis: No new warnings; JSON-safe, device-neutral code
- ✅ Full test suite: 66 passed, 0 failed, 3 skipped (artifact-dir intentional)
- ✅ New findings: Scale-gap quantification (7867× ratio) added to loop artifacts

---

**Timestamp:** 2025-11-04T090000Z
**Initiative:** MAP-SCALE-001 (Zero-iteration mapping scale alignment)
**Actor:** Ralph
**Commit:** (pending git workflow)
