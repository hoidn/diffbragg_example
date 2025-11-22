# Do Now — TORCH-GEOMETRY-CONVERGENCE-001 Phase B5 Fix Implementation

## Summary
Audit and fix code path discrepancy between `_forward_once` (script-level, chi²=1.425B catastrophic) and `run_nanobrag_refinement` (production path, chi²=1.13M healthy) U-matrix reconstruction logic; validate fix with 1-step diagnostic rerun.

## Mode
none (implementation + validation)

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
- **Active:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, must collect >0 and pass)
- **Validation:** 1-step diagnostic run via `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only --adam-steps 1 --device cpu --out-dir <artifacts>/diagnostic_b5_postfix/` (expect chi²_init~1.13M, grad_log_scale O(1-100), not 295k)

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/`

## Do Now

**CRITICAL CODE PATH DISCREPANCY FIX — Ralph Execute This 10-Step Protocol**

Phase B4 (2025-11-22T201500Z) identified root cause H4a with HIGH confidence (~85%): script-level `_forward_once` produces chi²=1.425B (catastrophic) while `run_nanobrag_refinement` produces chi²=1.13M (healthy) at SAME parameters. This proves B_ideal fix (commit e86fd4e) works correctly in production path but is NOT applied in simplified script path. Your task: audit `_forward_once`, align U-matrix logic with `run_nanobrag_refinement`, validate fix.

### Step 1: Review Phase B4 Evidence (5 min)
Read the following artifacts to understand the code path discrepancy:
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/phase_b4_extended_diagnostic.md` (§Executive Summary, §Root Cause Determination)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/telemetry/telemetry_step_000_init.json` (script path: chi²=1.425B, grad_log_scale=294k)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/block_dof_results_u_matrix.json` (production path: chi²_before=1.13M)

**Key Insight:** Script _forward_once uses different/incomplete U-matrix reconstruction logic than run_nanobrag_refinement.

### Step 2: Locate Target Functions (Code Pointers)
Identify the two code paths to audit:
1. **Script-level path (BROKEN):** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` — function `_forward_once` (grep for `def _forward_once`)
2. **Production path (WORKING):** `dbex/nanobrag_refinement.py` — function `compute_loss` in `build_stage_a_lbfgs_closure`, specifically the U-matrix branch around lines 971-1007 (commit e86fd4e fix location)

### Step 3: Audit U-Matrix Reconstruction Logic (Side-by-Side Comparison)
For EACH of the following elements, compare script _forward_once vs production compute_loss:

**A. B_ideal Derivation Source**
- **Production path (CORRECT per commit e86fd4e):** Uses `derive_u_matrix_from_mosflm_a_star` return value (U_matrix, B_ideal_reciprocal) from MOSFLM A*, stores in `components.B_ideal_reciprocal`.
- **Script path (CHECK):** Does `_forward_once` call `derive_u_matrix_from_mosflm_a_star`? If YES, does it CAPTURE and USE the returned B_ideal_reciprocal? If NO, does it recompute B_ideal from cctbx cell parameters (WRONG, causes mismatch)?
- **Expected Bug:** Script likely recomputes B_ideal via `TorchCrystal.compute_cell_tensors()` or `cctbx cell.fractionalization_matrix()` instead of using MOSFLM-derived B_ideal.

**B. Quaternion Normalization**
- **Production path:** Normalizes quaternion `q = q / torch.norm(q)` before `quaternion_to_matrix(q)` conversion (see nanobrag_refinement.py U-matrix branch).
- **Script path (CHECK):** Does `_forward_once` normalize quaternion before converting to U-matrix? If NO, unit-norm constraint violated → wrong U-matrix → wrong A* → catastrophic chi².

**C. A* Reconstruction Formula**
- **Production path:** Reconstructs `A* = U @ B_ideal_reciprocal` using consistent U (from quaternion) and B_ideal (from MOSFLM).
- **Script path (CHECK):** Does `_forward_once` use `A* = U @ B_ideal`? If it uses different B_ideal source, reconstruction is wrong.

**D. Detector/Crystal/Simulator Instantiation**
- **Production path:** Uses pre-built StageAContext components (detector, crystal, simulator) with consistent geometry.
- **Script path (CHECK):** Does `_forward_once` rebuild detector/crystal/simulator on-the-fly? If YES, check if it uses SAME U-matrix and B_ideal values as initialization.

**Audit Output:** Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/code_path_audit.md` documenting findings for A-D with file:line references for each discrepancy.

### Step 4: Implement Fix (Choose ONE Option Based on Audit)

**Option 1 (Quick Patch): Align _forward_once Logic**
If audit reveals specific bugs in _forward_once (e.g., wrong B_ideal source, missing quaternion normalization):
- Patch `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py::_forward_once` to match production logic:
  - Use MOSFLM-derived B_ideal from `derive_u_matrix_from_mosflm_a_star` return value
  - Normalize quaternion before `quaternion_to_matrix(q)`
  - Ensure `A* = U @ B_ideal` uses consistent tensors
- Document changes in `code_path_audit.md` §Fix Implementation.

**Option 2 (Robust Refactor): Call run_nanobrag_refinement Directly**
If _forward_once reimplements too much logic (detector/crystal/simulator rebuilds):
- Refactor script to call `dbex.nanobrag_refinement.run_nanobrag_refinement` directly for forward passes instead of _forward_once.
- Pass pre-built StageAContext components (detector, crystal, simulator) to closure.
- This ensures production path is used for ALL forward model evaluations (script + telemetry + optimization).
- **Caveat:** May require larger refactor; prefer Option 1 if quick patch is sufficient.

**Decision Criteria:**
- If audit finds 1-2 isolated bugs (B_ideal source, normalization): Choose Option 1.
- If audit finds >3 discrepancies or deep architectural differences: Choose Option 2 (escalate to Galph if refactor scope exceeds 1 loop).

### Step 5: Regression Guard (MANDATORY Before Validation)
Run regression test to ensure fix doesn't break default cell+misset path:
```bash
cd /home/ollie/Documents/diffbragg_example
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v --tb=short --durations=5 > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/pytest_regression_postfix.log 2>&1
```
**Expected:** PASSED (typically 12-14s). If FAILED, do NOT proceed to Step 6; fix regression first.

### Step 6: Validation Diagnostic (1-Step Rerun)
Execute 1-step diagnostic with fixed code path to validate chi² initialization:
```bash
cd /home/ollie/Documents/diffbragg_example
timeout 1800 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only \
  --adam-steps 1 \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/diagnostic_b5_postfix/ \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/diagnostic_b5_postfix.log 2>&1
echo "Exit code: $?"
```
**Timeout:** 1800s (30 min) to allow HKL grid builds + 1 optimizer step.

### Step 7: Extract Validation Metrics
Capture the following from artifacts directory `diagnostic_b5_postfix/`:
1. **Zero-Point Check:** `zero_point_check.json` — chi²_mapping, chi²_stage_a, correlation (expect ~989k, ~989k, ~1.0)
2. **Init Telemetry:** `telemetry/telemetry_step_000_init.json` — chi_squared, grad_log_scale (expect ~1.13M, O(1-100) NOT 295k)
3. **Convergence Metrics:** `block_dof_results_u_matrix.json` — chi²_before, chi²_after, CC_before, CC_after (expect chi²_before~1.13M healthy)
4. **Log Tail:** Last 20 lines of `diagnostic_b5_postfix.log` (check for errors/warnings)

Save summary to `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/validation_metrics.txt`:
```
Zero-Point: chi²_mapping=<value>, chi²_stage_a=<value>, corr=<value>
Init Telemetry: chi²=<value>, grad_log_scale=<value>
Convergence: chi²_before=<value>, chi²_after=<value>, CC_before=<value>, CC_after=<value>
Log Tail: [paste last 5 lines OR error message if failed]
```

### Step 8: Synthesize Decision (3-Path Template)
Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/phase_b5_fix_decision.md` with the following structure:

---
**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** B5 (Fix Implementation)
**Date:** 2025-11-22T183012Z
**Status:** [Choose ONE: Path A SUCCESS | Path B PARTIAL | Path C FAILURE]

### Decision Criteria
| Metric | Expected (SUCCESS) | Observed | Pass/Fail |
|--------|-------------------|----------|-----------|
| chi²_init (telemetry) | ~1.13M (within 2× of zero-point) | <fill> | <fill> |
| grad_log_scale_init | O(1-100), NOT ~295k | <fill> | <fill> |
| chi²_before (convergence) | ~1.13M | <fill> | <fill> |
| Zero-point correlation | ≥0.99 | <fill> | <fill> |

### Verdict

**Path A: FIX SUCCESS** ✅
- **Criteria:** chi²_init < 2M AND grad_log_scale < 1000 AND zero-point correlation ≥ 0.99
- **Evidence:** [cite validation_metrics.txt values]
- **Next Actions:** Mark B5 DONE in implementation.md; proceed to Phase C full convergence validation (10-step A_scale_only + D_full tests, findings update, close CONVERGENCE-001).

**Path B: FIX PARTIAL** ⚠️
- **Criteria:** chi²_init improved (2M-10M) but still elevated, OR gradient reduced but still high (1k-10k)
- **Evidence:** [cite validation_metrics.txt values]
- **Root Cause:** Fix addressed PART of discrepancy but not all (e.g., fixed B_ideal but missed normalization).
- **Next Actions:** Re-audit code paths (Step 3 deeper dive), apply additional fixes, rerun Step 6.

**Path C: FIX FAILURE** ❌
- **Criteria:** chi²_init > 10M OR grad_log_scale > 10k OR test timed out OR regression guard failed
- **Evidence:** [cite validation_metrics.txt or error logs]
- **Root Cause:** Fix did not address root cause, OR introduced new bug, OR refactor scope too large.
- **Next Actions:** Revert changes, escalate to Galph with audit findings and error logs; recommend Option 2 (full refactor) or alternative investigation.

[Fill in the verdict that matches your observed metrics]
---

### Step 9: Update Implementation Checklist
Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:
- Line 141: Replace current B4 entry text with:
  ```
  - [x] B4: **Extended Diagnostic (U_matrix/A*/Gradient Lifecycle Tracing)** — COMPLETED (2025-11-22T201500Z). Identified H4a (Code Path Discrepancy) with HIGH confidence ~85%. Script _forward_once produces chi²=1.425B (catastrophic) while run_nanobrag_refinement produces chi²=1.13M (healthy) at SAME parameters. See `phase_b4_extended_diagnostic.md`.
  ```
- After line 141, insert NEW line for B5:
  ```
  - [x|~|☐] B5: **Fix Code Path Discrepancy** — [DONE|BLOCKED|PENDING] (2025-11-22T183012Z). [Choose based on Path A/B/C]: [Path A: Patched _forward_once U-matrix logic (B_ideal source, quaternion normalization); chi²_init=<value> (healthy). See `phase_b5_fix_decision.md`.] [Path B: Partial fix applied; chi²_init improved to <value> but still elevated. See `phase_b5_fix_decision.md`.] [Path C: Fix FAILED; chi²_init=<value> or test error. See `phase_b5_fix_decision.md`.]
  ```

### Step 10: Write Summary and Commit
Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/summary.md`:
```markdown
### Turn Summary
[Choose based on Path A/B/C]:

**Path A (SUCCESS):**
Implemented Phase B5 fix for code path discrepancy: audited _forward_once U-matrix reconstruction, identified [list bugs: e.g., "wrong B_ideal source (cctbx recompute), missing quaternion normalization"], patched with MOSFLM-derived B_ideal and q normalization.
Validation test confirms fix works: chi²_init=<value> (healthy, down from 1.425B), grad_log_scale=<value> (normal, down from 295k), zero-point parity maintained.
Next: Phase C full convergence validation (10-step A_scale_only + D_full, findings update CONVERGENCE-002, close CONVERGENCE-001).
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/ (code_path_audit.md, phase_b5_fix_decision.md, validation_metrics.txt)

**Path B (PARTIAL):**
Implemented Phase B5 partial fix for code path discrepancy: patched [list changes], but chi²_init=<value> still elevated (improved from 1.425B but not fully healthy).
Additional discrepancies remain; re-audit required.
Next: Deeper code path audit (Step 3 extended), apply additional fixes, rerun validation.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/ (code_path_audit.md, phase_b5_fix_decision.md, validation_metrics.txt)

**Path C (FAILURE):**
Attempted Phase B5 fix for code path discrepancy but validation FAILED: chi²_init=<value> (still catastrophic) OR test error [cite error].
Fix did not address root cause; [escalate to Galph with audit findings | recommend Option 2 full refactor].
Next: Galph review audit findings, decide between deeper investigation vs alternative parameterization.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/ (code_path_audit.md, phase_b5_fix_decision.md, error logs)
```

Commit all changes:
```bash
cd /home/ollie/Documents/diffbragg_example
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B5: Fix _forward_once U-matrix code path discrepancy — [Path A SUCCESS | Path B PARTIAL | Path C FAILURE] (tests: test_stage_a_expansion)"
git push
```

## How-To Map

### Environment Setup
```bash
cd /home/ollie/Documents/diffbragg_example
# No environment changes — frozen per policy
```

### Step-by-Step Commands

**Step 1-3: Review + Audit (no commands, code inspection)**
```bash
# Read artifacts from Phase B4
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/phase_b4_extended_diagnostic.md
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/telemetry/telemetry_step_000_init.json
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/block_dof_results_u_matrix.json

# Locate functions
grep -n "def _forward_once" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
grep -n "def compute_loss" dbex/nanobrag_refinement.py | head -1
grep -n "derive_u_matrix_from_mosflm_a_star" dbex/nanobrag_refinement.py dbex/nanobrag_bridge.py

# Audit (manual code inspection, side-by-side comparison)
# Output: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/code_path_audit.md
```

**Step 4: Fix Implementation (example for Option 1 quick patch)**
```bash
# Edit plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
# - Find _forward_once function
# - Patch B_ideal derivation to use MOSFLM source (match commit e86fd4e logic)
# - Add quaternion normalization: q = q / torch.norm(q)
# - Ensure A* = U @ B_ideal uses consistent tensors
# Document changes in code_path_audit.md §Fix Implementation
```

**Step 5: Regression Guard**
```bash
cd /home/ollie/Documents/diffbragg_example
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v --tb=short --durations=5 > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/pytest_regression_postfix.log 2>&1
echo "Exit code: $?"
# Expected: PASSED (exit 0), ~12-14s
```

**Step 6: Validation Diagnostic**
```bash
cd /home/ollie/Documents/diffbragg_example
timeout 1800 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only \
  --adam-steps 1 \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/diagnostic_b5_postfix/ \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/diagnostic_b5_postfix.log 2>&1
echo "Exit code: $?"
```

**Step 7: Extract Metrics**
```bash
cd plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/diagnostic_b5_postfix/
# Inspect artifacts
cat zero_point_check.json
cat telemetry/telemetry_step_000_init.json
cat block_dof_results_u_matrix.json
tail -20 ../diagnostic_b5_postfix.log

# Create summary
cat > ../validation_metrics.txt <<'EOF'
Zero-Point: chi²_mapping=<value>, chi²_stage_a=<value>, corr=<value>
Init Telemetry: chi²=<value>, grad_log_scale=<value>
Convergence: chi²_before=<value>, chi²_after=<value>, CC_before=<value>, CC_after=<value>
Log Tail: [paste last 5 lines OR error message]
EOF
```

**Step 8-9: Decision + Checklist (manual editing)**
```bash
# Create phase_b5_fix_decision.md with 3-path template (see Step 8)
# Edit implementation.md Phase B checklist (see Step 9)
```

**Step 10: Summary + Commit**
```bash
cd /home/ollie/Documents/diffbragg_example
# Create summary.md (see Step 10)
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B5: Fix _forward_once U-matrix code path discrepancy — [Path A SUCCESS | Path B PARTIAL | Path C FAILURE] (tests: test_stage_a_expansion)"
git push
```

## Pitfalls to Avoid

### Code Alignment Pitfalls
1. **DO NOT** recompute B_ideal from cctbx cell parameters in _forward_once; use MOSFLM-derived B_ideal from `derive_u_matrix_from_mosflm_a_star` return value (matches commit e86fd4e).
2. **DO NOT** skip quaternion normalization `q = q / torch.norm(q)` before `quaternion_to_matrix(q)` conversion; unit-norm constraint is mandatory for proper rotation.
3. **DO NOT** mix TorchCrystal B_ideal with cctbx B_ideal; use ONE consistent source (MOSFLM-derived) across all code paths.
4. **DO NOT** assume script _forward_once is obsolete without auditing first; it may be intentionally simplified for telemetry overhead reduction (just ensure correctness).

### Validation Pitfalls
5. **DO NOT** skip regression guard (Step 5); cell+misset default path MUST remain unaffected (test_stage_a_expansion PASSED).
6. **DO NOT** accept chi²_init=1.425B as "improved" in Path B; threshold for PARTIAL is 2M-10M (significantly better than catastrophic but not yet healthy).
7. **DO NOT** proceed to Phase C if Path B or Path C; re-audit and fix first OR escalate to Galph.
8. **DO NOT** emit telemetry to non-existent directories; ensure `diagnostic_b5_postfix/telemetry/` is created by script OR auto-constructed.

### Scope Pitfalls
9. **DO NOT** refactor beyond _forward_once without Galph approval; if audit reveals >3 discrepancies, escalate with recommendation for Option 2 (full refactor).
10. **DO NOT** add new features (e.g., lifecycle logging to _forward_once) in this loop; focus on fixing existing logic to match production path.

### Documentation Pitfalls
11. **DO** document EVERY discrepancy found in audit with file:line references (code_path_audit.md).
12. **DO** fill in validation_metrics.txt with ACTUAL values from artifacts, not placeholders.
13. **DO** choose exactly ONE path (A/B/C) in phase_b5_fix_decision.md; do not hedge with "unclear" or "inconclusive" (use thresholds in Step 8 criteria).

### Environment
- **Environment Frozen:** Do NOT install/upgrade packages. If imports fail, record error signature and mark blocked.
- **Timeout Safety:** 1-step diagnostic should complete in ~10-15 min (HKL grids + 1 step); 1800s timeout is generous. If timeout, log tail shows where test stuck (likely HKL build or simulator warmup).

### Protected Assets
- **NO EDITS:** `dbex/nanobrag_refinement.py` is WORKING production path (commit e86fd4e fix applied). DO NOT modify unless escalated by Galph.
- **EDITABLE:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py::_forward_once` is script-level BROKEN path; patch freely to align with production logic.

## If Blocked

### Scenario 1: Regression Guard Fails (test_stage_a_expansion)
**Action:** Do NOT proceed to Step 6. Fix the regression:
1. Check if _forward_once is called by default cell+misset path (should NOT be; it's U-matrix-only).
2. If regression in U-matrix path: revert _forward_once changes, re-audit discrepancies.
3. Log error in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/regression_blocker.md` with pytest output.
4. Update Attempts History: "B5 BLOCKED — Regression guard failed after _forward_once patch; error: [cite]".

### Scenario 2: Validation Test Times Out (Step 6 exit code 143)
**Action:** Check log tail for stuck operation:
1. If stuck during HKL grid builds: Not a fix issue; CPU too slow. Reduce --adam-steps to 0 (zero-point check only) and re-validate chi²_init from telemetry.
2. If stuck during simulator warmup: Same as above; zero-point check is sufficient to validate initialization fix.
3. Document in phase_b5_fix_decision.md: "Test timed out during [HKL/simulator]; validated chi²_init from zero-point check instead."

### Scenario 3: Audit Reveals >3 Discrepancies (Step 3)
**Action:** Escalate to Galph instead of attempting quick patch:
1. Finish code_path_audit.md documenting ALL discrepancies (A-D plus any additional findings).
2. Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/escalation_recommendation.md`:
   - List all discrepancies with file:line references.
   - Recommend Option 2 (full refactor: deprecate _forward_once, call run_nanobrag_refinement directly).
   - Estimate refactor scope (e.g., "2-3 loops to refactor script architecture").
3. Update Attempts History: "B5 ESCALATED — Audit found >3 discrepancies; recommend Option 2 full refactor".
4. Do NOT attempt patch; let Galph decide.

### Scenario 4: Path C (Fix Failure) After Step 8
**Action:**
1. Revert _forward_once changes: `git checkout HEAD -- plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
2. Document in phase_b5_fix_decision.md §Path C with error evidence.
3. Update Attempts History: "B5 FAILED — Fix did not resolve chi² catastrophic failure; chi²_init=<value>; escalate to Galph".
4. Mark B5 as [~] BLOCKED in implementation.md checklist.
5. Commit with message: "TORCH-GEOMETRY-CONVERGENCE-001 Phase B5: FAILED fix attempt (reverted) — escalate to Galph (tests: test_stage_a_expansion)"

## Findings Applied

**Mandatory Findings Integration (from docs/findings.md):**

1. **REFINE-001 (LBFGS Scale Warm-Start, NaN/Inf Guards):**
   - Relevance: Gradient validation in Step 7 must check for NaN/Inf flags in telemetry.
   - Application: If grad_log_scale is NaN/Inf (not just high magnitude), note in phase_b5_fix_decision.md as secondary pathology.

2. **PHYSICS-LOSS-002 (Variance-Weighted Chi-Squared Sigma-Floor Guard):**
   - Relevance: Variance-weighted loss is unchanged by this fix; sigma-floor guard should remain effective.
   - Application: No action required; variance formula is implementation-agnostic.

3. **GRADIENT-001 (Autograd Graph Preservation, Crystal Overrides):**
   - Relevance: If _forward_once rebuilds crystal on-the-fly, ensure it uses `torch.no_grad()` context for non-trainable parameters.
   - Application: Audit Step 3D (detector/crystal instantiation) should check for autograd context mismatches.

4. **Escalation Source — TORCH-GEOMETRY-PARITY-003 (Quaternion U-Matrix Parity Perfect, Convergence Failed):**
   - Context: PARITY-003 Phase C2 validated parity <1e-17 but convergence catastrophically failed. Phase B4 identified code path discrepancy as root cause (H4a).
   - Application: This fix (B5) resolves PARITY-003's convergence blocker if Path A SUCCESS achieved. If Path C, may need to revisit parity validation method (does script _forward_once match parity test code path?).

**No Relevant Findings:** No additional findings from knowledge base apply to code path alignment. If NEW findings emerge (e.g., "GEOMETRY-005: Script telemetry must use production path"), document in docs/findings.md after Phase C validation.

## Pointers

### Spec References
- `docs/spec-db-workflow.md` §Stage A — Optimizer convergence criteria (CC ≥ 0.99, stable/improving χ²)
- `docs/spec-db-runtime.md` §Gradient stability — NaN/Inf checks, gradient magnitude thresholds
- `docs/spec-db-core.md` §Variance Model — Variance-weighted chi-squared formula (unchanged by this fix)

### Architecture References
- `docs/architecture.md` §Data Flow — U-matrix reconstruction flow from MOSFLM A* to simulator config
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Phase B checklist, hypothesis verdicts

### Testing References
- `docs/TESTING_GUIDE.md` §2 (Smoke Tests) — test_stage_a_expansion regression guard
- `docs/development/TEST_SUITE_INDEX.md` — Selector status (test_stage_a_expansion: Active)
- `docs/development/testing_strategy.md` — Validation strategy for U-matrix parameterization

### Key Code Locations
- `dbex/nanobrag_refinement.py:971-1007` — U-matrix branch in `compute_loss` (WORKING production path, commit e86fd4e)
- `dbex/nanobrag_bridge.py:794` — `derive_u_matrix_from_mosflm_a_star` signature (returns Tuple[U, B_ideal])
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` — `_forward_once` function (BROKEN script path, target for audit/fix)

### Fix-Plan References
- `docs/fix_plan.md` — Row [TORCH-GEOMETRY-CONVERGENCE-001] Attempts History (latest: 2025-11-22T201500Z Phase B4 diagnostic)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/` — Phase B4 artifacts (phase_b4_extended_diagnostic.md, telemetry, decision)

## Next Up (Optional, If Step 10 Completes with Path A SUCCESS AND Time Remains)

**DO NOT** start Phase C in this loop. Phase C requires multi-step convergence validation (10-step A_scale_only + D_full tests, findings update) which is scope for next loop. If you finish Step 10 early with Path A SUCCESS:

1. **Verify Commit Pushed Successfully:**
   ```bash
   git log -1 --oneline
   git status
   # Ensure clean working tree, latest commit is Phase B5
   ```

2. **Optional: Collect 10-Step Telemetry Preview (Background, Non-Blocking):**
   If time permits (>15 min remaining), you MAY launch a 10-step diagnostic in BACKGROUND for Galph to review:
   ```bash
   cd /home/ollie/Documents/diffbragg_example
   timeout 3600 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --use-u-matrix \
     --phases 5 \
     --dof-variants A_scale_only \
     --adam-steps 10 \
     --device cpu \
     --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/preview_10step/ \
     > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/preview_10step.log 2>&1 &
   echo "Background PID: $!"
   ```
   **Note in summary.md:** "Launched optional 10-step preview in background (PID <pid>) for Galph; DO NOT wait for completion."

3. **Update galph_memory.md (Galph's Responsibility, NOT Ralph's):**
   Do NOT edit galph_memory.md. Galph will append entry after reviewing your artifacts.

## Doc Sync Plan (Conditional)

**NOT APPLICABLE** for this loop. No tests added/renamed; only code fix + validation. Test registry (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) remains accurate with existing selector `test_stage_a_expansion`.

---

**END OF DO NOW — Ralph, Execute Steps 1-10 in Sequence. Report Results in summary.md with Path A/B/C Verdict.**
