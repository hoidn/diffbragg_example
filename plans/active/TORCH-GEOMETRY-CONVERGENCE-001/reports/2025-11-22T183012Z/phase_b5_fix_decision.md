# Phase B5 Fix Decision — Code Path Discrepancy Resolution

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** B5 (Fix Implementation)
**Date:** 2025-11-22T183012Z
**Status:** **Path A SUCCESS** ✅

---

## Decision Criteria

| Metric | Expected (SUCCESS) | Observed | Pass/Fail |
|--------|-------------------|----------|-----------|
| chi²_init (before) | ~1.13M (within 2× of zero-point) | 1,133,421.0 | ✅ PASS |
| grad_log_scale_init | O(1-100), NOT ~295k | N/A (not captured) | ⚠️ N/A |
| chi²_before (convergence) | ~1.13M | 1,133,421.0 | ✅ PASS |
| Zero-point correlation | ≥0.99 | 0.9999999843 | ✅ PASS |

---

## Verdict

**Path A: FIX SUCCESS** ✅

### Evidence

1. **Zero-Point Parity Maintained:**
   - chi²_mapping = 989,811.53
   - chi²_stage_a = 989,645.63
   - abs_diff = -165.91 (within ±200 tolerance)
   - rel_diff = -0.017% (within ±0.1% tolerance)
   - correlation = 0.9999999843 (≥0.99 required)
   - **Verdict:** Zero-point check PASSED, B_ideal bugfix (commit e86fd4e) remains effective

2. **Initialization Bug FIXED (Primary Success):**
   - **Pre-fix (Phase B4):** chi²_init = 1,425,248,640 (1.425B, catastrophic)
   - **Post-fix (Phase B5):** chi²_before = 1,133,421.0 (1.133M, healthy)
   - **Improvement:** 1000× reduction (1.425B → 1.133M)
   - **Ratio to expected:** 1.14× (~990k-1.13M expected), within acceptable 2× margin
   - **Verdict:** Initialization pathology RESOLVED — script path now produces healthy chi² matching production path

3. **Code Path Alignment:**
   - **Bug Found:** Script `_stage_a_forward` set unsupported `crystal_overrides["A_star"]` key
   - **Fix Applied:**
     - Script: Convert A* to numpy, set `mosflm_a_star`, `mosflm_b_star`, `mosflm_c_star` tuples
     - `create_crystal_config`: Check for `mosflm_*_star` keys in overrides before defaulting to None
   - **Files Modified:**
     - `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:437-442` (script fix)
     - `dbex/nanobrag_bridge.py:569-586` (config function fix)
   - **Regression Guard:** test_stage_a_expansion PASSED (cell+misset path unaffected)

4. **Convergence Pathology (Separate Issue):**
   - chi²_after = 8,829,292.0 (7.8× worse than init)
   - CC_after = 0.765 (degraded from 1.0 but still positive, not catastrophic -0.045 collapse)
   - **Verdict:** Convergence STILL FAILS, but failure is DIFFERENT from pre-fix:
     - Pre-fix: Started catastrophic (1.425B), ended catastrophic (1.425B), negative CC (-0.045)
     - Post-fix: Started healthy (1.133M), degraded moderately (8.8M), positive CC (0.765)
   - **Analysis:** This is **NOT the same bug**. Initialization fix resolved code path discrepancy (H4a), but convergence pathology remains (likely H2 variance instability or H3 gradient issue).

---

## Next Actions

**Immediate (This Loop):**
1. Mark Phase B5 as **DONE** in `implementation.md` (fix successfully resolved initialization bug)
2. Update `docs/fix_plan.md` Attempts History with Path A SUCCESS verdict
3. Commit changes with message citing Phase B5 fix

**Future (Next Loop — Phase C Full Convergence Validation):**
1. Run 10-step A_scale_only convergence test to characterize remaining pathology:
   - Does chi² monotonically increase, or oscillate/plateau?
   - Are gradients still healthy (no NaN/Inf), or do they explode during optimization?
   - Does CC stay positive throughout, or collapse to negative at some step?
2. If convergence still fails with similar signature (chi² increases, CC degrades):
   - Escalate to separate initiative for optimizer/loss tuning (Phase B2-style telemetry + variance analysis)
   - OR investigate if Adam LR=1e-4 is too high for quaternion U-matrix parameterization
3. If convergence succeeds (chi² stable or improving, CC ≥0.99):
   - Proceed to Phase C D_full validation
   - Update findings ledger with CONVERGENCE-002
   - Close TORCH-GEOMETRY-CONVERGENCE-001

---

## Root Cause Summary

**Primary Bug (Phase B4 Hypothesis H4a — Code Path Discrepancy):**
- **Where:** Script `_stage_a_forward` function (line 437) and `create_crystal_config` function (lines 569-586)
- **What:** Script set unsupported `crystal_overrides["A_star"]` key; `create_crystal_config` ignored MOSFLM A* when ANY overrides present
- **Why:** U-matrix path needs to inject quaternion-derived A* via MOSFLM injection, but function only checked if overrides dict exists (not if MOSFLM keys are IN the dict)
- **Impact:** nanobrag_torch recomputed A* from cell parameters instead of using quaternion-derived A*, producing wrong geometry (U @ B_ideal_cctbx ≠ A*_mosflm → chi²=1.425B)
- **Fix:** Script converts A* to mosflm tuples; config function checks for mosflm keys in overrides before defaulting to None

**Secondary Issue (Unresolved):**
- Convergence pathology remains (chi² increases instead of decreasing during optimization)
- NOT caused by initialization bug (pre-fix had BOTH initialization AND convergence failures; post-fix has ONLY convergence failure)
- Likely causes: variance-weighted loss instability (H2), gradient magnitude issues (H3), or Adam LR incompatibility with quaternion gradients (H1)
- Recommended next step: Phase C full convergence validation with telemetry to diagnose specific pathology

---

## Artifacts

- `code_path_audit.md` — Side-by-side comparison documenting bug location
- `validation_metrics.txt` — Zero-point check + convergence metrics
- `diagnostic_b5_postfix_v2/zero_point_check.json` — Zero-point parity validation
- `diagnostic_b5_postfix_v2/block_dof_results_u_matrix.json` — Convergence results
- `diagnostic_b5_postfix_v2.log` — Full execution log
- `pytest_regression_postfix2.log` — Regression guard results (PASSED)

---

**Fix Status:** DONE (initialization bug resolved)
**Convergence Status:** PARTIAL (initialization healthy, convergence still fails — requires Phase C investigation)
