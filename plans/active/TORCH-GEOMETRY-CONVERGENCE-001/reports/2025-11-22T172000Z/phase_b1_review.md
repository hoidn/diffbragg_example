# Phase B1 Prior Attempt Review

## Summary
Ralph's Phase B1 LBFGS test (commit 8440df8, 2025-11-22T165000Z) executed zero-point validation successfully but the LBFGS optimization loop terminated prematurely with incomplete artifacts and catastrophic chi² at step 0.

## Zero-Point Validation (PASSED)

**File:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/zero_point_check.json`

**Chi² Values:**
- Mapping path: **989,811.5**
- Stage A (U-matrix explicit): **989,645.5**
- Absolute difference: -166.0
- Relative difference: **-0.017%** (well within 0.1% tolerance ✓)
- Correlation median: **0.9999999843** (essentially perfect)

**Verdict:** B_ideal bugfix (commit 826f4c9) IS working correctly in the zero-point validation code path. The `derive_u_matrix_from_mosflm_a_star` function properly returns `(U_matrix, B_ideal_reciprocal)` and both are being used correctly for A* reconstruction during zero-point checks.

## Telemetry Step 000 (CATASTROPHIC FAILURE)

**File:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/telemetry/telemetry_step_000.json`

**Metrics:**
- Chi²: **1,425,248,640** (1.425 billion — catastrophic)
- log_scale gradient: **294,909.5625** (~295k — massive)
- q_params gradients: null (expected for A_scale_only with train_orientation=False)
- No NaN/Inf flags

**Comparison to Phase A Pre-Bugfix:**
This chi²=1.425B matches EXACTLY the Phase A forward model discrepancy signature before the B_ideal bugfix. This strongly suggests that the LBFGS optimization loop is hitting a code path where B_ideal is still being computed incorrectly (possibly via cctbx fractionalization_matrix instead of the MOSFLM-derived value).

## Telemetry Path Duplication Issue

**Observed Path:**
```
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/
    telemetry/telemetry_step_000.json
```

**Root Cause (Identified):**
In `stage_a_mapping_adam_debug.py:1662-1670`, when `--telemetry-dir` is provided as a relative path, it gets resolved relative to `--out-dir`:

```python
if args.telemetry_dir is not None:
    telemetry_p = PPath(args.telemetry_dir)
    if not telemetry_p.is_absolute():
        telemetry_dir_resolved = str(out_root / telemetry_p)  # PREPENDS out_root
    else:
        telemetry_dir_resolved = args.telemetry_dir
```

Ralph's command likely passed:
- `--out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/`
- `--telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/telemetry/`

Since `--telemetry-dir` starts with the same prefix as `--out-dir`, the script treated it as "relative" and prepended `out_root`, causing the path duplication.

**Fix:** Remove `--telemetry-dir` flag entirely and let the script auto-construct the telemetry path from `--out-dir`.

## Test Execution Log

**File:** `stage_a_lbfgs_test.log` (69 lines, truncated)

**Content:**
- Initial simulator warmup completed
- Multiple HKL grid builds (~40 instances, lines 13-69)
- No error messages, tracebacks, or explicit termination signals
- Timestamp: 2025-11-22 07:16:08

**Analysis:** The log shows many HKL grid builds, consistent with LBFGS backtracking line search behavior (closure evaluated multiple times per step). The test appears to have been terminated prematurely (possibly backgrounded and orphaned), leaving incomplete artifacts.

## Hypothesis Selection

### H1: B_ideal Mismatch in LBFGS Closure (MOST LIKELY)

**Evidence FOR:**
1. Zero-point check uses `use_mapping_zero_geometry=True`, which bypasses U @ B_ideal reconstruction and directly uses MOSFLM A* → chi²=989k (correct)
2. LBFGS optimization uses `use_mapping_zero_geometry=False`, forcing U @ B_ideal reconstruction → chi²=1.425B (catastrophic)
3. Chi²=1.425B matches pre-bugfix signature exactly
4. Massive log_scale gradient (295k) suggests parameters are far from optimum, consistent with wrong B_ideal being used

**Evidence AGAINST:**
1. Lines 317-324 of `stage_a_mapping_adam_debug.py` show proper destructuring of `(U_matrix, B_ideal_reciprocal_np)` from the bugfixed `derive_u_matrix_from_mosflm_a_star`
2. Line 436 uses `components.B_ideal_reciprocal` for A* reconstruction
3. No obvious alternate code paths that would compute B_ideal differently

**Mechanism (Speculative):**
The bugfix may be incomplete. Possible causes:
- `components.B_ideal_reciprocal` is being overwritten/mutated during optimization
- Different code path in LBFGS closure than in zero-point check
- Tensor aliasing or device/dtype mismatch causing B_ideal to revert to wrong value
- Pass-by-reference semantics causing B_ideal to be recomputed somewhere

### H2: Telemetry Captures Line-Search Exploratory Step (POSSIBLE)

**Evidence FOR:**
1. LBFGS line search evaluates closure multiple times with different step sizes (backtracking)
2. Log shows ~40 HKL grid builds, suggesting many closure evaluations
3. Telemetry may capture an EXPLORATORY evaluation far from the zero point, not the accepted step
4. step_index=0 should be first step, but chi² suggests it's from an intermediate line-search probe

**Evidence AGAINST:**
1. Telemetry is emitted BEFORE optimizer.step() call (lines 850-904, 923-977), so it should capture the parameter state before the step, not during line search
2. If this were a line-search probe, we'd expect to see multiple telemetry files with step_index=0 (one for each probe), but there's only one

### H3: Telemetry Path Duplication Caused Data Corruption (UNLIKELY)

**Evidence FOR:**
1. Path duplication is confirmed (nested directory structure)
2. If telemetry writes were failing silently, data could be from a different run

**Evidence AGAINST:**
1. Telemetry file exists and is well-formed JSON
2. Path duplication is just a cosmetic issue, doesn't affect data integrity
3. The chi² value is too specific (1.425B) to be random corruption

### H4: Test Terminated Prematurely (SECONDARY ISSUE)

**Evidence:**
1. Log has only 69 lines (truncated)
2. No `block_dof_results.json` file
3. Test was likely backgrounded (based on Ralph's commit pattern)
4. No error messages or exit code recorded

**Verdict:** This is a real issue (background execution is unreliable), but it's a consequence of H1, not the root cause.

## Recommended Fix

**Primary:** Remove `--telemetry-dir` flag from test invocation. Let script auto-construct telemetry path as `{out_dir}/telemetry/`.

**Execution:** Run test in FOREGROUND (blocking, no background) with explicit timeout (1200s).

**Expected Outcome:**
- If H1 is correct (B_ideal mismatch): chi²=1.425B persists at step 0 → escalate to deep diagnostic
- If H1 is wrong (telemetry timing): chi²~1M at step 0, normal convergence → proceed to Phase C

## Next Actions

1. Remove `--telemetry-dir` from command line (rely on auto-construction)
2. Run LBFGS test in foreground with 1200s timeout
3. If chi²=1.425B persists: implement deep diagnostic with B_ideal checksums in closure
4. If chi²~1M: proceed with convergence metric extraction and Phase C fix implementation
