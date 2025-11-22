# Phase B1 LBFGS Test Rerun Summary

## Loop ID
2025-11-22T172000Z

## What Was Done
1. **Reviewed prior Phase B1 attempt** (2025-11-22T165000Z) showing premature termination with telemetry path duplication and catastrophic chi² at step 0
2. **Diagnosed telemetry path duplication bug** in stage_a_mapping_adam_debug.py:1662-1670 where relative paths get prepended with out_root, causing nested directory structure when already-absolute path is passed
3. **Fixed telemetry paths** by passing `--telemetry-dir telemetry` (simple relative path) instead of full path; telemetry now correctly written to `{out_root}/telemetry/`
4. **Reran LBFGS Test B1** in foreground (blocking, no background) with 1200s timeout and corrected telemetry paths
5. **Extracted convergence metrics** from partial artifacts (test timed out after completing only 2/10 steps)
6. **Synthesized decision document** (`phase_b1_decision.md`) selecting **Path B: LBFGS Convergence FAILURE** with escalation to deep diagnostic
7. **Updated implementation plan** checklist (B1 marked BLOCKED with Path B verdict)
8. **Updated fix_plan.md** Attempts History with comprehensive diagnostic entry

## Results

### Zero-Point Validation (PASSED ✓)
- Chi² mapping: 989,811.5
- Chi² stage_a: 989,645.5
- Relative difference: -0.017% (well within 0.1% tolerance)
- Correlation: 0.9999999843
- **Verdict:** B_ideal bugfix (826f4c9) works correctly in zero-point code path (use_mapping_zero_geometry=True)

### LBFGS Step 000 (CATASTROPHIC FAILURE ✗)
- Chi²: **1,425,248,640** (1.425 billion)
- log_scale gradient: 294,909.5625 (~295k)
- **Verdict:** EXACTLY the same catastrophic signature as pre-bugfix Phase A, confirming B_ideal mismatch PERSISTS in optimization loop

### Code Path Divergence
- **Zero-point check** (use_mapping_zero_geometry=True): Bypasses U @ B_ideal reconstruction, uses MOSFLM A* directly → chi²=989k (healthy)
- **LBFGS optimization** (use_mapping_zero_geometry=False): Forces U @ B_ideal reconstruction → chi²=1.425B (catastrophic)

### Test Execution
- **Status:** TIMED OUT after 1200s (exit code 143)
- **Completed:** 2/10 optimizer steps (telemetry_step_000.json, telemetry_step_001.json)
- **Missing:** 8 steps + block_dof_results.json (final convergence summary)
- **Performance:** ~600s per LBFGS step on CPU (prohibitively slow; 10 steps would require ~100 minutes)

## Decision

**Path B: LBFGS Convergence FAILURE (BLOCKED)**

### Rationale
1. **Reproducibility:** Chi²=1.425B signature appeared in BOTH runs (2025-11-22T165000Z AND 2025-11-22T172000Z) with different telemetry configurations, ruling out data corruption
2. **Specificity:** The value is EXACTLY 1.425 billion in both runs, matching pre-bugfix Phase A signature — indicates SAME underlying B_ideal matrix (cctbx fractionalization_matrix)
3. **Code Path Divergence:** Zero-point check PASSED, LBFGS step 0 FAILED with same input data — confirms bugfix incomplete (works in one path, fails in another)
4. **Gradient Magnitude:** log_scale gradient of 295k consistent with catastrophic B_ideal mismatch (scale trying to compensate for 1000× error)

### Root Cause (High Confidence)
The `derive_u_matrix_from_mosflm_a_star` bugfix (826f4c9) correctly returns `(U_matrix, B_ideal_reciprocal)`, but somewhere in the LBFGS optimization loop, `components.B_ideal_reciprocal` is:
- Being overwritten/mutated with wrong value (cctbx fractionalization_matrix), OR
- Not being used (different code path computes B_ideal separately), OR
- Experiencing tensor aliasing/device mismatch causing reversion to wrong value

## Next Steps (Priority 1 - Mandatory Deep Diagnostic)

### Deliverables
1. **Instrument LBFGS closure** with B_ideal checksum/hash logging (entry and during A* reconstruction)
2. **Add device/dtype logging** for U_matrix and B_ideal_reciprocal tensors to catch mismatches
3. **Run 2-step LBFGS diagnostic variant** (reduced from 10 steps to save time ~20 minutes vs 100 minutes)
4. **Capture B_ideal lifecycle:** creation → components assignment → closure entry → A* reconstruction → identify EXACT divergence point
5. **Document root cause** in `phase_b1_diagnostic_results.md`
6. **Implement fix** (likely: ensure components.B_ideal_reciprocal is immutable clone OR fix code path that overwrites it)
7. **Rerun Test B1** after fix to validate chi² step 0 drops from 1.425B → ~1M

### Estimated Time
1-2 loops (diagnostic run + fix implementation)

### Exit Criteria
- B_ideal checksum in closure matches MOSFLM-derived value from `derive_u_matrix_from_mosflm_a_star`
- Chi² step 0 drops from 1.425B → ~1M (same as zero-point check)
- LBFGS convergence metrics show healthy behavior (chi² stable or improving, CC ≥ 0.99)

## Artifacts
- `phase_b1_review.md` — Prior attempt review (zero-point PASSED, step 000 catastrophic, telemetry path duplication diagnosis)
- `phase_b1_decision.md` — Test B1 decision with full metrics and Path B verdict
- `stage_a_lbfgs_rerun.log` — Full test log (foreground execution, 1200s timeout)
- `telemetry/telemetry_step_000.json` — First step catastrophic failure (chi²=1.425B)
- `telemetry/telemetry_step_001.json` — Second step (incomplete, test timed out)
- `zero_point_check.json` — Zero-point validation metrics (chi²=989k, PASSED)

## Ledger Updates
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Phase B checklist B1 marked [~] BLOCKED with Path B verdict
- `docs/fix_plan.md` — Attempts History entry 57 added with full diagnostic summary

## Protected Assets
No changes to production code (dbex/*.py) this loop — telemetry path issue was usage error, not code bug. Prior LBFGS infrastructure (commit 8440df8) remains intact.

## Regression Guard
Not rerun this loop (no production code changes). Prior run (commit 8440df8) PASSED in 13.16s.
