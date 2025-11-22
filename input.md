# Do Now — TORCH-GEOMETRY-CONVERGENCE-001 Phase C1: Convergence Telemetry & Root Cause Analysis

## Summary
Diagnose remaining quaternion U-matrix convergence pathology (chi² 1.13M → 8.8M over 10 steps, CC 1.0 → 0.765) via step-by-step telemetry analysis after Phase B5 initialization fix.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, Active, collected 1)

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/`

## Do Now

**Context:** Phase B5 (commit fe6048f) successfully resolved **initialization bug** (chi² step 0 = 1.13M healthy, 1000× improvement from catastrophic 1.425B). Zero-point parity maintained (corr=0.9999999843). Regression guard PASSED. **However**, convergence pathology persists with a DIFFERENT signature than pre-fix:
- **Pre-fix:** Started catastrophic (1.425B), ended catastrophic (1.425B), negative CC (-0.045)
- **Post-fix:** Started healthy (1.13M), degraded moderately (8.8M after 10 steps), positive CC (0.765)

This confirms the initialization bug (code path discrepancy in MOSFLM A* injection) is **separate from** the convergence bug (optimizer/loss/gradient pathology during parameter updates).

**Objective:** Execute Phase C1 convergence telemetry analysis to identify root cause of chi² degradation during optimization (likely H1 Adam LR incompatibility, H2 variance instability, or H3 gradient pathology).

**Implementation Checklist (Phase C1):**

1. **Review Phase B5 artifacts** (2025-11-22T183012Z):
   - Read `phase_b5_fix_decision.md` (fix summary + convergence failure signature)
   - Read `diagnostic_b5_postfix_v2/block_dof_results_u_matrix.json` (10-step convergence trajectory)
   - Note: chi²_before=1.13M (healthy), chi²_after=8.8M (7.8× degradation), CC_after=0.765 (positive but degraded)

2. **Execute 10-step convergence test with comprehensive telemetry**:
   - **Command:**
     ```bash
     KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python \
       plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
       --use-u-matrix \
       --phases 5 \
       --dof-variants A_scale_only \
       --adam-steps 10 \
       --device cpu \
       --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_telemetry \
       --telemetry-dir telemetry
     ```
   - **Timeout:** 2400s (40 minutes, HKL grid builds ~10-15 min + 10 Adam steps ~20-25 min on CPU)
   - **Expected outputs:**
     - `convergence_telemetry/telemetry/telemetry_step_{000..009}.json` (all 10 steps + initialization step)
     - `convergence_telemetry/block_dof_results_u_matrix.json` (final convergence metrics)
     - `convergence_telemetry/zero_point_check.json` (zero-point parity validation)
   - **ROI:** Full telemetry trajectory capturing transition from healthy initialization (step 0) to degraded convergence (steps 1-10)

3. **Extract convergence trajectory metrics** into `convergence_trajectory.txt`:
   - For each telemetry step 000-009:
     - Step number
     - `chi_squared` (total loss)
     - `grad_log_scale` norm (optimizer magnitude signal)
     - `grad_q_params` norm (if train_orientation=True, else null for A_scale_only)
     - `q_norm` (quaternion magnitude, should stay ~1.0)
     - `has_nan` / `has_inf` gradient flags
   - Summary statistics:
     - Chi² trajectory: monotonic increase, plateau, oscillation?
     - Gradient norms: stable O(1-100), exploding >1e5, vanishing <1e-6?
     - Divergence step: first step where chi² increases >10% from previous step
   - **Command:**
     ```bash
     python -c "
     import json
     import pathlib
     tel_dir = pathlib.Path('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_telemetry/telemetry')
     with open('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_trajectory.txt', 'w') as f:
         f.write('Step\tChi²\tGrad_log_scale\tq_norm\tHas_NaN\tHas_Inf\n')
         for i in range(10):
             tel_file = tel_dir / f'telemetry_step_{i:03d}.json'
             if tel_file.exists():
                 data = json.loads(tel_file.read_text())
                 chi2 = data.get('chi_squared', 'N/A')
                 grad_ls = data.get('grad_log_scale', 'N/A')
                 qnorm = data.get('q_norm', 'N/A')
                 has_nan = data.get('has_nan', False)
                 has_inf = data.get('has_inf', False)
                 f.write(f'{i}\t{chi2}\t{grad_ls}\t{qnorm}\t{has_nan}\t{has_inf}\n')
     "
     ```

4. **Synthesize root cause hypothesis** in `phase_c1_convergence_analysis.md`:
   - **Section: Telemetry Trajectory Analysis**
     - Plot/table chi² vs step (is degradation monotonic, sudden, or oscillating?)
     - Plot/table gradient norms vs step (stable, exploding, vanishing?)
     - Identify divergence step (first chi² jump)
   - **Section: Hypothesis Verdicts**
     - **H1 (Adam LR too high):** If grad_log_scale stable O(1-100) but chi² increases monotonically → LR overshoot, parameter updates too large
       - Evidence: Gradient norms healthy, no NaN/Inf, but chi² degrades steadily
       - Recommended fix: Reduce Adam LR to 1e-5 or 1e-6 for U-matrix path
     - **H2 (Variance instability):** If variance components show sigma_floor clamping →1.0 or exploding V_denom
       - Evidence: (Phase B2 telemetry has V_denom histograms, but may not be captured in current run — if missing, note for future)
       - Recommended fix: Adjust sigma_floor, loss clamping
     - **H3a (Gradient NaN/Inf):** If has_nan=true OR has_inf=true at any step
       - Evidence: Telemetry gradient flags
       - Recommended fix: FP64, gradient clipping, investigate autograd graph
     - **H3b (Gradient explosion):** If grad_log_scale >1e5 OR q_norm drifts far from 1.0
       - Evidence: Gradient norms explode during optimization
       - Recommended fix: Gradient clipping, quaternion renormalization frequency
   - **Section: Primary Hypothesis** — Choose ONE primary hypothesis with confidence level (HIGH/MEDIUM/LOW) and cite specific telemetry evidence (step numbers, metric values)
   - **Section: Recommended Next Actions:**
     - **Path A (Hypothesis testable with simple fix):** Describe targeted fix (e.g., LR reduction, gradient clipping config flag)
     - **Path B (Hypothesis requires deeper investigation):** Describe additional diagnostic (e.g., variance telemetry, finite-difference gradient validation)
     - **Path C (No clear hypothesis):** Recommend alternative parameterization (hybrid cell+quaternion, LBFGS-only, mapping-path-only)

5. **Decision template** in `phase_c1_decision.md`:
   ```markdown
   # Phase C1 Decision — Convergence Root Cause

   **Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
   **Phase:** C1 (Convergence Telemetry & Root Cause Analysis)
   **Date:** 2025-11-22T230000Z

   ## Verdict
   [ ] **Path A — Primary Hypothesis CLEAR (implement targeted fix)**
   [ ] **Path B — Hypothesis requires additional diagnostic**
   [ ] **Path C — No clear hypothesis (escalate to alternative parameterization)**

   ## Evidence Summary
   - Divergence step: [step number]
   - Chi² trajectory: [monotonic increase / plateau / oscillation / sudden jump]
   - Gradient norms: [stable O(1-100) / exploding >1e5 / vanishing <1e-6]
   - NaN/Inf flags: [true/false, step numbers if true]
   - Quaternion norm drift: [q_norm range across steps]

   ## Primary Hypothesis
   [H1 / H2 / H3a / H3b] with [HIGH / MEDIUM / LOW] confidence

   **Rationale:** [1-2 sentences citing specific telemetry evidence]

   ## Recommended Next Actions
   [Targeted fix implementation / Additional diagnostic / Alternative parameterization escalation]
   ```

6. **Update implementation.md checklist** — Mark C1 as `[x] DONE` with timestamp and primary hypothesis verdict.

7. **Regression guard** — Run `test_stage_a_expansion` to ensure Phase B5 fix didn't introduce regressions:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
   > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/pytest_regression.log 2>&1
   ```
   - **Expected:** PASSED (cell+misset path unaffected by U-matrix telemetry instrumentation)

8. **Write summary** in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/summary.md`:
   - Phase C1 convergence telemetry execution status (success/timeout)
   - Telemetry file count (10/10 steps captured?)
   - Primary hypothesis verdict (H1/H2/H3a/H3b with confidence)
   - Divergence step number and chi² trajectory summary
   - Recommended next actions (Path A/B/C from decision doc)
   - Regression guard status (PASSED/FAILED)

9. **Commit and push**:
   ```bash
   git add plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/
   git add plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md
   git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase C1: Convergence telemetry & root cause analysis (tests: test_stage_a_expansion)

   **Objective:** Diagnose remaining quaternion U-matrix convergence pathology after Phase B5 initialization fix (chi² 1.13M → 8.8M over 10 steps, CC 1.0 → 0.765).

   **Work Completed:**
   - Executed 10-step A_scale_only convergence test with telemetry (2025-11-22T230000Z/convergence_telemetry/)
   - Extracted convergence trajectory metrics (convergence_trajectory.txt)
   - Synthesized root cause hypothesis (phase_c1_convergence_analysis.md)
   - Decision: [Path A/B/C] — [Primary hypothesis] with [confidence] confidence
   - Regression guard: test_stage_a_expansion [PASSED/FAILED]

   **Primary Hypothesis:** [H1/H2/H3a/H3b] — [one-line rationale]

   **Recommended Next Actions:** [Targeted fix / Additional diagnostic / Escalation]

   **Artifacts:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   git push
   ```

## How-To Map

**Step 1 — Review Phase B5 artifacts:**
```bash
cd plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z
cat phase_b5_fix_decision.md
cat diagnostic_b5_postfix_v2/block_dof_results_u_matrix.json
```

**Step 2 — Execute convergence test with telemetry:**
```bash
cd /home/ollie/Documents/diffbragg_example
timeout 2400 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only \
  --adam-steps 10 \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_telemetry \
  --telemetry-dir telemetry \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_test.log 2>&1
echo "Exit code: $?"
ls -lh plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_telemetry/telemetry/
```

**Step 3 — Extract trajectory metrics:**
```bash
python3 -c "
import json
import pathlib
tel_dir = pathlib.Path('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_telemetry/telemetry')
with open('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_trajectory.txt', 'w') as f:
    f.write('Step\tChi²\tGrad_log_scale\tq_norm\tHas_NaN\tHas_Inf\n')
    for i in range(10):
        tel_file = tel_dir / f'telemetry_step_{i:03d}.json'
        if tel_file.exists():
            data = json.loads(tel_file.read_text())
            chi2 = data.get('chi_squared', 'N/A')
            grad_ls = data.get('grad_log_scale', 'N/A')
            qnorm = data.get('q_norm', 'N/A')
            has_nan = data.get('has_nan', False)
            has_inf = data.get('has_inf', False)
            f.write(f'{i}\t{chi2}\t{grad_ls}\t{qnorm}\t{has_nan}\t{has_inf}\n')
"
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/convergence_trajectory.txt
```

**Step 4 — Synthesize root cause hypothesis:**
- Read `convergence_trajectory.txt` to identify divergence step and trajectory pattern
- Analyze gradient norms, NaN/Inf flags, quaternion norm drift
- Choose primary hypothesis (H1/H2/H3a/H3b) with confidence level
- Write analysis to `phase_c1_convergence_analysis.md` with evidence citations

**Step 5 — Write decision doc:**
- Copy decision template above to `phase_c1_decision.md`
- Fill in verdict (Path A/B/C), evidence summary, primary hypothesis, recommended next actions

**Step 6 — Update implementation checklist:**
- Mark C1 as `[x] DONE (2025-11-22T230000Z)` with primary hypothesis verdict in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`

**Step 7 — Regression guard:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
> plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/pytest_regression.log 2>&1
tail -20 plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/pytest_regression.log
```

**Step 8 — Write summary:**
- Create `summary.md` with: telemetry execution status, file count, primary hypothesis, divergence step, recommended next actions, regression guard result

**Step 9 — Commit and push:**
```bash
git add plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/
git add plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md
git commit -m "[See commit message template in Do Now Step 9]"
git push
```

## Pitfalls To Avoid

1. **DO NOT** modify production code in this loop — Phase C1 is evidence-only (telemetry analysis + hypothesis synthesis).
2. **DO NOT** skip zero-point validation in telemetry run — confirms Phase B5 fix is still working.
3. **DO NOT** use background bash for convergence test — run in foreground with `timeout` to ensure completion verification.
4. **DO NOT** assume hypothesis without telemetry evidence — cite specific step numbers and metric values in analysis.
5. **DO NOT** bundle multiple hypotheses — choose ONE primary hypothesis with highest confidence.
6. **Device/dtype neutrality:** Telemetry instrumentation must not assume CUDA (cpu-only test).
7. **Protected Assets:** Do not modify `dbex/nanobrag_refinement.py` in this loop (telemetry instrumentation from Phase B2 already present).
8. **Vectorization:** Telemetry extraction script must handle missing files gracefully (some steps may timeout).
9. **No ad-hoc scripts:** Use inline `python -c` for simple trajectory extraction (T0 tier per scriptization policy).
10. **Environment freeze:** Do not install packages or upgrade dependencies.

## If Blocked

**Timeout during convergence test (exit code 143 or 124):**
- Capture partial telemetry if any steps completed (e.g., steps 0-5 only)
- Document timeout in `phase_c1_convergence_analysis.md` as blocker
- Recommend reduced-step rerun (5 steps instead of 10) OR GPU execution for next loop
- Update fix_plan Attempts History with timeout evidence

**Telemetry files missing or incomplete:**
- Document which steps are missing in `phase_c1_convergence_analysis.md`
- If step 0 missing: initialization telemetry failed, recommend debugging script
- If steps 1-9 missing: optimizer loop telemetry failed, recommend investigating dbex/nanobrag_refinement.py instrumentation
- If zero_point_check.json missing: parity validation failed, may indicate Phase B5 fix regression

**No clear hypothesis after analysis:**
- Choose **Path C** in decision doc
- Recommend escalation to alternative parameterization (hybrid cell+quaternion, LBFGS-only, mapping-path-only)
- Document inconclusive evidence in `phase_c1_convergence_analysis.md`

## Findings Applied

- **REFINE-001:** LBFGS for scale-only warm-start, NaN/Inf gradient guards (H3a check via telemetry flags)
- **PHYSICS-LOSS-002:** Variance-weighted chi-squared sigma-floor guard (H2 check via variance components if available)
- **GRADIENT-001:** Autograd graph preservation, crystal_overrides handling (Phase B5 fix applied this)
- **PARITY-003:** Quaternion U-matrix parity perfect but convergence failed (escalation context)

## Pointers

- Spec: `docs/spec-db-workflow.md §Stage A — Optimizer convergence` (Adam LR=1e-4 for orientation/cell, LBFGS for scale-only)
- Spec: `docs/spec-db-runtime.md §Gradient Stability` (NaN/inf checks, gradient clipping)
- Spec: `docs/spec-db-core.md §Variance Model` (sigma-floor guard to prevent infinite weights)
- Architecture: `docs/architecture/pytorch_design.md` (U-matrix parameterization design)
- Fix Plan: `docs/fix_plan.md` row [TORCH-GEOMETRY-CONVERGENCE-001] (Attempts History entry for Phase C1)
- Implementation Plan: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` Phase C checklist
- Testing: `docs/TESTING_GUIDE.md §2` (test_stage_a_expansion selector)
- Finding: `docs/findings.md` REFINE-001 (LBFGS usage), PHYSICS-LOSS-002 (variance guards), GRADIENT-001 (autograd preservation)

## Next Up

If Ralph finishes Phase C1 early and convergence telemetry analysis is complete with a **clear primary hypothesis** (Path A):
- **Option 1 (H1 — Adam LR too high):** Implement LR reduction fix in Phase C2 (extend RefinementConfig with `u_matrix_learning_rate` field, update optimizer setup)
- **Option 2 (H3b — Gradient explosion):** Implement gradient clipping fix in Phase C2 (extend RefinementConfig with `gradient_clip_threshold`, add `torch.nn.utils.clip_grad_norm_` in optimizer loop)

If analysis yields **Path B** (hypothesis requires additional diagnostic):
- Schedule Phase C2 as deeper diagnostic (variance telemetry instrumentation, finite-difference gradient validation, quaternion renormalization frequency analysis)

If analysis yields **Path C** (no clear hypothesis):
- Do NOT proceed with fix implementation
- Galph will escalate to TORCH-GEOMETRY-CONVERGENCE-002 for alternative parameterization (hybrid cell+quaternion, LBFGS-only, or mapping-path-only refinement)

## Doc Sync Plan
Not applicable (no tests added/renamed in this loop).
