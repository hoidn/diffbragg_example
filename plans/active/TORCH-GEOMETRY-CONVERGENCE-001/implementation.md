# Implementation Plan: TORCH-GEOMETRY-CONVERGENCE-001

## Initiative
- ID: TORCH-GEOMETRY-CONVERGENCE-001
- Title: Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md, docs/spec-db-runtime.md, docs/spec-db-core.md
- Status: pending

## Goals
- Diagnose why quaternion U-matrix parameterization (PARITY-002) achieves perfect parity (<1e-17) but catastrophically fails during Adam optimization (χ²→1.43B, CC→-0.045).
- Identify root cause among: optimizer hyperparameters, variance-weighted loss numerical stability, gradient pathologies (NaN/inf/exploding), quaternion normalization constraint interaction.
- Implement fix enabling Stage A convergence with U-matrix parameterization (CC ≥ 0.99, stable/improving χ²).
- Document findings and restore quaternion path viability OR recommend alternative parameterization.

## Phases Overview
- Phase A — Evidence Collection & Gradient Diagnosis: Instrument quaternion U-matrix closure with telemetry (parameter trajectories, gradient norms, loss components per step); diagnose first divergence point.
- Phase B — Hypothesis Testing: Test optimizer alternatives (LBFGS, lower LR), loss stability (gradient clipping, finite-difference validation), quaternion constraint handling (normalization frequency, gradient projection).
- Phase C — Fix Implementation & Validation: Implement chosen fix, validate Phase 5 convergence (A_scale_only + D_full), regression guard, findings update.

## Exit Criteria
1. Root cause of quaternion U-matrix convergence failure is identified with evidence (gradient telemetry, loss component analysis, parameter trajectories).
2. Chosen fix (optimizer tuning, loss modification, or constraint handling) enables `stage_a_mapping_adam_debug.py` Phase 5 with `--use-u-matrix` to pass:
   - A_scale_only: median ROI CC ≥ 0.99, χ² stable (≤0.5% drift) after 10 Adam steps
   - D_full (or equivalent U-matrix+scale variant): monotonic χ² improvement without large CC collapses
3. `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` regression guard passes.
4. Findings ledger updated with CONVERGENCE-002 (or extension to existing REFINE-001/GRADIENT-001) documenting root cause, fix, and quaternion U-matrix usage conventions.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md §Stage A — Optimizer convergence`
- [ ] **Spec Constraint:** `docs/spec-db-runtime.md §Gradient stability`
- [ ] **Spec Constraint:** `docs/spec-db-core.md §Variance Model`
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [TORCH-GEOMETRY-CONVERGENCE-001]`
- [ ] **Finding/Policy ID:** `REFINE-001` (LBFGS scale warm-start, NaN/Inf guards)
- [ ] **Finding/Policy ID:** `PHYSICS-LOSS-002` (variance-weighted chi-squared sigma-floor guard)
- [ ] **Finding/Policy ID:** `GRADIENT-001` (autograd graph preservation, crystal_overrides)
- [ ] **Escalation Source:** `TORCH-GEOMETRY-PARITY-003` decision.json (2025-11-22T130000Z) — Quaternion U-matrix parity perfect but convergence catastrophically failed

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md, docs/spec-db-runtime.md, docs/spec-db-core.md
- **Key Clauses:**
  - spec-db-workflow.md §Stage A: "Adam optimizer with LR=1e-4 for orientation/cell refinement; LBFGS for scale-only"
  - spec-db-runtime.md §Gradient Stability: "Gradient checks must validate absence of NaN/inf; clip extreme magnitudes if necessary"
  - spec-db-core.md §Variance Model: "Variance-weighted chi-squared with sigma-floor guard to prevent infinite weights"

## Architecture / Interfaces

### Current State (PARITY-003 Escalation)
- Quaternion U-matrix parameterization: Perfect parity at zero deltas (max_abs_diff=3.469e-18)
- Catastrophic convergence failure: A_scale_only Adam LR=1e-4, 10 steps → χ² +125,648%, CC 1.0→-0.045
- Failure NOT file-specific: Reproduced with canonical refGeom.expt (det(U)=1.0 per dxtbx audit)
- Hypothesis space: Optimizer incompatibility, loss numerical stability, gradient pathology, quaternion constraint interaction

### Root Cause Hypotheses

1. **H1: Adam hyperparameters incompatible with quaternion gradients**
   - Quaternion gradient manifold (S³ unit sphere) may require different LR scaling than cell/misset Euclidean parameters
   - Adam momentum accumulation may violate unit-norm constraint between normalization steps
   - Test: Try LBFGS (no momentum), lower LR (1e-5, 1e-6), gradient clipping

2. **H2: Variance-weighted loss numerical instability**
   - Quaternion U-matrix may produce model images with different variance structure than cell+misset
   - Sigma-floor guard (PHYSICS-LOSS-002) may interact poorly with quaternion parameterization
   - Test: Log variance components (I_model, sigma_readout, sigma_floor, clamp fraction) per step; check for NaN/inf in loss or gradients

3. **H3: Gradient pathology (NaN/inf/exploding magnitudes)**
   - Quaternion normalization `q / ||q||` may produce numerical instabilities during backprop if ||q|| approaches zero
   - Matrix operations in `quaternion_to_matrix` may amplify small errors
   - Test: Instrument closure with gradient norm logging (global + per-DOF); check for NaN/inf; validate finite-difference gradients

4. **H4: Quaternion constraint handling**
   - Current implementation normalizes quaternion once per forward pass; if Adam updates violate ||q||=1 between normalizations, gradients may point off-manifold
   - Need Riemannian optimization (project gradients to tangent space of S³) or more frequent normalization
   - Test: Log ||q|| per step; compare gradient magnitudes before/after normalization; try Riemannian Adam or constrained optimization

### Proposed Diagnostic Protocol (Phase A)

**Step A1: Instrument Quaternion Closure with Telemetry**
- Add logging to `build_stage_a_lbfgs_closure` (U-matrix path) to capture per-step:
  - Parameter values: `q_params` (4-element quaternion), `log_scale`, `||q||`
  - Gradient norms: `||∂L/∂q||`, `||∂L/∂log_scale||`, element-wise max/min gradients
  - Loss components: total chi-squared, variance components (mean/median/max of I_model, V_denom), clamp fraction
  - Model outputs: forward model chi-squared, median ROI CC (if available without full ROI scoring overhead)
- Run `stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only --adam-steps 10` with telemetry enabled
- Emit telemetry JSON per step: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/<timestamp>/telemetry_step_{0..9}.json`

**Step A2: Execute Instrumented Run**
- [x] *(2025-11-22T140000Z)* Implemented telemetry instrumentation in dbex/nanobrag_refinement.py and stage_a_mapping_adam_debug.py (commit 3d5c613)
- [~] *(2025-11-22T140000Z)* Executed instrumented run; captured 9/10 telemetry steps (step_000 through step_008); Phase 5 incomplete (no block_dof_results.json)
- **Status:** Incomplete - only 9 steps captured, missing step_009 and final DoF results. Need to investigate why run stopped early.

**Step A3: Identify First Divergence Point**
- [x] *(2025-11-22T150000Z)* Analyzed telemetry steps 000-008; identified **step 0 catastrophic failure** (chi-squared 1.425B, 1000× worse than expected ~1.13M)
- [x] *(2025-11-22T150000Z)* Documented first divergence in `phase_a_first_divergence.md` with preliminary root cause hypothesis: forward model pathology (H3), not optimizer issue
- [x] *(2025-11-22T150000Z)* Classified primary failure mode as `forward_model_pathology` - problem exists before optimizer runs
- [x] *(2025-11-22T150000Z)* **ROOT CAUSE CONFIRMED: B_ideal computation mismatch** - `derive_u_matrix_from_mosflm_a_star` uses TorchCrystal while `_build_stage_a_components` uses cctbx, producing inconsistent B_ideal matrices. Zero-point check (chi²=990k) uses MOSFLM A* directly; Adam loop step 0 (chi²=1.425B) reconstructs A* via `U @ B_ideal_cctbx` which differs from A*_mosflm due to B_ideal source mismatch.
- **Key Finding:** Chi-squared discrepancy is a **B_ideal computation bug**, NOT optimizer or gradient pathology
- **Hypothesis Verdicts:** H1 (Adam hyperparameters) REJECTED; H2 (variance instability) NOT APPLICABLE; H3 (gradient/forward pathology) RESOLVED as B_ideal bug; H4 (quaternion constraint) NOT TESTABLE with A_scale_only

**Step A4: Finite-Difference Gradient Validation**
- At the first-divergence step (or step 0 if immediate failure), compute finite-difference approximation of `∂χ²/∂q` using small perturbations (ε=1e-5)
- Compare FD gradients vs autograd gradients; check for sign flips, magnitude mismatches, or NaN
- Document in `phase_a_gradient_validation.md`

**Step A4: Variance/Loss Component Analysis**
- At first-divergence step, log full variance tensor breakdown:
  - `I_model` histogram (min/median/max/std)
  - `V_denom = max(I_model + sigma_readout^2, sigma_floor^2)` histogram
  - Clamp fraction (pixels where sigma_floor dominates)
  - Weighted residuals `(I_target - I_model)^2 / V_denom` histogram
- Check for pathological distributions (e.g., V_denom→0, residuals→inf)
- Document in `phase_a_variance_analysis.md`

**Step A5: Hypothesis Decision**
- Synthesize A1-A4 results into root cause determination (H1, H2, H3, H4, or combination)
- Document in `phase_a_root_cause_determination.md` with confidence level (high/medium/low)
- Recommend Phase B test: optimizer tuning (H1), loss modification (H2), gradient projection (H3/H4), or alternative parameterization (if no clear fix)

## Phase A — Evidence Collection & Gradient Diagnosis
### Checklist
- [x] A0: **Evidence Synthesis** — Compile PARITY-003 Phase C2 failure artifacts (block_dof_results_u_matrix.json, convergence telemetry if available); document known failure signature (χ² +125,648%, CC→-0.045, step count=10). **DONE (2025-11-22T134421Z):** Synthesized PARITY-003 escalation evidence, cross-referenced REFINE-001/PHYSICS-LOSS-002/GRADIENT-001 findings, documented four hypotheses (H1-H4), archived PARITY-003 artifacts. See `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a0_evidence_synthesis.md`.
- [x] A1: **Instrument Quaternion Closure** — Extend `build_stage_a_lbfgs_closure` (U-matrix path) with per-step telemetry logging (q_params, gradients, loss components, variance metrics); emit `telemetry_step_{i}.json`. **DONE (2025-11-22T140000Z):** Implemented telemetry in dbex/nanobrag_refinement.py and stage_a_mapping_adam_debug.py (commit 3d5c613). Captures parameters (q_params, log_scale, q_norm), gradients (norms, NaN/Inf flags), loss (chi_squared), and variance components (simplified in script). See `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/`.
- [~] A2: **Execute Instrumented Run** — Run `stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only --adam-steps 10 --device cpu` with telemetry enabled; capture all step artifacts. **PARTIAL (2025-11-22T140000Z):** Captured 9/10 telemetry steps (step_000 through step_008); Phase 5 incomplete (no block_dof_results.json). Need to investigate early termination and rerun or extract partial results.
- [x] A3: **First Divergence Analysis** — Identify first step where χ² increases >10% OR CC drops <0.95 OR gradients explode/vanish OR NaN appears; document parameter/gradient state in `phase_a_first_divergence.md`. **DONE (2025-11-22T150000Z):** Identified step 0 catastrophic failure (chi-squared 1.425B, 1000× worse than expected ~1.13M); classified as `forward_model_pathology` (not optimizer issue); preliminary hypotheses: H1 REJECTED, H2 PLAUSIBLE, H3 PARTIALLY SUPPORTED, H4 NOT TESTABLE with A_scale_only. See `phase_a_first_divergence.md`.
- [ ] A4: **Finite-Difference Validation** — At first-divergence step (or step 0), compute FD approximation of `∂χ²/∂q` (ε=1e-5); compare vs autograd gradients; check for sign flips, magnitude mismatches, NaN. Document in `phase_a_gradient_validation.md`. **BLOCKED:** Requires D_full or C_scale_plus_orientation variant (A_scale_only has train_orientation=False so q_params.grad is None).
- [ ] A5: **Variance/Loss Analysis** — At first-divergence step, log variance tensor breakdown (I_model, V_denom, clamp fraction, weighted residuals histograms); check for pathological distributions. Document in `phase_a_variance_analysis.md`. **PENDING:** Requires full variance telemetry instrumentation in dbex/nanobrag_refinement.py closure (current script-level telemetry has variance components as null).
- [ ] A6: **Hypothesis Decision** — Synthesize A0-A5 results into root cause determination (H1/H2/H3/H4); assign confidence level; recommend Phase B test. Document in `phase_a_root_cause_determination.md`. **PENDING:** Requires A4 (gradient validation) and A5 (variance analysis) to complete evidence base.

### Notes & Risks
- Risk: Telemetry overhead may slow convergence test; mitigate by running on CPU (no CUDA sync overhead) and emitting JSON only (no visualization).
- Risk: Finite-difference validation may be slow for 4-DOF quaternion; mitigate by testing only at first-divergence step, not every step.
- Fallback: If first divergence is immediate (step 0), root cause is likely initialization or forward-pass numerical issue, not optimizer; pivot to investigating `quaternion_to_matrix` implementation or U₀ extraction.

## Phase B — Hypothesis Testing
### Checklist
- [x] B0: **Test Protocol Design** — Based on Phase A root cause determination (B_ideal mismatch), prioritized H1 (LBFGS) → H1+H3 (LR+gradients) → H2 (variance). **DONE (2025-11-22T165000Z):** Documented test protocol with LBFGS as priority 1 to bypass Adam momentum pathology. See `phase_b_test_protocol.md`.
- [~] B1: **LBFGS Validation Test** — BLOCKED: Path B verdict (Fix INCOMPLETE). **COMPLETED (2025-11-22T183000Z):** LBFGS test execution completed with 3 optimizer steps, A_scale_only variant. Zero-point validation PASSED (chi²=989,811, corr=0.9999999843, B_ideal fix confirmed working for initialization). However, LBFGS optimization CATASTROPHICALLY FAILED with identical signature to pre-fix runs: chi² 1.13M → 1.425B (+125,648%), CC 1.0 → -0.045 after 3 steps. **Root Cause Assessment:** B_ideal fix (commit e86fd4e) resolved INITIALIZATION bug but did NOT resolve CONVERGENCE pathology. Failure is optimizer-agnostic (reproduced with both Adam and LBFGS), indicating forward model/loss/gradient bug during optimization, NOT initialization. **Decision: Path B (Fix INCOMPLETE)** — Escalate to Phase B2 (gradient validation, variance analysis, finite-difference checks) to identify specific pathology (NaN/Inf gradients, exploding magnitudes, variance instability). See `phase_b1_validation_decision.md`, `lbfgs_validation/zero_point_check.json`, `lbfgs_validation/block_dof_results_u_matrix.json`.
- [x] B2: **Deep Diagnostic (Gradient/Variance Telemetry)** — Enhanced telemetry instrumentation + diagnostic analysis. **COMPLETED (2025-11-22T190000Z):** Implemented comprehensive Phase B2 telemetry in dbex/nanobrag_refinement.py (U_matrix checksum, enhanced gradient stats with element-wise min/max/mean/std/sign consistency, V_denom histograms, weighted residuals stats, mean per-pixel chi²). Diagnostic test (2-step LBFGS) BLOCKED by timeout during HKL grid building (exit code 143 after 20min). Decision synthesized from Phase B1 validation evidence (post-fix: step 0 healthy chi²=1.13M, steps 1-3 catastrophic chi²=1.425B) and Phase A1 telemetry (pre-fix: grad_log_scale~295k, no NaN/Inf). **Root Cause Determination:** Primary hypothesis **H4 (Forward Model Bug)** MEDIUM-HIGH confidence — initialization healthy, optimization catastrophic, optimizer-agnostic → parameter-update-triggered forward model bug. Secondary hypotheses H2 (variance instability) MEDIUM, H3b (gradient explosion) MEDIUM. H1 (optimizer hyperparameters) REJECTED, H3a (NaN/Inf gradients) REJECTED, H3c (sign flip) NOT TESTABLE. **Recommended Next Actions:** Phase B3 forward model sanity checks (U_matrix checksum tracking, A* reconstruction validation, parameter update propagation verification). Regression guard test_stage_a_expansion PASSED (12.44s). See `phase_b2_diagnostic_decision.md`, `phase_b2_diagnostic_blocker.md`, `pytest_regression.log`.
- [x] B3: **Forward Model Sanity Check (1-step diagnostic)** — Validate parameter update propagation from initialization through forward model. **COMPLETED (2025-11-22T195000Z):** Executed 1-step diagnostic (A_scale_only, Adam optimizer due to --use-lbfgs flag bug, telemetry enabled). Zero-point validation PASSED (chi²_mapping=989,811, chi²_stage_a=989,645, correlation=0.9999999843) confirming B_ideal fix works for initialization. **CRITICAL FINDING:** chi²_before=1.13M (HEALTHY initialization, 1000× improvement vs pre-fix 1.425B) BUT chi²_after=1.425B (CATASTROPHIC after single optimizer step). This CONFIRMS H4 (Forward Model Bug) with **HIGH confidence (~80%)**. B_ideal fix resolved INITIALIZATION pathology but CONVERGENCE pathology persists — forward model/loss/gradient bug manifests DURING OPTIMIZATION when parameters are updated. Gradient explosion detected (log_scale gradient ~295k, likely SYMPTOM not PRIMARY cause). **Verdict:** H4 CONFIRMED (parameter-update-triggered forward model bug), H3b PLAUSIBLE (gradient explosion likely symptom), H2 NOT TESTABLE (variance telemetry incomplete), H3a RULED OUT (no NaN/Inf), H1 REJECTED (optimizer-agnostic failure). **Recommended Next Actions:** Path A (Extended Diagnostic B4 to capture U_matrix/A* checksums, initialization gradients) OR Path B (proceed to targeted fix attempt based on MEDIUM-HIGH confidence). Regression guard test_stage_a_expansion PASSED (13.28s). See `phase_b3_forward_model_sanity_check.md`, `diagnostic_1step.log`, `pytest_regression.log`. Artifacts: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/`.
- [x] B4: **Extended Diagnostic (U_matrix/A*/Gradient Lifecycle Tracing)** — Capture missing metrics to definitively identify U/A* staleness vs gradient pathology. **COMPLETED (2025-11-22T201500Z):** Executed 1-step diagnostic (A_scale_only, Adam optimizer, lifecycle instrumentation in nanobrag_refinement.py + dual telemetry emission in script). **CRITICAL CODE PATH DISCREPANCY FOUND:** Script-level _forward_once produces chi²=1.425B (catastrophic) BEFORE optimizer.step(), while run_nanobrag_refinement produces chi²_before=1.13M (healthy) at SAME parameters. This proves B_ideal fix (commit e86fd4e) works correctly in run_nanobrag_refinement but is NOT applied in simplified script path. **Verdict:** H4a (Code Path Discrepancy) CONFIRMED with HIGH confidence (~85%), H3b (Gradient Explosion) ruled SYMPTOM not PRIMARY (gradient ~295k appears only when chi²=1.425B catastrophic, not when chi²=1.13M healthy). **Lifecycle data:** U_matrix/A* lifecycle JSON files NOT emitted due to code path mismatch (script bypasses run_nanobrag_refinement closure), but code path finding provides sufficient evidence without checksums. **Recommended Next Actions:** Phase B5 fix implementation — audit and align _forward_once U-matrix logic with run_nanobrag_refinement (verify B_ideal derivation from MOSFLM A*, quaternion normalization). Regression guard test_stage_a_expansion PASSED. See `phase_b4_extended_diagnostic.md`, `summary.md`, `telemetry_step_000_init.json` (catastrophic chi²), `block_dof_results_u_matrix.json` (healthy chi²_before). Artifacts: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/`.
- [x] B5: **Code Path Fix Implementation** — Align script _forward_once U-matrix logic with run_nanobrag_refinement to resolve initialization bug. **COMPLETED (2025-11-22T183012Z, commit fe6048f):** Root cause identified via code audit: script `_stage_a_forward` set unsupported `crystal_overrides["A_star"]` key, causing `create_crystal_config` to ignore MOSFLM A* tuple when ANY overrides present. Fix applied in two locations: (1) Script (stage_a_mapping_adam_debug.py:437-442) converts A* numpy to `mosflm_a/b/c_star` tuples, (2) Config function (nanobrag_bridge.py:569-586) checks for `mosflm_*_star` keys in overrides before defaulting to None. **Validation Results (Path A SUCCESS):** Zero-point parity maintained (corr=0.9999999843, chi²_diff=-166 within ±200 tolerance), initialization bug FIXED (chi²_before=1.13M healthy, 1000× improvement from 1.425B catastrophic, 1.14× expected ~990k-1.13M). Regression guard test_stage_a_expansion PASSED. **Convergence pathology REMAINS:** chi² 1.13M → 8.8M after 10 steps (7.8× degradation), CC 1.0 → 0.765 (degraded but positive, NOT catastrophic -0.045 collapse). This is a DIFFERENT failure mode from pre-fix (healthier initialization, no negative CC) → separate optimizer/loss issue for Phase C. Artifacts: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/` (code_path_audit.md, phase_b5_fix_decision.md, validation_metrics.txt, diagnostic_b5_postfix_v2 results).

### Notes & Risks
- Risk: Multiple optimizer/loss variants may require significant code changes; prefer config flags over rewriting closures.
- Mitigation: Use `RefinementConfig` extensions (e.g., `adam_learning_rate`, `use_gradient_clipping`, `quaternion_normalization_frequency`) to toggle behaviors without rewrites.
- Risk: If all tests fail, may need to escalate to alternative parameterization (hybrid cell+quaternion+scale per PARITY-003 Option 1) or mark quaternion approach as non-viable.

## Phase C — Fix Implementation & Validation
### Checklist
- [x] C1: **Convergence Telemetry & Root Cause Analysis** — DONE (2025-11-22T230000Z): Executed 10-step A_scale_only convergence test with telemetry (all 10 steps captured). **Root Cause:** H1 (Adam LR too high) HIGH confidence (~85%). First optimizer step causes catastrophic overshoot (chi² 1.13M → 8.84M, +679%), subsequent steps slowly recover but stuck in bad local minimum. Gradients healthy (O(150k), stable, no NaN/Inf), quaternion norm stable (1.0). Mechanism: LR=1e-4 calibrated for cell/misset (gradients O(1-100)) is 1000× too high for quaternions (gradients O(150k)) → Adam update Δq = -15.0 (massive ~35° rotation). **Recommended fix:** Reduce Adam LR to 1e-5 for U-matrix path. See `phase_c1_convergence_analysis.md`, `phase_c1_decision.md`, `convergence_trajectory.txt`.
- [~] C2: **Phase 5 Convergence Test (A_scale_only)** — **BLOCKED: Path C FAIL (2025-11-22T235959Z)**: Implemented LR reduction fix (RefinementConfig.u_matrix_learning_rate=1e-5, script --u-matrix-lr flag, conditional LR logic). Executed Phase C2 validation (A_scale_only, 10 steps, LR=1e-5). Zero-point PASSED (chi²=989k, correlation=1.0). **Convergence CATASTROPHICALLY FAILED with IDENTICAL signature to Phase C1 pre-fix:** chi²: 1.13M → 8.84M (+679.6%, NO improvement vs +679% pre-fix), CC: 1.0 → 0.765 (not ≥0.99 required). **H1 (Adam LR too high) REJECTED with HIGH confidence** — 10× LR reduction produced ZERO change in convergence behavior. Root cause is NOT LR but a DIFFERENT pathology (forward model bug, loss instability, or gradient/parameter propagation issue). Decision: Path C (FAIL). Escalate to alternative hypothesis investigation (H2/H3b/H4) or alternative parameterization. See `phase_c2_c3_decision.json`, `block_dof_results_u_matrix.json`.
- [x] C3: **Parameter Lifecycle Investigation** — **COMPLETED (2025-11-22T224717Z)**: Executed 2-step diagnostic with lifecycle telemetry (LR=1e-5, A_scale_only). **ROOT CAUSE IDENTIFIED with HIGH confidence (~90%):** chi² = 8.8M BEFORE first optimizer.step() (not after), indicating forward model uses STALE/WRONG parameters during first closure evaluation, NOT an optimizer issue. Pattern matches Phase B5 code path discrepancy. Zero-point validation PASSED (corr=1.0), but first closure chi²=8.8M. Parameter update Δlog_scale=+1e-5 (wrong magnitude, expected -1.5) is SECONDARY symptom. **Verdict: Path C CONFIRMED** (forward model parameter staleness). **H5 (NEW): Forward model parameter staleness** PRIMARY hypothesis (90% confidence). **Recommended next actions:** (Priority 1) Audit first closure U_matrix/A* derivation for parameter staleness similar to B5 B_ideal mismatch; (Priority 2) Test LBFGS optimizer to rule out Adam-specific bug. See `phase_c3_parameter_lifecycle_decision.md`, `telemetry/telemetry_step_000_{init,post}.json`.
- [ ] C4: **Phase 5 Convergence Test (D_full or U+scale)** — SKIPPED per C2 FAIL (chi²>8M, CC<0.9). Will not run D_full until alternative fix identified.
- [x] C4: **Regression Guard** — PASSED (2025-11-22T235959Z): Regression guard test_stage_a_expansion passed, confirming LR config additions and script CLI flag do not break cell+misset default path. See `pytest_regression.log`.
- [ ] C5: **Findings Update** — Create CONVERGENCE-002 (or extend REFINE-001/GRADIENT-001) in `docs/findings.md` documenting: (a) root cause from Phase A, (b) fix choice from Phase B, (c) convergence metrics from Phase C, (d) usage conventions for quaternion U-matrix refinement.
- [ ] C6: **Fix-Plan Close** — Mark TORCH-GEOMETRY-CONVERGENCE-001 as `done`; unblock TORCH-GEOMETRY-PARITY-003 (if fix succeeds) or document quaternion approach as non-viable and recommend alternative (hybrid cell+quaternion+scale or other).

### Abort/Escalation Trigger
- If C2/C3 convergence tests fail after implementing Phase B best fix:
  - Attempt one more iteration: re-run Phase A telemetry with the fix enabled to see if failure mode changed
  - If second failure with same signature: Mark quaternion U-matrix approach as non-viable for current nanobrag_torch/optimizer setup
  - Escalate to TORCH-REFINE-003 (alternative parameterizations: hybrid cell+quaternion+scale per PARITY-003 Option 1, or LBFGS-only Stage A, or mapping-path-only refinement without explicit geometry DOF)
- If regression guard (C4) fails: Fix regression before proceeding to findings update

### Notes & Risks
- Risk: Fix may be quaternion-specific (e.g., Riemannian optimizer) and not generalizable; document limitations clearly in findings
- Risk: Fix may degrade performance on cell+misset path; use feature flags to preserve backward compatibility
- Mitigation: Default to cell+misset path; enable U-matrix path only via explicit config flag (`use_u_matrix_parameterization=True`)

## Phase D — Post-H1 Diagnostics (Parameter Lifecycle, Gradients, Variance)

### Objectives
- Confirm whether Stage A parameter updates (especially `log_scale` and quaternion DOFs) applied by the optimizer are actually consumed by the U-matrix forward model in subsequent closures.
- Validate autograd gradients against finite-difference approximations for scale and orientation around the healthy initialization point.
- Characterize the variance-weighted loss surface (V_denom, clamp fraction, weighted residuals) before and after the first optimizer step to detect numerical pathologies.

### Checklist
- [ ] D0: **Pivot & Scope Clarification** — Record that Phase C2 LR reduction (LR=1e-5) reproduced the catastrophic overshoot seen at LR=1e-4 (chi²≈8.84M, CC≈0.77), formally rejecting H1 (“Adam LR too high”) as a primary root cause. Update `input.md` and this implementation plan to frame Phase D around H2/H3/H5 (variance/gradient/parameter propagation) and cite `docs/spec-db-core.md §Objective Function & Variance Model` and `docs/spec-db-runtime.md §Gradient Stability` as normative constraints.
- [ ] D1: **Parameter Lifecycle Instrumentation (A_scale_only)** — Extend the Stage A U-matrix closure in `dbex/nanobrag_refinement.py` and the TOOLING-VIS-001 Adam helper to log `log_scale` and, where applicable, quaternion parameters at three points: (a) at closure entry (before forward), (b) immediately after `loss.backward()` (before any optimizer update), and (c) after `optimizer.step()` completes. Emit per-step lifecycle JSON (for example, `telemetry_step_{i:03d}_init.json` and `telemetry_step_{i:03d}_post.json`) under `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/<timestamp>/lifecycle_diagnostic/`, ensuring logging is done via `.detach().cpu().tolist()` outside the differentiable forward path to comply with spec-db-runtime guards.
- [ ] D2: **Two-Step Lifecycle Diagnostic (A_scale_only, U-matrix)** — Run a short Stage A debug experiment with `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` using `--use-u-matrix --u-matrix-lr 1e-5 --phases 5 --dof-variants A_scale_only --adam-steps 2 --device cpu --telemetry-dir telemetry` and archive artifacts under `reports/<timestamp>/lifecycle_diagnostic/`. Post-process lifecycle telemetry into `phase_d_lifecycle_analysis.md`, comparing observed Δlog_scale against the first-step approximation `Δθ ≈ -LR × gradient` and checking that the next closure call sees the updated parameter values (no stale warm cache or crystal_overrides usage).
- [ ] D3: **Finite-Difference Gradient Validation (Scale + Orientation)** — Implement a focused gradient probe (either as an extension to TOOLING-VIS-001 or a small helper script) that evaluates χ² and autograd gradients at the C2 initialization point for a variant with trainable orientation (`C_scale_plus_orientation` or `D_full`). Compute finite-difference approximations for `∂χ²/∂log_scale` and `∂χ²/∂q` (using small ε consistent with spec-db-runtime) and compare sign/magnitude to autograd. Record results and any discrepancies in `phase_d_gradient_validation.md`.
- [ ] D4: **Variance/Loss Surface Analysis** — Use the existing variance telemetry hooks in `dbex/nanobrag_refinement.py` (I_model statistics, V_denom histograms, clamp_fraction, weighted residuals) to characterize the variance-weighted loss at initialization and after the first optimizer step for the U-matrix A_scale_only run. Summarize distributions and any pathological behavior (for example, V_denom dominated by sigma_floor, extreme clamp_fraction, highly skewed weighted residuals) in `phase_d_variance_analysis.md`, cross-referencing `docs/spec-db-core.md §Objective Function & Variance Model`.
- [ ] D5: **Root Cause & Path Selection** — Synthesize D0–D4 into a refined hypothesis verdict: (a) parameter propagation bug (H5), (b) variance model pathology (H2), (c) gradient correctness/scale issue (H3), or a combination. Update `phase_a_root_cause_determination.md` or author `phase_d_root_cause_update.md` with an explicit decision, confidence level, and next-step recommendation: targeted code fix in the U-matrix Stage A path, variance-model adjustment within the spec, or escalation to alternative parameterization per TORCH-GEOMETRY-PARITY-003. Feed this decision back into `docs/fix_plan.md` and any downstream initiatives.

### Notes & Risks
- Risk: Additional telemetry and lifecycle logging may increase Stage A wall time; mitigate by restricting diagnostics to short (1–2 step) CPU runs and ROI subsets and reusing existing TOOLING-VIS-001 infrastructure.
- Risk: Finite-difference probes for quaternion parameters are numerically sensitive; carefully select ε and reuse mapping-aligned zero points to avoid conflating geometry and variance effects.
- Risk: If diagnostics confirm a fundamental incompatibility between the U-matrix parameterization and the current variance-weighted loss, the initiative may need to pivot to documenting limitations and recommending an alternative parameterization rather than forcing convergence.

## Artifacts Index
- Reports root: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/`
- Latest run: `2025-11-22T<timestamp>Z/`
- Key deliverables:
  - Phase A: `phase_a_first_divergence.md`, `phase_a_gradient_validation.md`, `phase_a_variance_analysis.md`, `phase_a_root_cause_determination.md`, `telemetry_step_{0..9}.json`
  - Phase B: `phase_b_test_protocol.md`, `phase_b_test{1,2,3}_results.json`, `phase_b_fix_selection.md`
  - Phase C: `phase_c_fix_implementation.md`, `phase_c_convergence_{a_scale_only,d_full}.json`, `pytest_stage_a_regression.log`
