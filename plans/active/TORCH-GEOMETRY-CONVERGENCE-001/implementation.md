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

**Step A2: Identify First Divergence Point**
- Analyze telemetry to find first step where:
  - χ² increases dramatically (>10% from initial)
  - CC drops below 0.95
  - Gradients explode (norm >1e10) or vanish (norm <1e-10)
  - NaN/inf appears in loss or gradients
- Document first-divergence step and parameter/gradient values in `phase_a_first_divergence.md`

**Step A3: Finite-Difference Gradient Validation**
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
- [ ] A1: **Instrument Quaternion Closure** — Extend `build_stage_a_lbfgs_closure` (U-matrix path) with per-step telemetry logging (q_params, gradients, loss components, variance metrics); emit `telemetry_step_{i}.json`.
- [ ] A2: **Execute Instrumented Run** — Run `stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only --adam-steps 10 --device cpu` with telemetry enabled; capture all step artifacts.
- [ ] A3: **First Divergence Analysis** — Identify first step where χ² increases >10% OR CC drops <0.95 OR gradients explode/vanish OR NaN appears; document parameter/gradient state in `phase_a_first_divergence.md`.
- [ ] A4: **Finite-Difference Validation** — At first-divergence step (or step 0), compute FD approximation of `∂χ²/∂q` (ε=1e-5); compare vs autograd gradients; check for sign flips, magnitude mismatches, NaN. Document in `phase_a_gradient_validation.md`.
- [ ] A5: **Variance/Loss Analysis** — At first-divergence step, log variance tensor breakdown (I_model, V_denom, clamp fraction, weighted residuals histograms); check for pathological distributions. Document in `phase_a_variance_analysis.md`.
- [ ] A6: **Hypothesis Decision** — Synthesize A0-A5 results into root cause determination (H1/H2/H3/H4); assign confidence level; recommend Phase B test. Document in `phase_a_root_cause_determination.md`.

### Notes & Risks
- Risk: Telemetry overhead may slow convergence test; mitigate by running on CPU (no CUDA sync overhead) and emitting JSON only (no visualization).
- Risk: Finite-difference validation may be slow for 4-DOF quaternion; mitigate by testing only at first-divergence step, not every step.
- Fallback: If first divergence is immediate (step 0), root cause is likely initialization or forward-pass numerical issue, not optimizer; pivot to investigating `quaternion_to_matrix` implementation or U₀ extraction.

## Phase B — Hypothesis Testing
### Checklist
- [ ] B0: **Test Protocol Design** — Based on Phase A root cause determination, design 2-3 targeted tests (e.g., if H1: test LBFGS, lower LR, gradient clipping; if H2: test loss clamping, FP64; if H3/H4: test normalization frequency, Riemannian projection). Document in `phase_b_test_protocol.md`.
- [ ] B1: **Execute Test 1** — Implement and run first hypothesis test (e.g., LBFGS optimizer for A_scale_only with U-matrix); validate convergence metrics (CC ≥ 0.99, χ² stable). Emit `phase_b_test1_results.json`.
- [ ] B2: **Execute Test 2** — Implement and run second hypothesis test (e.g., Adam LR=1e-6 instead of 1e-4); validate convergence. Emit `phase_b_test2_results.json`.
- [ ] B3: **Execute Test 3 (Optional)** — If first two tests fail or are inconclusive, run third test (e.g., gradient clipping or FP64 precision). Emit `phase_b_test3_results.json`.
- [ ] B4: **Test Result Synthesis** — Compare test results; select best-performing fix (or combination); validate it achieves exit criteria thresholds. Document in `phase_b_fix_selection.md`.

### Notes & Risks
- Risk: Multiple optimizer/loss variants may require significant code changes; prefer config flags over rewriting closures.
- Mitigation: Use `RefinementConfig` extensions (e.g., `adam_learning_rate`, `use_gradient_clipping`, `quaternion_normalization_frequency`) to toggle behaviors without rewrites.
- Risk: If all tests fail, may need to escalate to alternative parameterization (hybrid cell+quaternion+scale per PARITY-003 Option 1) or mark quaternion approach as non-viable.

## Phase C — Fix Implementation & Validation
### Checklist
- [ ] C1: **Implement Chosen Fix** — Based on Phase B selection, implement fix in `dbex/nanobrag_refinement.py` (e.g., add LR tuning, gradient clipping, normalization projection, or optimizer switch for U-matrix path). Document changes in `phase_c_fix_implementation.md`.
- [ ] C2: **Phase 5 Convergence Test (A_scale_only)** — Run `stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only` with fix enabled; validate CC ≥ 0.99, χ² drift ≤ 0.5%. Emit `phase_c_convergence_a_scale_only.json`.
- [ ] C3: **Phase 5 Convergence Test (D_full or U+scale)** — Run D_full variant (or equivalent U-matrix+scale multi-DOF variant) with fix enabled; validate monotonic χ² improvement, no large CC collapses. Emit `phase_c_convergence_d_full.json`.
- [ ] C4: **Regression Guard** — Run `test_stage_a_expansion` to ensure cell+misset default path unaffected; validate U-matrix path if enabled by default. Emit `pytest_stage_a_regression.log`.
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

## Artifacts Index
- Reports root: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/`
- Latest run: `2025-11-22T<timestamp>Z/`
- Key deliverables:
  - Phase A: `phase_a_first_divergence.md`, `phase_a_gradient_validation.md`, `phase_a_variance_analysis.md`, `phase_a_root_cause_determination.md`, `telemetry_step_{0..9}.json`
  - Phase B: `phase_b_test_protocol.md`, `phase_b_test{1,2,3}_results.json`, `phase_b_fix_selection.md`
  - Phase C: `phase_c_fix_implementation.md`, `phase_c_convergence_{a_scale_only,d_full}.json`, `pytest_stage_a_regression.log`
