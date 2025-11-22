# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase A0 Evidence Synthesis

## Summary
Synthesize PARITY-003 Phase C2 failure artifacts to establish baseline evidence for quaternion U-matrix convergence pathology investigation.

## Mode
Docs

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
none — evidence-only (Phase A0 synthesis and A1 instrumentation planning)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/

## Do Now

**Checklist Items:** Phase A0 (evidence synthesis)

**Your Task (Evidence Synthesis Only — No Production Code):**

1. **Synthesize PARITY-003 Phase C2 Failure Evidence** (`phase_a0_evidence_synthesis.md`):
   - Read `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/decision.json`
   - Read `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/phase_c2_convergence_verification.json`
   - Read `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/block_dof_results_u_matrix.json`
   - Extract key failure metrics:
     * Parity: max_abs_diff, det(U)
     * A_scale_only convergence: initial/final χ², initial/final median CC, drift percent
     * Optimizer config: type (Adam), LR (1e-4), steps (10)
     * Failure mode classification (cc_collapse, chi2_explosion, gradient_pathology, etc.)
   - Document known constraints from PARITY-002/PARITY-003 evidence chain:
     * Perfect parity at zero deltas (3.469e-18)
     * Catastrophic failure NOT file-specific (reproduced with canonical refGeom.expt)
     * det(U)=1.0 per dxtbx audit (PARITY-003 Phase A1), det(U)=1.000565 per MOSFLM reconstruction (0.06% offset is nanobrag_torch/dxtbx parity artifact, NOT a convergence blocker)
   - Cross-reference relevant findings: REFINE-001 (LBFGS scale warm-start), PHYSICS-LOSS-002 (variance sigma-floor guard), GRADIENT-001 (autograd graph preservation)
   - Emit comprehensive Markdown summary under `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a0_evidence_synthesis.md` with sections:
     * **Failure Signature**: Exact metrics from PARITY-003 Phase C2
     * **Known Constraints**: Parity status, file-independence, det(U) analysis
     * **Relevant Findings**: REFINE-001, PHYSICS-LOSS-002, GRADIENT-001 with one-line applicability notes
     * **Hypothesis Space**: Four hypotheses from implementation.md (H1: Adam hyperparameters, H2: variance-weighted loss instability, H3: gradient pathology, H4: quaternion constraint handling)
     * **Recommended Next Steps**: Phase A1 (instrumentation) → A2 (execute instrumented run) → A3 (first divergence analysis)

2. **Draft Phase A1 Instrumentation Plan** (`phase_a1_instrumentation_plan.md`):
   - Based on implementation.md:145-190 (Phase A diagnostic protocol), outline exactly what telemetry to capture in `build_stage_a_lbfgs_closure` (U-matrix path):
     * Per-step parameter values: `q_params` (4-element quaternion), `log_scale`, `||q||` (quaternion norm)
     * Per-step gradient norms: `||∂L/∂q||`, `||∂L/∂log_scale||`, element-wise max/min gradients
     * Per-step loss components: total chi-squared, variance components (mean/median/max of I_model, V_denom), clamp fraction
     * Per-step forward metrics: median ROI CC (if available without full ROI scoring overhead)
   - Specify instrumentation injection points:
     * Closure location: `dbex/nanobrag_refinement.py:build_stage_a_lbfgs_closure` (~line 950-1150, U-matrix branch starting ~line 1000)
     * Telemetry emission: JSON per step to `reports/<timestamp>/telemetry_step_{0..9}.json`
   - Note constraints:
     * Must NOT mutate production code logic (telemetry is observation only)
     * Emit JSON only (no visualization overhead)
     * Run on CPU (--device cpu) to avoid CUDA sync overhead
   - Emit plan under `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a1_instrumentation_plan.md`

3. **Archive PARITY-003 Phase C2 Artifacts**:
   - Copy key PARITY-003 decision artifacts to CONVERGENCE-001 reports directory for reference:
     * `cp plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/decision.json plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/parity_003_decision.json`
     * `cp plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/phase_c2_convergence_verification.json plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/parity_003_phase_c2.json`
     * `cp plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/block_dof_results_u_matrix.json plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/parity_003_dof_results.json`

4. **Update CONVERGENCE-001 Implementation Plan Checklist**:
   - Mark Phase A0 checklist item as complete (implementation.md:130, checklist line "A0: Evidence Synthesis")
   - Add brief completion note with artifact paths

5. **Emit Summary**:
   - Write a concise summary to `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/summary.md` with:
     * What was accomplished (evidence synthesized, instrumentation plan drafted, artifacts archived)
     * Key findings (failure signature, hypothesis space)
     * Next actions (Phase A1 implementation → A2 instrumented run → A3 first-divergence analysis)

## How-To Map

**Evidence Synthesis:**
```bash
# Read PARITY-003 decision and failure artifacts
cat plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/decision.json
cat plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/phase_c2_convergence_verification.json
cat plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/block_dof_results_u_matrix.json

# Cross-reference findings
grep "REFINE-001\|PHYSICS-LOSS-002\|GRADIENT-001" docs/findings.md

# Emit phase_a0_evidence_synthesis.md with sections per Do Now #1
```

**Instrumentation Planning:**
```bash
# Review U-matrix closure implementation for injection points
grep -n "use_u_matrix_parameterization" dbex/nanobrag_refinement.py

# Draft phase_a1_instrumentation_plan.md with telemetry spec per Do Now #2
```

**Artifact Archival:**
```bash
# Copy PARITY-003 Phase C2 artifacts to CONVERGENCE-001 for reference
cp plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/decision.json \
   plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/parity_003_decision.json
cp plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/phase_c2_convergence_verification.json \
   plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/parity_003_phase_c2.json
cp plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/block_dof_results_u_matrix.json \
   plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/parity_003_dof_results.json
```

**Checklist Update:**
```bash
# Mark Phase A0 complete in implementation.md:130
# Add completion note with artifact paths
```

## Pitfalls To Avoid

1. **Do NOT implement production code changes** — This is a docs-only evidence synthesis loop per implementation floor rule (max one docs-only loop per focus, next must have production code task).
2. **Do NOT run tests** — Phase A0 is synthesis only; instrumented runs happen in Phase A2.
3. **Do NOT prescribe environment changes** — Environment is frozen per AGENTS.md:8.
4. **Comprehensive evidence extraction** — Ensure all four hypotheses (H1-H4) are addressable by the evidence you synthesize; if any hypothesis requires data not in PARITY-003 artifacts, note it as a gap for Phase A1 instrumentation.
5. **Cross-reference findings accurately** — REFINE-001, PHYSICS-LOSS-002, GRADIENT-001 are relevant to optimizer/loss/gradient pathologies; cite them with specific applicability notes (e.g., "REFINE-001: scale warm-start relevant if quaternion gradients also explode without bounds").
6. **Hypothesis space clarity** — Do NOT collapse the four hypotheses prematurely; Phase A evidence synthesis sets up Phase A1-A6 to test each systematically.
7. **Artifact completeness** — Ensure PARITY-003 artifacts are copied to CONVERGENCE-001 reports directory so future loops can reference them without cross-initiative navigation.
8. **Implementation plan hygiene** — Mark A0 complete in implementation.md checklist with brief note + artifact path (e.g., "✓ A0: Evidence synthesized, see plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a0_evidence_synthesis.md").

## If Blocked

If PARITY-003 Phase C2 artifacts are incomplete or missing critical metrics (e.g., parameter trajectories, gradient norms):
1. Document the gap in `phase_a0_evidence_synthesis.md` under "Evidence Gaps" section
2. Note that Phase A1 instrumentation MUST capture the missing data
3. Proceed to Phase A1 instrumentation planning without synthesizing unavailable data

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards): Relevant if quaternion U-matrix convergence involves scale DOF and gradients explode similar to REFINE-001 signature; monitor for log_scale gradient explosion.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Directly relevant — variance components (I_model, V_denom, clamp fraction) must be logged per-step in Phase A telemetry to diagnose if sigma-floor interaction causes numerical instability with quaternion parameterization.
- **GRADIENT-001** (autograd graph preservation, crystal_overrides): Relevant to ensure quaternion U-matrix closure preserves autograd graph correctly; check that quaternion normalization `q / ||q||` doesn't break gradient flow.
- No other findings in the knowledge base directly address quaternion parameterization convergence pathology.

## Pointers

- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence), docs/spec-db-runtime.md §Gradient stability, docs/spec-db-core.md §Variance Model
- **Architecture:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (full Phase A-C plan)
- **Escalation Source:** plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/decision.json (catastrophic failure decision)
- **Fix Plan:** docs/fix_plan.md line 40 (TORCH-GEOMETRY-CONVERGENCE-001 entry)
- **Testing:** No tests for Phase A0 evidence synthesis; Phase A2 will use `stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only`

## Next Up (Optional)

If you finish Phase A0 evidence synthesis and A1 instrumentation planning early:
- **Do NOT proceed to Phase A1 implementation** — Implementation floor rule requires next loop to have production code task.
- Instead, review `dbex/nanobrag_refinement.py:build_stage_a_lbfgs_closure` (~line 950-1150) to validate Phase A1 instrumentation injection points are feasible and document any implementation risks in `phase_a1_instrumentation_plan.md` (e.g., closure nesting complexity, tensor detachment requirements for JSON serialization).

## Doc Sync Plan

Not applicable (no tests added/renamed this loop).
