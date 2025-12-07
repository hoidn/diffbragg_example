# ARCH-IMPL-CONFORMANCE-001 Phase B.8 Implementation Summary (Loop i=118 Ralph)

## Turn Summary — Loop i=118 (Ralph Implementation)

**Status**: BLOCKED (deeper semantic issue revealed)

Implemented test mask contract fix (use `inputs.loss_mask` instead of `trusted_mask`) per Phase B.8 spec. Warm-cache test (Phase A.1) passes with perfect parity (rel_error = 0.0), but cold-path test (Phase A.2) fails with 12.77% rel_error (worse than pre-fix 2.46%), revealing deeper semantic issue in reconstruction cold-path simulation. Marked Phase B.8 blocked pending investigation of simulator config parity between Stage A and reconstruction paths.

Artifacts: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/` (pytest_phase_b8_fix.log, summary.md)

### Changes Implemented

Fixed test mask contract in `tests/architecture/test_scale_contracts.py` at 4 locations (lines 76-81, 141-144, 218-223, 286-289):
- Changed from `trusted_mask` (all trusted pixels) to `inputs.loss_mask` (ROI pixels only per spec-db-core.md:55)
- Aligns test measurement domain with mapping.py:287-288 semantics
- Added comments citing spec-db-core.md:55 and ARCH-IMPL-CONFORMANCE-001 Phase B.8

### Test Results

**Phase A.1 (warm-cache): PASS** ✓
```
masked_mean_stage_a      = 8.711842e+01
masked_mean_reconstruction = 8.711842e+01
rel_error                 = 0.000000e+00
ratio (stage_a/reconstruction) = 1.000000
```

**Phase A.2 (cold-path): FAIL** ✗
```
masked_mean_stage_a            = 8.711842e+01
masked_mean_reconstruction_cold = 9.824423e+01
rel_error                       = 1.277091e-01 (12.77%)
ratio (stage_a/reconstruction_cold) = 0.886754
```

### Metrics Progression

| Phase | Mask Domain | Stage A Mean | Reconstruction Mean | Rel Error | Ratio |
|-------|-------------|--------------|---------------------|-----------|-------|
| B.7 (before fix) | `trusted_mask` | 2.155699 | 2.102600 | 2.46% | 1.0253 |
| B.8 (after fix) | `loss_mask` | 87.11842 | 98.24423 | **12.77%** | 0.8868 |

### Key Findings

1. **Warm-cache path validated**: Phase A.1 continues to pass with perfect parity (rel_error = 0.0)
   - Cache optimization (reconstruction.py:83-86) correctly returns Stage A bragg_zero_iter
   - No mask contract issue in warm-cache path

2. **Cold-path deeper bug revealed**: Fixing mask contract exposed larger discrepancy
   - Previous 2.46% error over `trusted_mask` was averaging out a larger problem
   - When measured over correct ROI domain (`loss_mask`), reconstruction cold-path systematically overestimates by ~12.77%
   - Reconstruction produces 98.24 vs Stage A's 87.12 (ratio 0.887)

3. **Mask coverage evidence**:
   - `loss_mask.sum()` < `trusted_mask.sum()` (as expected: background >= 0 constraint removes non-ROI pixels)
   - Masked means are much higher over `loss_mask` (87.12 vs 2.16) confirming ROI pixels have higher intensity

4. **Root cause hypothesis**:
   - Cold-path reconstruction applies `masked_mean_ratio` from calibration (value: 0.027774)
   - This ratio was computed by mapping.py over `loss_mask`: `target_mean / bragg_mean`
   - But reconstruction cold-path simulation may be producing different raw intensities than Stage A in ROI regions
   - Suggests systematic bias in how cold-path simulators are configured vs Stage A simulators

### Blocked Reason

Test mask fix was implemented correctly per spec, but Phase A.2 still fails with **worse** rel_error than Phase B.7:
- Expected: rel_error < 1e-6 after mask fix
- Actual: rel_error = 12.77% (5× worse than pre-fix 2.46%)

This indicates **deeper semantic issue beyond mask contract** (per input.md Scenario 1).

### Next Steps (Escalation Required)

1. **Investigate cold-path simulation config**:
   - Compare simulator construction between Stage A (stage_a_utils.py) and reconstruction cold-path (reconstruction.py:88-223)
   - Check if N_cells, spot_scale, beam calibration are applied consistently
   - Verify HKL grid construction matches

2. **Trace masked_mean_ratio application**:
   - mapping.py computes ratio from `(raw * sqrt(spot)) bragg` over loss_mask
   - reconstruction should apply same ratio to `(raw_cold * sqrt(spot))` over loss_mask
   - Verify `raw_cold` matches `raw` when simulators have identical config

3. **Consider parity localization**:
   - Add DMI protocol (consumption-state verification) to find first divergence
   - Compare panel-by-panel outputs between Stage A and reconstruction cold-path
   - Check if discrepancy is uniform across all panels or localized

---

# ARCH-IMPL-CONFORMANCE-001 Phase B.8 Planning Summary (Loop i=118 Galph)

## Turn Summary — Loop i=117 (Galph Planning)

Loop i=117 (Ralph) implemented Phase B.7 masked_mean_ratio fallback, achieving 30× error reduction (738% → 2.5%). After 3 implementation attempts (B.5/B.6/B.7), warm-cache test passes but cold-path test blocked at 2.5% residual error. Root cause identified: **test contract mismatch** - test uses `trusted_mask` (all trusted pixels) while mapping computes `masked_mean_ratio` from `inputs.loss_mask` (ROI pixels only per spec-db-core.md:55). Phase B.8 fix: update test to use `inputs.loss_mask` for masked mean computation (harness fix, no production changes). Expected outcome: both tests PASS with rel_error < 1e-6.

## Key Findings

1. **Mask Contract Investigation** (confidence=0.98):
   - `inputs.loss_mask = (background >= 0) & trusted_mask` per inputs.py:230 (ROI pixels only)
   - mapping.py:287-288 computes `masked_mean_ratio` from `inputs.loss_mask`
   - Test uses `trusted_mask` (all trusted pixels), measuring over different domain than mapping

2. **Root Cause Mechanism**:
   - Mapping scales ALL pixels by ROI-derived ratio: `bragg *= (target[loss_mask].mean() / bragg[loss_mask].mean())`
   - Test measures over all trusted pixels: `bragg[trusted_mask].mean()`
   - When intensity distribution differs inside vs outside ROIs, scaling preserves mean within ROIs but not over all trusted pixels
   - Result: 2.5% error = distribution mismatch artifact, not implementation bug

3. **Production Code Status**: **Correct** (Phase B.7 masked_mean_ratio fallback working as designed)

4. **Test Harness Status**: **Incorrect** (measures over wrong mask domain, violates spec-db-core.md:55)

## Next Action

**Phase B.8 (Loop i=118)**: Ralph updates test_scale_contracts.py lines 77-80, 141-143, 218-220, 284-286 to use `inputs.loss_mask` instead of `trusted_mask`, expects both tests PASS with rel_error < 1e-6.

## Artifacts

- `phase_b7_root_cause_analysis.md` — Detailed investigation with evidence trail, solution specification, and compliance checklist
- `summary.md` (this file) — Concise turn summary

## Metrics Progression

| Phase | Fix | Rel Error | Ratio | Status |
|-------|-----|-----------|-------|--------|
| B.5 | double-sqrt diagnosis | 3420% | 1/35.2 | BLOCKED |
| B.6 | conditional sqrt fix | 738% | 1/8.4 | PARTIAL |
| B.7 | masked_mean_ratio fallback | 2.5% | 1.025 | PARTIAL |
| B.8 | test mask contract fix | < 0.0001% (expected) | ≈1.0 (expected) | READY |

---

**Loop**: i=118 (Galph planning)
**Timestamp**: 2025-12-07T050658Z
**Confidence**: 0.98
**Decision**: patch_ready (harness fix)
