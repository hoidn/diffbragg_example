# Engineering Task — TORCH-GEOMETRY-CONVERGENCE-001 Phase C2: Adam LR Reduction Fix

## Summary
Implement Adam learning rate reduction fix (LR=1e-5 for U-matrix path) to resolve catastrophic first-step overshoot in quaternion parameterization, validated by Phase C1 root cause analysis showing LR=1e-4 is 1000× too high for quaternion gradient magnitudes O(150k).

## Mode
TDD

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure (Phase C2: LR Reduction Fix Implementation & Validation)

## Branch
`integration`

## Mapped Tests
**Active Selectors:**
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard for cell+misset default path)

**Validation Criteria:**
- Phase C2: Phase 5 A_scale_only with `--use-u-matrix --u-matrix-lr 1e-5` must achieve:
  - chi² ≤ 1.2M after 10 steps (≤5% drift from initialization ~1.13M)
  - median ROI CC ≥ 0.99
  - monotonic chi² improvement OR stable oscillation (no catastrophic jumps)
- Phase C3: Phase 5 D_full with `--use-u-matrix --u-matrix-lr 1e-5` must achieve:
  - Monotonic chi² improvement (no large CC collapses <0.9)
  - Final chi² < initial chi² (convergence toward optimum)

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/`
- `phase_c2_validation_a_scale_only.log` (convergence test log)
- `phase_c2_validation/block_dof_results_u_matrix.json` (A_scale_only metrics)
- `phase_c2_validation/zero_point_check.json` (initialization parity validation)
- `phase_c2_validation/telemetry/` (optional: telemetry JSONs if needed for debugging)
- `phase_c3_validation_d_full.log` (D_full convergence test log)
- `phase_c3_validation/block_dof_results_u_matrix.json` (D_full metrics)
- `phase_c2_c3_decision.json` (decision template with Path A/B/C verdicts)
- `pytest_regression.log` (regression guard results)
- `summary.md` (turn summary)

---

## Do Now (Phase C2 + C3 Implementation & Validation)

**Context:** Phase C1 convergence telemetry (2025-11-22T230000Z) identified **H1 (Adam LR too high)** as primary root cause with HIGH confidence (~85%). First optimizer step causes catastrophic overshoot (chi² 1.13M → 8.84M, +679%) because LR=1e-4 (designed for cell/misset gradients O(1-100)) produces massive quaternion update Δq = -1e-4 × 150k = -15.0 (~35° rotation). Recommended fix: Reduce Adam LR to 1e-5 for U-matrix path. This loop implements the fix and validates convergence success.

**Implementation Tasks:**

1. **Extend `RefinementConfig` with `u_matrix_learning_rate` field** (`dbex/nanobrag_refinement.py`):
   - Add field: `u_matrix_learning_rate: float = 1e-5` (default 10× lower than standard LR=1e-4)
   - Location: After existing `use_u_matrix_parameterization` field
   - Docstring: "Learning rate for Adam optimizer when use_u_matrix_parameterization=True. Default 1e-5 (10× lower than cell/misset LR) to accommodate quaternion gradient scale O(150k). Per CONVERGENCE-001 Phase C1 root cause analysis."

2. **Update Adam optimizer setup in `run_nanobrag_refinement`** (`dbex/nanobrag_refinement.py`):
   - Location: Stage A closure, line ~1080-1085 (Adam optimizer instantiation)
   - Conditional LR selection:
     ```python
     lr = config.u_matrix_learning_rate if config.use_u_matrix_parameterization else 1e-4
     optimizer = torch.optim.Adam([log_scale_param], lr=lr, betas=(0.9, 0.999))
     ```
   - Ensure cell+misset path UNCHANGED (default LR=1e-4 preserved when `use_u_matrix_parameterization=False`)

3. **Extend script with `--u-matrix-lr` CLI flag**:
   - Script path: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
   - Add argument: `--u-matrix-lr`, type=float, default=1e-5
   - Help text: "Learning rate for Adam optimizer when --use-u-matrix is enabled (default: 1e-5, per CONVERGENCE-001 Phase C1 root cause)"
   - Integration: Pass `u_matrix_learning_rate=args.u_matrix_lr` to `RefinementConfig(...)` in script main
   - Location: After `--use-u-matrix` flag definition (~line 80-90)

4. **Phase C2 Validation Test (A_scale_only)**:
   - Run command:
     ```bash
     timeout 1200 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
       --use-u-matrix \
       --u-matrix-lr 1e-5 \
       --phases 5 \
       --dof-variants A_scale_only \
       --adam-steps 10 \
       --device cpu \
       --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_validation/ \
       > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_validation_a_scale_only.log 2>&1
     ```
   - Extract metrics from `block_dof_results_u_matrix.json`:
     - `chi_squared_after` (expect ≤ 1.2M, within 5% of initialization ~1.13M)
     - `median_roi_cc_after` (expect ≥ 0.99)
     - `chi_squared_before` (sanity check: ~1.13M initialization healthy per Phase B5 fix)
     - `correlation_zero_point` (sanity check: ≥ 0.999999, parity maintained)

5. **Phase C3 Validation Test (D_full)** (CONDITIONAL: Run ONLY if Phase C2 succeeds):
   - Run command:
     ```bash
     timeout 1200 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
       --use-u-matrix \
       --u-matrix-lr 1e-5 \
       --phases 5 \
       --dof-variants D_full \
       --adam-steps 10 \
       --device cpu \
       --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c3_validation/ \
       > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c3_validation_d_full.log 2>&1
     ```
   - Extract metrics from `block_dof_results_u_matrix.json`:
     - `chi_squared_after` vs `chi_squared_before` (expect monotonic improvement OR stable)
     - `median_roi_cc_after` (expect ≥ 0.9, no catastrophic collapse)

6. **Decision Synthesis** (write `phase_c2_c3_decision.json`):
   - Template (fill based on validation results):
     ```json
     {
       "phase_c2_a_scale_only": {
         "chi_squared_before": <value>,
         "chi_squared_after": <value>,
         "chi_squared_drift_pct": <(after-before)/before*100>,
         "median_roi_cc_after": <value>,
         "verdict": "SUCCESS|PARTIAL|FAIL",
         "notes": "<interpretation>"
       },
       "phase_c3_d_full": {
         "chi_squared_before": <value>,
         "chi_squared_after": <value>,
         "chi_squared_improvement_pct": <(before-after)/before*100>,
         "median_roi_cc_after": <value>,
         "verdict": "SUCCESS|PARTIAL|FAIL|SKIPPED",
         "notes": "<interpretation>"
       },
       "overall_verdict": "Path A: SUCCESS (proceed to Phase C4-C6)|Path B: PARTIAL (tune LR further)|Path C: FAIL (escalate to alternative fix)",
       "recommended_next_action": "<describe>"
     }
     ```
   - Decision tree:
     - **Path A (SUCCESS):** C2 chi² drift ≤ 5% AND CC ≥ 0.99 AND C3 monotonic improvement → Proceed to Phase C4 (regression guard), C5 (findings update CONVERGENCE-002), C6 (close initiative)
     - **Path B (PARTIAL):** C2 improved vs pre-fix (chi² <8.8M) but not within 5% tolerance → Try tighter LR (1e-6 or 1e-7) OR per-parameter LR OR gradient clipping
     - **Path C (FAIL):** C2 still catastrophic (chi² >8M, CC <0.9) → Escalate to alternative fix (LBFGS, Riemannian Adam, hybrid parameterization)

7. **Regression Guard** (run AFTER C2/C3 validation):
   - Execute: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v`
   - Capture output to: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/pytest_regression.log`
   - Verify PASSED (cell+misset default path unchanged)

8. **Update `implementation.md` Checklist**:
   - Mark Phase C1 as complete (already done per commit 04ea022)
   - Mark Phase C2 as complete (with decision verdict from step 6)
   - Mark Phase C3 as complete OR note "SKIPPED if C2 failed" OR "PARTIAL (needs tuning)"
   - Note C4-C6 status based on Path A/B/C verdict

9. **Emit `summary.md`**:
   - Location: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/summary.md`
   - Content: Turn summary paragraph (3-5 sentences) + decision verdict + next action + artifacts list

---

## How-To Map (Exact Commands & ROI Definitions)

### Phase C2 Validation (A_scale_only)
```bash
# 1. Implement config field + optimizer LR branch + CLI flag (steps 1-3 above)

# 2. Run A_scale_only validation test
cd /home/ollie/Documents/diffbragg_example
timeout 1200 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --u-matrix-lr 1e-5 \
  --phases 5 \
  --dof-variants A_scale_only \
  --adam-steps 10 \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_validation/ \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_validation_a_scale_only.log 2>&1
echo "Exit code: $?"

# 3. Extract metrics
jq '{chi_squared_before, chi_squared_after, median_roi_cc_after, correlation_zero_point}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_validation/block_dof_results_u_matrix.json
```

### Phase C3 Validation (D_full, CONDITIONAL)
```bash
# Only run if C2 verdict is SUCCESS or PARTIAL with chi² <8M

timeout 1200 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --u-matrix-lr 1e-5 \
  --phases 5 \
  --dof-variants D_full \
  --adam-steps 10 \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c3_validation/ \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c3_validation_d_full.log 2>&1
```

### Regression Guard
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
> plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/pytest_regression.log 2>&1
tail -20 plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/pytest_regression.log
```

### Decision Synthesis
```bash
# Manually author phase_c2_c3_decision.json based on extracted metrics
# Use decision tree from step 6 to determine Path A/B/C
```

---

## Pitfalls To Avoid

1. **Device/Dtype Neutrality:** Ensure LR change applies ONLY to optimizer initialization, not forward model or gradient computation.
2. **Protected Assets:** Do NOT modify cell+misset default path (LR=1e-4 preserved when `use_u_matrix_parameterization=False`).
3. **Regression Guard:** Run `test_stage_a_expansion` AFTER implementing LR fix to ensure backward compatibility.
4. **Conditional Phase C3:** Do NOT run D_full test if A_scale_only FAILS catastrophically (chi² >8M, CC <0.9).
5. **Telemetry Overhead:** Telemetry is OPTIONAL for C2/C3; omit `--telemetry-dir` flag unless debugging is needed (Phase C1 already captured gradient behavior).
6. **Environment Freeze:** Do NOT install new packages or modify environment; LR fix is pure config/code change.
7. **Timeout Handling:** If validation test times out (>20min), capture partial log and note in decision.json as BLOCKED; do NOT retry without investigation.
8. **Decision Template Completion:** Fill ALL fields in `phase_c2_c3_decision.json` with actual metrics (no placeholders like "TBD" or "N/A" unless test was skipped).
9. **Implementation.md Sync:** Update checklist AFTER validation completes, not before (avoid marking C2/C3 complete prematurely).
10. **LR Range Validation:** If C2 shows partial improvement (chi² 1.13M → 3M instead of catastrophic 8.8M), try LR=1e-6 as fallback before marking as FAIL.

---

## If Blocked

**Scenario 1: Phase C2 A_scale_only FAILS (chi² >8M, CC <0.9)**
- Capture logs/metrics in `phase_c2_validation_a_scale_only.log` and `block_dof_results_u_matrix.json`
- Mark decision.json verdict as "Path C: FAIL (LR reduction insufficient)"
- Log in Attempts History: "Phase C2 A_scale_only failed with chi²=<value>, CC=<value>; LR=1e-5 insufficient to resolve overshoot. Next action: Try LR=1e-6 OR escalate to LBFGS/Riemannian Adam alternative."
- Do NOT proceed to Phase C3; do NOT update findings

**Scenario 2: Phase C2 validation test TIMES OUT (>20min)**
- Capture partial log (first 100 lines + last 100 lines) to `phase_c2_validation_a_scale_only.log`
- Mark decision.json verdict as "BLOCKED: timeout during HKL grid building or ROI scoring"
- Log in Attempts History: "Phase C2 timed out at <timestamp>; investigate HKL warmup or ROI overhead before retry."
- Do NOT mark C2 as complete; do NOT proceed to C3

**Scenario 3: Regression guard `test_stage_a_expansion` FAILS**
- Capture full pytest output to `pytest_regression.log`
- Mark decision.json overall_verdict as "BLOCKED: regression in cell+misset path"
- Log in Attempts History: "Regression guard failed; LR change broke cell+misset default path. Revert LR change and audit optimizer setup."
- Do NOT proceed to findings update; do NOT close initiative

---

## Findings Applied

**Relevant Finding IDs:**
- **REFINE-001:** LBFGS scale warm-start, NaN/Inf guards, gradient stability conventions → Adherence: LR reduction fix maintains gradient stability (no NaN/Inf), preserves LBFGS fallback option if Adam fails
- **PHYSICS-LOSS-002:** Variance-weighted chi-squared sigma-floor guard → Adherence: LR change does NOT modify loss function; sigma-floor guard remains active
- **GRADIENT-001:** Autograd graph preservation, crystal_overrides handling → Adherence: LR change is optimizer-only; autograd graph UNCHANGED
- **CONVERGENCE-001 Phase C1:** Adam LR=1e-4 too high for quaternion gradients O(150k); first-step overshoot causes chi² 1.13M → 8.84M → Adherence: Implementing recommended fix (LR=1e-5) per Phase C1 decision.md Path A

**No relevant findings in the knowledge base** beyond those listed above.

---

## Pointers

**Spec References:**
- `docs/spec-db-workflow.md` §Stage A — Optimizer convergence (line ~150-180)
- `docs/spec-db-runtime.md` §Gradient stability (line ~200-220)
- `docs/spec-db-core.md` §Variance Model (line ~300-350)

**Architecture References:**
- `docs/architecture/pytorch_design.md` — RefinementConfig field conventions (line ~80-120)
- `docs/pytorch_runtime_checklist.md` — Optimizer setup patterns (line ~40-60)

**Testing References:**
- `docs/TESTING_GUIDE.md` §2.1 — `test_stage_a_expansion` selector (smoke test for Stage A default path)
- `docs/development/TEST_SUITE_INDEX.md` — test_stage_a_expansion entry (line ~50-70)

**Fix Plan References:**
- `docs/fix_plan.md` — Row [TORCH-GEOMETRY-CONVERGENCE-001] (Tier 1, in_progress, Phase C2 pending)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Phase C checklist (C1 complete, C2-C6 pending)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/phase_c1_decision.md` — LR reduction fix specification (line 113-131)

**Code Locations:**
- `dbex/nanobrag_refinement.py:~750-800` — RefinementConfig definition (add `u_matrix_learning_rate` field)
- `dbex/nanobrag_refinement.py:~1080-1085` — Adam optimizer setup in Stage A closure (conditional LR selection)
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:~80-90` — CLI argument parser (add `--u-matrix-lr` flag)

---

## Next Up (Optional Early Completion Tasks)

If you finish Phase C2/C3 validation early AND Path A verdict (SUCCESS):

1. **Phase C4 Extended Regression Guard** (optional):
   - Run full `tests/dbex/test_torch_refine_smoke.py` module (not just `test_stage_a_expansion`)
   - Validate Stage B/C smoke tests unaffected by LR change

2. **Draft CONVERGENCE-002 Finding** (preparation for Phase C5):
   - Document root cause: Adam LR=1e-4 incompatible with quaternion gradient scale O(150k), causing first-step overshoot (chi² 1.13M → 8.84M)
   - Document fix: Reduce LR to 1e-5 for U-matrix path via `RefinementConfig.u_matrix_learning_rate`
   - Document validation metrics: Phase C2 A_scale_only chi² drift <5%, CC ≥ 0.99 after 10 steps
   - Save draft to `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/convergence_002_finding_draft.md`

---

## Doc Sync Plan

**Not applicable** — No new tests added/renamed this loop. Phase C2/C3 validation uses existing script infrastructure. If Phase C2 succeeds and initiative closes (Phase C6), update `docs/TESTING_GUIDE.md` §3 (Usage Examples) with `--use-u-matrix --u-matrix-lr 1e-5` example.

---

## Normative Math/Physics

**Learning Rate Scaling:** See `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T230000Z/phase_c1_decision.md` §Physics Interpretation (line 87-109) for normative derivation of quaternion update magnitude Δq = -LR × gradient and rotation angle equivalence. Do NOT paraphrase the gradient scale calculation; reference the exact section for parameter update physics.

**Quaternion Normalization:** See `docs/spec-db-core.md` §U-Matrix Parameterization (if exists) OR `dbex/nanobrag_bridge.py:quaternion_to_matrix` docstring for normative quaternion → SO(3) rotation matrix mapping. Ensure LR change does NOT modify normalization frequency or manifold constraints.

---

**End of input.md**
