# Phase B3 Forward Model Sanity Check — Parameter Update Propagation Diagnostic

## Summary
Execute lightweight 1-step LBFGS diagnostic to capture U_matrix/A*/gradient checksums and validate parameter update propagation, confirming/refuting H4 (Forward Model Bug) hypothesis.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/

## Do Now

Execute Phase B3 forward model sanity checks per phase_b2_diagnostic_decision.md §Path H4 recommendations. Goal: Determine if parameter updates (log_scale, q_params) propagate correctly to forward model (U_matrix, A*, I_model) or if staleness/detachment causes catastrophic chi².

### Implementation Tasks

**1. Review Phase B2 Instrumentation**
- Read `dbex/nanobrag_refinement.py` lines 960-1100 (U-matrix closure branch) to confirm Phase B2 telemetry (commit 3338df1) captures:
  - U_matrix checksum (`U.sum().item()`)
  - Enhanced gradient stats (element-wise min/max/mean/std, sign consistency)
  - V_denom histograms
  - Weighted residuals stats
- Verify telemetry is conditionally emitted only when `config.telemetry_output_dir` is set (no overhead by default)

**2. Execute Lightweight 1-Step Diagnostic**
- Run reduced diagnostic variant (1 LBFGS step instead of 2) to minimize timeout risk:
  ```bash
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 \
  python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
    --use-u-matrix \
    --phases 5 \
    --dof-variants A_scale_only \
    --use-lbfgs \
    --optimizer-steps 1 \
    --telemetry-dir telemetry \
    --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/diagnostic_1step \
    --device cpu \
    2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/diagnostic_1step.log
  ```
- Timeout: 1200s (20 minutes, same as prior runs)
- Expected outputs:
  - `diagnostic_1step/telemetry/telemetry_step_000.json` (initialization, before optimizer.step())
  - `diagnostic_1step/telemetry/telemetry_step_001.json` (after 1 LBFGS step with line search)
  - `diagnostic_1step/zero_point_check.json` (B_ideal fix validation)
  - `diagnostic_1step/block_dof_results_u_matrix.json` (chi² before/after, CC metrics)

**3. Extract Forward Model Sanity Check Metrics**

From `telemetry_step_000.json` and `telemetry_step_001.json`, extract and compare:

**A. U-matrix Checksum:**
- Step 000: `U_matrix_checksum` (should be non-zero, e.g., ~5-15 range for typical orientation matrix)
- Step 001: `U_matrix_checksum` (MUST differ from step 000 if q_params updated OR should be identical if A_scale_only with train_orientation=False)
- **Sanity Check:** If A_scale_only (train_orientation=False), U_matrix_checksum SHOULD be CONSTANT (q_params frozen). If U changes, bug detected.

**B. Log-Scale Update:**
- Step 000: `parameters.log_scale` (initial value, typically ~-0.2 to 0.0)
- Step 001: `parameters.log_scale` (should differ by small delta, e.g., ±0.01 to ±0.1 depending on gradient magnitude)
- **Sanity Check:** If log_scale UNCHANGED after LBFGS step → optimizer not updating parameters (bug). If changed but clamped to ±10.0 boundary → clamp may be interfering.

**C. Gradient Magnitude (Post-Fix):**
- Step 000: `gradients.log_scale.norm`
- Step 001: `gradients.log_scale.norm`
- **Compare to Pre-Fix (Phase A1 telemetry):** ~295k gradient at step 000
- **H3b Test:** If post-fix gradient is ALSO ~295k → H3b (gradient explosion) is PRIMARY, not symptom of H4
- **H3b Test:** If post-fix gradient is O(1-100) → H3b was symptom of B_ideal mismatch (now fixed), H4 is separate issue

**D. Chi-Squared Trajectory:**
- Step 000: `loss.chi_squared` (should be ~1.13M per Phase B1 validation, post-fix initialization)
- Step 001: `loss.chi_squared` (CRITICAL: if ~1.425B catastrophic OR if ~1.13M unchanged OR if improved <1.13M)
- **H4 Verdict:**
  - If chi² step_001 ~1.425B → **H4 CONFIRMED** (forward model bug triggered by parameter update)
  - If chi² step_001 ~1.13M (unchanged) → Forward model may be stale (parameters didn't propagate OR LBFGS rejected update)
  - If chi² step_001 <1.13M (improved) → **H4 RULED OUT** (forward model is working, likely variance or optimizer issue)

**E. Variance Components (If Captured):**
- Step 000 vs Step 001: `variance.V_denom_min`, `variance.V_denom_median`, `variance.V_denom_max`
- **H2 Test:** If V_denom_min→0 OR V_denom_max explodes >1e9 → variance instability (H2)
- **H2 Test:** If clamp_fraction→1.0 → variance floor dominates (symptom of I_model collapse, likely H4)

**4. Synthesize Phase B3 Diagnostic Decision**

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/phase_b3_forward_model_sanity_check.md` with:

**A. Metrics Summary Table:**
| Metric | Step 000 | Step 001 | Delta | Verdict |
|--------|----------|----------|-------|---------|
| U_matrix_checksum | X.XX | X.XX | ±Y.YY | CONSTANT (expected for A_scale_only) OR CHANGED (bug if A_scale_only) |
| log_scale | -0.XXX | -0.YYY | ±0.ZZZ | UPDATED (healthy) OR UNCHANGED (optimizer stalled) OR CLAMPED (at ±10.0 boundary) |
| grad_log_scale.norm | XXXK | XXXK | ±YYK | LARGE ~295k (H3b primary) OR SMALL O(1-100) (H3b was symptom) |
| chi_squared | 1.13M | Z.ZZM/B | +ΔΔΔΔ% | CATASTROPHIC ~1.425B (H4 confirmed) OR UNCHANGED (stale) OR IMPROVED (H4 ruled out) |
| V_denom_min | X.XX | Y.YY | ±Z.ZZ | HEALTHY ≥sigma_floor² OR →0 (H2 variance bug) |
| V_denom_max | X.XXK | Y.YYK | ±Z.ZZK | HEALTHY O(1e3-1e6) OR EXPLODES O(1e9+) (H2) |

**B. Hypothesis Verdict Update:**
- H4 (Forward Model Bug): [CONFIRMED | RULED OUT | INCONCLUSIVE] — confidence [HIGH | MEDIUM | LOW]
  - Evidence: [chi² catastrophic at step 001 | log_scale updated but chi² exploded | U_matrix stale | etc.]
- H3b (Gradient Explosion): [PRIMARY | SYMPTOM | RULED OUT] — confidence [HIGH | MEDIUM | LOW]
  - Evidence: [grad_log_scale ~295k post-fix | grad_log_scale O(100) post-fix]
- H2 (Variance Instability): [PLAUSIBLE | RULED OUT] — confidence [MEDIUM | LOW]
  - Evidence: [V_denom pathology observed | V_denom healthy]

**C. Root Cause Determination:**
- **Primary Hypothesis:** [H4 | H3b | H2] with [HIGH | MEDIUM | LOW] confidence
- **Rationale:** [Explain key evidence supporting primary hypothesis]
- **Candidate Bug (if H4 confirmed):** [U-matrix staleness | log_scale clamp interference | crystal_overrides aliasing | detach placement]

**D. Recommended Next Actions:**
- **If H4 CONFIRMED with candidate bug identified:** Proceed to Phase C1 (implement targeted fix per candidate)
- **If H4 CONFIRMED but candidate unclear:** Add A* checksum logging (extend telemetry, rerun 1-step diagnostic)
- **If H3b PRIMARY:** Proceed to Phase C1 (implement gradient clipping or LR reduction)
- **If H2 PRIMARY:** Proceed to variance analysis (increase sigma_floor, add loss clamping, investigate I_model collapse)
- **If INCONCLUSIVE:** Extend diagnostic to 2 steps OR accept MEDIUM-HIGH confidence H4 verdict from Phase B2 and proceed to fix attempt

**5. Regression Guard**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  -xvs 2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/pytest_regression.log
```
- Expected: PASSED (cell+misset default path unaffected by Phase B2 telemetry instrumentation)
- If FAILED: Revert Phase B2 changes, investigate regression

**6. Update Implementation Plan Checklist**

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:
- Mark B3 as [x] DONE with brief note: "1-step diagnostic executed, forward model sanity check complete, H4 verdict: [CONFIRMED|RULED OUT|INCONCLUSIVE]"
- If H4 CONFIRMED: Update "Recommended Next Actions" to point to specific Phase C1 fix (e.g., "Fix U-matrix staleness bug")
- If H4 RULED OUT: Update to pivot to H3b (gradient clipping) or H2 (variance analysis)

**7. Write Loop Summary**

Emit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/summary.md` with:
- Execution outcome (diagnostic completed OR timed out again)
- Key metrics (U_matrix checksum delta, log_scale delta, chi² step_001, gradient magnitude post-fix)
- H4 verdict (CONFIRMED/RULED OUT/INCONCLUSIVE) with confidence level
- Recommended next phase (C1 fix implementation OR deeper diagnostic OR pivot to H3b/H2)

**8. Commit Changes**
```bash
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B3: Forward model sanity check - [H4 verdict] (tests: test_stage_a_expansion)"
git push
```

## How-To Map

**Environment:**
```bash
export KMP_DUPLICATE_LIB_OK=TRUE  # Suppress duplicate libiomp5 warnings
export NANOBRAGG_DISABLE_COMPILE=1  # Disable torch.compile for CPU diagnostics
# No other env vars needed (CPU execution, no CUDA)
```

**Execute 1-Step Diagnostic:**
```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/diagnostic_1step

timeout 1200 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only \
  --use-lbfgs \
  --optimizer-steps 1 \
  --telemetry-dir telemetry \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/diagnostic_1step \
  --device cpu \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/diagnostic_1step.log
```

**Extract Metrics (Python one-liner for quick checks):**
```python
import json
from pathlib import Path

base = Path("plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/diagnostic_1step/telemetry")
t0 = json.load(open(base / "telemetry_step_000.json"))
t1 = json.load(open(base / "telemetry_step_001.json"))

print(f"U_matrix checksum: step 000={t0.get('U_matrix_checksum', 'N/A')} step 001={t1.get('U_matrix_checksum', 'N/A')}")
print(f"log_scale: step 000={t0['parameters']['log_scale']:.6f} step 001={t1['parameters']['log_scale']:.6f} delta={t1['parameters']['log_scale']-t0['parameters']['log_scale']:.6f}")
print(f"chi²: step 000={t0['loss']['chi_squared']:.2e} step 001={t1['loss']['chi_squared']:.2e} ratio={t1['loss']['chi_squared']/t0['loss']['chi_squared']:.2f}")
print(f"grad_log_scale norm: step 000={t0['gradients']['log_scale']['norm']:.2e} step 001={t1['gradients']['log_scale']['norm']:.2e}")
```

**Regression Guard:**
```bash
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -xvs
```

## Pitfalls To Avoid

**1. Timeout Management:**
- Use `timeout 1200` prefix for diagnostic command
- If timeout hits again, do NOT rerun with longer timeout; synthesize decision from Phase B1+B2 evidence (MEDIUM-HIGH confidence H4 is sufficient to proceed to fix attempt)

**2. Telemetry Path:**
- Use relative path `--telemetry-dir telemetry` (script prepends out_root automatically per bugfix in 2025-11-22T172000Z)
- Do NOT pass absolute path (causes double-prepending)

**3. A_scale_only Interpretation:**
- train_orientation=False → q_params.grad is None → U_matrix should NOT change between steps
- If U_matrix checksum DIFFERS between steps, this is a BUG (quaternion updated despite being frozen)
- log_scale IS trainable → should update every step (unless LBFGS line search rejects update)

**4. Chi² Catastrophic Threshold:**
- Step 001 chi² ~1.425B is catastrophic (1000× worse than initialization ~1.13M)
- Step 001 chi² ~1.13M (±10%) is "unchanged" (optimizer stalled OR forward model ignoring updates)
- Step 001 chi² <1.0M is improvement (H4 likely ruled out, forward model working)

**5. Gradient Magnitude Context:**
- Pre-fix gradient ~295k was measured at step 000 (catastrophic initialization with B_ideal bug)
- Post-fix gradient at step 000 is KEY: if still ~295k → H3b is primary; if O(1-100) → H3b was symptom
- Do NOT compare step 001 gradient to pre-fix step 000 gradient (different parameter values, different forward model state)

**6. Variance Telemetry May Be Incomplete:**
- Phase B2 instrumentation (commit 3338df1) added V_denom histograms, but if timeout occurred during closure construction, step 001 telemetry may be missing variance section
- If variance section is null/missing: H2 hypothesis NOT TESTABLE this loop; defer to next diagnostic OR accept H4 verdict without variance evidence

**7. Protected Assets (No Changes to Production Logic):**
- Phase B2 telemetry is OBSERVATION ONLY (conditional JSON emission)
- Do NOT modify optimizer.step() logic, loss computation, or forward model during this diagnostic
- If extending telemetry (A* checksum), add ONLY logging, no behavioral changes

**8. Device/Dtype Neutrality:**
- Diagnostic runs on CPU (--device cpu), so all tensors are CPU tensors
- When logging checksums (.sum().item()), ensure tensors are NOT detached prematurely (breaks autograd graph for gradient checks)

**9. LBFGS Line Search Behavior:**
- LBFGS may call closure MULTIPLE TIMES per optimizer.step() (each line search evaluation)
- Telemetry emits JSON only AFTER optimizer.step() completes (not per closure call)
- If step 001 chi² is UNCHANGED from step 000, LBFGS may have rejected ALL candidate updates (strong Wolfe conditions not satisfied)

**10. No New Scripts:**
- Use existing `stage_a_mapping_adam_debug.py` with CLI flags
- Metrics extraction via Python one-liner is T0 (micro probe, inline only) per scriptization policy
- Analysis document (phase_b3_forward_model_sanity_check.md) contains analysis text only

## If Blocked

**Blocker 1: Diagnostic Times Out Again (exit code 143 after 1200s)**
- Cause: HKL grid building is prohibitively slow on CPU for this experiment
- Immediate Action:
  1. Check if telemetry_step_000.json was captured (initialization before timeout)
  2. If step 000 exists: Analyze initialization state (U_matrix, log_scale, chi², gradients) and synthesize PARTIAL decision
  3. If step 000 missing: Timeout occurred before first closure call → telemetry overhead is NOT the issue, HKL grid is blocker
- Fallback:
  - Option A: Analyze existing zero_point_check.json from diagnostic_1step/ directory
  - Option B: Accept that 1-step diagnostic is infeasible on CPU; synthesize decision from Phase B1 validation + Phase A1 telemetry (already sufficient for H4 MEDIUM-HIGH confidence)
- Document in `phase_b3_diagnostic_blocker.md` with timeout analysis
- Update implementation.md: mark B3 as [~] BLOCKED with rationale
- Next loop: Proceed to Phase C1 fix implementation based on H4 hypothesis (MEDIUM-HIGH confidence sufficient for targeted fix attempt)

**Blocker 2: Telemetry Files Missing/Corrupted**
- Cause: Script may have crashed or telemetry path misconfigured
- Immediate Action:
  1. Check diagnostic_1step.log for Python exceptions
  2. Verify telemetry directory exists and has correct permissions
  3. Check if --telemetry-dir path was double-prepended (prior bugfix in 2025-11-22T172000Z should prevent this)
- Fallback: Rerun diagnostic with explicit absolute path for telemetry-dir (bypass script auto-prepending)
- Document in phase_b3_diagnostic_blocker.md

**Blocker 3: Regression Guard Fails**
- Cause: Phase B2 telemetry instrumentation may have introduced bug in cell+misset default path
- Immediate Action:
  1. Review pytest output for specific failure (assertion, exception, timeout)
  2. Check if telemetry code is ALWAYS executed (should be gated by `if config.telemetry_output_dir is not None`)
  3. If telemetry guard missing: Add conditional gate, rerun regression guard
- Fallback: Revert Phase B2 telemetry instrumentation (git revert 3338df1), mark B2/B3 as BLOCKED, escalate to alternative diagnostic approach
- Document in phase_b3_regression_failure.md

**Blocker 4: Inconclusive Verdict (Multiple Hypotheses Remain Plausible)**
- Cause: Step 001 metrics don't clearly point to single root cause (e.g., chi² catastrophic but U/log_scale/gradients all look healthy)
- Immediate Action:
  1. Accept H4 verdict from Phase B2 with MEDIUM-HIGH confidence (~70%)
  2. Proceed to Phase C1 fix implementation with targeted fix attempt
  3. If fix fails, will iterate back to deeper diagnostic
- Rationale: Phase B2 evidence (initialization healthy, optimization catastrophic, optimizer-agnostic) is sufficient for fix attempt; perfect diagnosis not required
- Document in phase_b3_forward_model_sanity_check.md with MEDIUM-HIGH confidence rating

## Findings Applied

**REFINE-001** (LBFGS scale warm-start, NaN/Inf guards):
- Applies to LBFGS optimizer choice for A_scale_only variant
- NaN/Inf guards already implemented in Phase B2 telemetry (grad_has_nan, grad_has_inf flags)

**PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard):
- Variance floor guard implemented in nanobrag_refinement.py
- Phase B2 telemetry captures V_denom histograms to verify guard is working
- If H2 (variance instability) is confirmed, may need to adjust sigma_floor value

**GRADIENT-001** (autograd graph preservation, crystal_overrides):
- Telemetry checksums (.sum().item()) must not detach tensors prematurely
- crystal_overrides (mosflm_a_star_tuple) construction is candidate bug for H4
- If A* staleness confirmed, verify crystal_overrides are recomputed per step, not aliased

**GEOMETRY-003** (U-matrix proper rotation, det(U)=1):
- Not directly relevant to this diagnostic (focuses on parameter update propagation, not det(U) validation)
- If U_matrix checksum changes unexpectedly in A_scale_only (train_orientation=False), revisit GEOMETRY-003

## Pointers

**Spec/Arch:**
- docs/spec-db-workflow.md §Stage A — Optimizer convergence criteria
- docs/spec-db-runtime.md §Gradient stability (NaN/Inf checks)
- docs/spec-db-core.md §Variance Model (sigma-floor guard)

**Fix Plan:**
- docs/fix_plan.md — Row [TORCH-GEOMETRY-CONVERGENCE-001], Attempts History entry 2025-11-22T190000Z

**Implementation Plan:**
- plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md
  - Phase B checklist (B0/B1/B2 done, B3 this loop, B4 pending)
  - Exit Criteria (CC ≥ 0.99, stable/improving χ²)

**Prior Evidence:**
- Phase B2 diagnostic decision: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/phase_b2_diagnostic_decision.md
- Phase B1 validation: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/phase_b1_validation_decision.md
- Phase A1 telemetry: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/

**Testing:**
- docs/TESTING_GUIDE.md §Stage A selectors
- docs/development/TEST_SUITE_INDEX.md — test_stage_a_expansion status

## Next Up

If Phase B3 completes successfully with clear H4 verdict:
- **Next Loop:** Phase C1 — Implement targeted fix based on H4 candidate bug (U-matrix staleness, log_scale clamp, crystal_overrides aliasing, or detach placement)
- **Validation:** Phase C2/C3 convergence tests (A_scale_only + D_full) to confirm fix resolves catastrophic failure

If Phase B3 blocked or inconclusive:
- **Alternative 1:** Proceed to Phase C1 based on Phase B2 MEDIUM-HIGH confidence H4 verdict (accept that perfect diagnosis is not required for fix attempt)
- **Alternative 2:** Pivot to simpler approach (disable quaternion U-matrix, revert to cell+misset only, document quaternion approach as infeasible)
