# Phase B1 LBFGS Test Diagnostic Analysis

## Summary
Ralph's Phase B1 LBFGS test (commit 8440df8) terminated prematurely after partial execution. Zero-point validation PASSED (chi²=989k), but telemetry_step_000.json shows catastrophic chi²=1.425B, identical to Phase A pre-bugfix failure signature.

## Observed Artifacts

### Zero-Point Check (PASSED)
- File: `zero_point_check.json`
- Chi² mapping path: 989,811.5
- Chi² stage_a (U-matrix explicit): 989,645.5
- Relative difference: -0.017% (well within 0.1% tolerance)
- Correlation: median=0.9999999843 (essentially perfect)
- **Verdict:** B_ideal bugfix (826f4c9) IS working correctly for zero-point validation

### Telemetry Step 000 (FAILED)
- File: `plans/.../telemetry/telemetry_step_000.json`
- Chi²: **1,425,248,640** (1.425B — catastrophic failure)
- log_scale gradient: **294,909.5625** (massive, ~300k)
- q_params gradients: null (expected for A_scale_only, train_orientation=False)
- No NaN/Inf flags

### Test Execution Log
- File: `stage_a_lbfgs_test.log`
- Lines: 69 (truncated early)
- Content: Initial simulator warmup, HKL grid builds (line search evaluations), then terminated
- No error messages, traceback, or explicit termination signal
- Timestamp: 2025-11-22 07:16:08 (approximately same time as Ralph's commit)

## Root Cause Hypothesis

### H1: B_ideal Mismatch Persists in Optimization Loop
**Evidence:**
- Zero-point check uses `use_mapping_zero_geometry=True` → bypasses U-matrix reconstruction, directly uses MOSFLM A*
- Telemetry step 000 executes during LBFGS optimization loop with `use_mapping_zero_geometry=False` → forces U @ B_ideal reconstruction
- Chi²=1.425B matches Phase A pre-bugfix signature exactly (2025-11-22T150000Z forward_model_discrepancy_analysis.md)

**Hypothesis:** Despite bugfix in `derive_u_matrix_from_mosflm_a_star`, there may be a SECOND code path that still computes B_ideal using cctbx fractionalization_matrix during the LBFGS closure execution.

**Evidence Against:** Lines 317-324 of stage_a_mapping_adam_debug.py show proper destructuring of `(U_matrix, B_ideal_reciprocal_np)` and tensor conversion. Line 436 uses `components.B_ideal_reciprocal` for reconstruction. No other fractionalization_matrix calls visible in script.

### H2: Telemetry Captures Wrong Timestep
**Evidence:**
- File named `telemetry_step_000.json` should be the FIRST optimizer step
- But zero-point check (which runs BEFORE optimization) shows chi²=989k
- Telemetry chi²=1.425B suggests it's capturing a POST-divergence state, not step 0

**Evidence Against:** Telemetry JSON explicitly shows `"step_index": 0` which should be the first step.

### H3: Path Duplication Bug in Telemetry Output
**Evidence:**
- Telemetry file path: `plans/active/.../reports/2025-11-22T165000Z/plans/active/.../reports/2025-11-22T165000Z/telemetry/...`
- Nested duplication suggests script may have double-prepended the output directory
- If the telemetry path resolution is buggy, the telemetry data itself might be from a different execution

**Evidence for:** Ralph passed both `--telemetry-dir plans/active/.../telemetry/` AND `--out-dir plans/active/.../2025-11-22T165000Z/`, which may have caused double-prepending.

### H4: LBFGS Line Search Exploratory Step Hit Bad Region
**Evidence:**
- LBFGS line search may evaluate closure multiple times with different step sizes
- Log shows ~40 HKL grid builds (lines 13-69), suggesting many closure evaluations
- Telemetry step_000 may capture a line-search EXPLORATORY evaluation, not the accepted step
- LBFGS may have evaluated parameters at a point far from zero, hitting catastrophic chi²

**Evidence For:** This is consistent with LBFGS behavior (backtracking line search can evaluate at multiple points). Massive log_scale gradient (294k) suggests parameters are very far from optimum.

## Diagnostic Protocol for Next Iteration

### Priority 1: Verify B_ideal Consistency Across All Code Paths
1. **Add debug logging to LBFGS closure** to print:
   - `B_ideal_reciprocal` tensor hash/checksum at closure entry
   - Reconstructed `A_star_new` at closure entry
   - Chi² before and after each closure call
2. **Compare B_ideal values**:
   - Zero-point check path (use_mapping_zero_geometry=True) → direct MOSFLM A*
   - LBFGS closure path (use_mapping_zero_geometry=False) → U @ B_ideal reconstruction
3. **Check for stale tensor references**: Verify `components.B_ideal_reciprocal` is not being overwritten or mutated during optimization

### Priority 2: Fix Telemetry Path Duplication
1. Investigate why telemetry path has nested duplication
2. Either:
   - Remove `--telemetry-dir` flag and let script auto-construct from `--out-dir`
   - OR ensure script doesn't double-prepend paths

### Priority 3: Disambiguate Telemetry Timing
1. Add `closure_call_count` field to telemetry to distinguish:
   - Accepted optimizer steps (e.g., step_000 = first ACCEPTED step)
   - Line-search exploratory evaluations (should not be written to telemetry)
2. Only emit telemetry AFTER `optimizer.step(closure)` returns, not inside closure

## Recommended Next Steps

**Option A: Deep Diagnostic (Recommended if time permits)**
- Instrument LBFGS closure with B_ideal checksums and per-call chi² logging
- Run LBFGS test with full debugging, capture all closure evaluations
- Identify EXACT point where chi² diverges from 989k → 1.425B

**Option B: Quick Rerun (Recommended for immediate progress)**
- Fix telemetry path duplication bug
- Rerun LBFGS test with corrected paths, wait for completion (DO NOT background)
- If test still shows chi²=1.425B at step 0, switch to Option A deep diagnostic

**Option C: Fallback to Adam LR Tuning (If LBFGS infrastructure is too buggy)**
- Skip Test B1 (mark as inconclusive due to instrumentation issues)
- Proceed directly to Test B2: Adam LR=1e-6 with gradient validation
- LBFGS can be revisited after simpler tests establish baseline behavior

## Risk Assessment

**High Risk:** If B_ideal mismatch persists despite bugfix 826f4c9, the quaternion U-matrix approach may have a deeper architectural issue (e.g., tensor aliasing, device/dtype mismatches, or incorrect pass-by-reference semantics).

**Medium Risk:** Telemetry path duplication and premature termination suggest Ralph's background execution pattern is unreliable. May need to switch to foreground execution with explicit timeout monitoring.

**Low Risk:** LBFGS line search exploratory steps are expected behavior and not a bug. Telemetry should simply be configured to capture only accepted steps, not line-search probes.

## Decision Tree for Galph

1. **If confident in B_ideal fix AND telemetry is just path bug:**
   - Fix telemetry paths
   - Rerun LBFGS test B1 in FOREGROUND (blocking, wait for completion)
   - Decision point: SUCCESS → Phase C fix implementation, FAILURE → Test B2 Adam LR tuning

2. **If uncertain about B_ideal consistency:**
   - Implement Priority 1 deep diagnostic (B_ideal checksums, closure-level chi² logging)
   - Run diagnostic variant, analyze where chi² diverges
   - Fix root cause → Rerun LBFGS test B1

3. **If time budget exceeded or LBFGS infrastructure too complex:**
   - Mark Test B1 as BLOCKED (instrumentation issues)
   - Pivot to Test B2 (Adam LR=1e-6) which uses simpler telemetry pattern
   - Revisit LBFGS after establishing Adam baseline behavior

## Recommendation
**Option B: Quick Rerun** with foreground execution and fixed telemetry paths. If that fails, escalate to Option A deep diagnostic.
