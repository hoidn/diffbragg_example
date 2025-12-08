**Status:** superseded (by TORCH-GEOMETRY-UB-REALIGN-001)
**Reason:** The det(U)≠1 issue discovered in PARITY-002 was bypassed by the incremental UB approach using dxtbx U₀/B₀ as baseline with quaternion ΔR increments.
**Date:** 2025-12-08

---

# Implementation Plan: TORCH-GEOMETRY-PARITY-003

## Initiative
- ID: TORCH-GEOMETRY-PARITY-003
- Title: Investigate det(U)≠1 Root Cause & Implement Hybrid Cell+U+Scale Parameterization
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md, docs/spec-db-core.md
- Status: pending

## Goals
- Investigate why `det(U₀)=1.000557` when deriving U from mapping MOSFLM A* via `U = A* @ inv(B_ideal)`.
- Determine if this 0.06% volume scaling is physical, a dxtbx calibration artifact, or implementation bug.
- Design and implement a hybrid parameterization that preserves mapping zero-point parity (<1e-6) while supporting convergent refinement.
- Restore Stage A convergence (CC ≥ 0.99, stable/improving χ²) for scale-only and full-DoF variants.

## Phases Overview
- Phase A — Root Cause Investigation: Audit dxtbx A*/cell relationship, validate det(U) computation, analyze MOSFLM calibration metadata.
- Phase B — Parameterization Design: Evaluate hybrid cell+U+scale factorization vs GL(3) vs quaternion+scale approaches; prototype gradient flow.
- Phase C — Implementation & Validation: Implement chosen parameterization, extend parity probes, validate Phase 5 convergence, update findings.

## Exit Criteria
1. Root cause of `det(U₀)=1.000557` is documented with evidence (dxtbx API audit, cell parameter measurements, or physical explanation).
2. Chosen parameterization achieves `max_abs_diff < 1e-6` A* parity at mapping zero point.
3. `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` Phase 5 with new parameterization shows:
   - A_scale_only: median ROI CC ≥ 0.99, χ² stable (≤0.5% drift) after 10 Adam steps
   - D_full (or equivalent variant): monotonic χ² improvement without large CC collapses
4. `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` regression guard passes.
5. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new selectors; `pytest --collect-only` logs saved under `plans/active/TORCH-GEOMETRY-PARITY-003/reports/<timestamp>/`.
6. Findings ledger updated with GEOMETRY-004 documenting parameterization choice, det(U) root cause, and convergence metrics.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md §Stage A — mapping zero-point invariant`
- [ ] **Spec Constraint:** `docs/spec-db-core.md §Geometry Mapping`
- [ ] **Spec Constraint:** `docs/spec-db-conformance.md (Mapping-Aligned Stage-A Initialization)`
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [TORCH-GEOMETRY-PARITY-003]`
- [ ] **Finding/Policy ID:** `GEOMETRY-001` (detector mapping)
- [ ] **Finding/Policy ID:** `GEOMETRY-002` (Euler inversion)
- [ ] **Finding/Policy ID:** `GEOMETRY-003` (B_ideal-based mapping misset) — to be superseded/extended
- [ ] **Finding/Policy ID:** `DXTBX-001` (dxtbx crystal API conventions)
- [ ] **Finding/Policy ID:** `REFINE-001` (LBFGS scale warm-start)
- [ ] **Escalation Source:** `TORCH-GEOMETRY-PARITY-002` decision.json (2025-11-22T120500Z) — Quaternion U-matrix failed catastrophically (CC→-0.045, χ²→1.43B) due to SO(3) constraint incompatible with mapping geometry

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md, docs/spec-db-core.md, docs/spec-db-conformance.md
- **Key Clauses:**
  - spec-db-workflow.md §Stage A: "Trainable (normative): Unit cell logs/angles, orientation (quaternion → XYZ), global scale."
  - spec-db-core.md §Geometry Mapping: Crystal orientation must reproduce MOSFLM A* injection at mapping zero point.
  - spec-db-conformance.md: Mapping-aligned initialization ensures explicit parameterization matches mapping geometry.

## Architecture / Interfaces

### Current State (GEOMETRY-003 + PARITY-002 Failure)
- Cell+misset parameterization: Cannot express 1.37e-3 symmetric strain → 24.5% χ² gap at zero
- Quaternion U-matrix: Achieves perfect parity (3.5e-18) with raw U, but `det(U₀)=1.000557` → SO(3) projection loses 0.06% volume scaling → parity degrades to ~4e-05 → convergence catastrophically fails (CC→-0.045)

### Root Cause Hypotheses

1. **H1: dxtbx A*/cell inconsistency** (DXTBX-001 extension)
   - `crystal.get_A()` may embed isotropic scale factor not reflected in `crystal.get_unit_cell()` parameters
   - Possible calibration artifact from upstream processing (MOSFLM, DIALS indexing)
   - Test: Compare `det(A*)` vs `1/det(B_ideal)` where `B_ideal = reciprocal_matrix_from_unit_cell(crystal.get_unit_cell())`

2. **H2: Physical volume scaling**
   - Crystal may have undergone thermal expansion, pressure, or radiation damage relative to reference cell
   - Small isotropic strain is physical but not representable as cell+misset decomposition
   - Test: Check experiment metadata for environmental conditions

3. **H3: Numerical precision in B_ideal derivation**
   - `cctbx.uctbx.unit_cell(...).fractionalization_matrix()` roundtrip may introduce small errors
   - Test: Validate `B_ideal` computation against direct dxtbx `crystal.get_B()` (if available)

### Proposed Parameterizations (Evaluation Phase B)

**Option 1: Hybrid Cell+Quaternion+Scale (Recommended)**
- Factor: `A* = s · quaternion_to_matrix(q) @ diag(a, b, c) @ angles_matrix(α, β, γ)`
- Where:
  - `s`: isotropic scale (1-DOF, absorbs det offset)
  - `q`: quaternion (4-DOF with unit norm constraint) → SO(3) rotation
  - `(a, b, c, α, β, γ)`: unit cell (6-DOF, same as current)
- Initialization: Extract `s₀ = det(U₀)^(1/3)`, `q₀ = matrix_to_quaternion(U₀ / s₀)`
- Gradient flow: Isotropic scale decouples from rotational DOF, may improve conditioning
- Risk: 7-DOF for orientation (q + s) is redundant with 6-DOF cell; need to validate gradient interaction

**Option 2: Quaternion+Anisotropic Scale**
- Factor: `A* = quaternion_to_matrix(q) @ diag(s_a, s_b, s_c) @ B_ref`
- Where:
  - `q`: quaternion (4-DOF) → SO(3) rotation
  - `(s_a, s_b, s_c)`: anisotropic scale (3-DOF)
  - `B_ref`: fixed reference B-matrix from nominal cell
- Initialization: Extract scale via SVD of U₀
- Risk: 7-DOF coupling, potential overfitting

**Option 3: Direct GL(3) with Regularization**
- Parameterize full 9-DOF A* with soft constraints (determinant penalty, orthogonality penalty)
- Highest expressivity but no guarantee of physical interpretation
- Risk: Overfitting, non-physical solutions

**Decision Criteria:**
- Must achieve <1e-6 parity at zero deltas
- Must converge (CC ≥ 0.99, χ² stable/improving) in Phase 5 tests
- Prefer minimal DOF increase over GEOMETRY-003 baseline
- Prefer interpretable physical parameters

### Boundary Definitions
- `dbex/nanobrag_bridge.py`: Add helpers for hybrid parameterization (`derive_isotropic_scale_from_u`, `factorize_u_with_scale`)
- `dbex/nanobrag_refinement.py`: Extend `RefinementConfig` with `use_hybrid_u_parameterization` flag and `isotropic_scale_mode` option
- `build_stage_a_lbfgs_closure`: Branch on parameterization mode; hybrid path applies `s · quaternion_to_matrix(q) @ cell_matrix`

## Context Priming (read before edits)
- Primary docs/specs to re-read:
  - `docs/spec-db-core.md` §Geometry Mapping
  - `docs/spec-db-workflow.md` §Stage A trainable parameters
  - `docs/dxtbx_api.md` (crystal API conventions)
  - `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase_c1_parity_failure_diagnosis.md`
  - `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/phase_c2_c3_decision.json`
- Required findings/case law:
  - `GEOMETRY-001` (detector mapping), `GEOMETRY-002` (Euler inversion), `GEOMETRY-003` (B_ideal misset)
  - `DXTBX-001` (dxtbx crystal API)
- Related telemetry/attempts:
  - TORCH-REFINE-002E: All DoF variants degraded due to 1.37e-3 symmetric strain
  - TORCH-GEOMETRY-PARITY-002: Quaternion U-matrix perfect parity (raw) but catastrophic convergence failure after SO(3) projection

## Phase A — Root Cause Investigation
### Checklist
- [ ] A0: **Evidence Synthesis** — Compile det(U) measurements from PARITY-002 artifacts; document known facts (det=1.000557, parity=3.5e-18 raw, parity=~4e-05 quaternion).
- [ ] A1: **dxtbx A*/cell Audit** — Write analysis script to extract `crystal.get_A()`, `crystal.get_unit_cell()`, compute `B_ideal = reciprocal_matrix_from_unit_cell(cell)`, validate `det(A*)` vs `1/det(B_ideal)`, and check if dxtbx has `crystal.get_B()` API. Compare against mapping zero-point U-matrix.
- [ ] A2: **Metadata Review** — Inspect experiment JSON/pickle for calibration flags, processing history, environmental metadata (temperature, pressure). Check if MOSFLM or DIALS indexing applied isotropic scale correction.
- [ ] A3: **Numerical Precision Test** — Validate cctbx fractionalization_matrix roundtrip: `cell → B_ideal → cell'` and measure error. Confirm det(U) computation is numerically stable.
- [ ] A4: **Hypothesis Decision** — Synthesize A0-A3 results into root cause determination (H1, H2, H3, or combination). Document in `phase_a_root_cause_determination.md`.

### Notes & Risks
- Risk: dxtbx may not expose sufficient introspection to distinguish H1 vs H2 without deep MOSFLM/DIALS source audit
- Fallback: If root cause remains ambiguous, document as "empirical det offset" and proceed to parameterization design

## Phase B — Parameterization Design & Prototyping
### Checklist
- [ ] B0: **Design Evaluation Matrix** — Document Options 1-3 (hybrid cell+q+s, q+aniso scale, GL(3)) with DOF count, initialization formula, gradient flow sketch, physical interpretation. Reference phase_a_root_cause_determination.md findings.
- [ ] B1: **Prototype Isotropic Scale Extraction** — Implement `derive_isotropic_scale_from_u(U) -> s` using `s = det(U)^(1/3)` or SVD-based method; validate on mapping U₀ (expect s₀≈1.000186).
- [ ] B2: **Prototype Hybrid Factorization** — Implement `factorize_u_with_scale(U, B_ideal) -> (s, q)` that extracts isotropic scale and quaternion from raw U; validate `s · quaternion_to_matrix(q) @ B_ideal ≈ A*` to <1e-12.
- [ ] B3: **Gradient Flow Analysis** — Sketch Jacobian for `A*(s, q, cell) = s · R(q) @ cell_matrix(a,b,c,α,β,γ)`; identify potential coupling between s and cell parameters; document conditioning concerns.
- [ ] B4: **Parameterization Decision** — Select Option 1, 2, or 3 based on parity validation, DOF efficiency, and gradient analysis. Document rationale in `phase_b_parameterization_choice.md`.

### Notes & Risks
- Risk: 7-DOF (q + s) may redundantly encode information already in 6-DOF cell, creating rank-deficient Hessian
- Mitigation: Consider fixing one DOF (e.g., always refine `s`, disable one cell length) or use log-scale for s to improve conditioning
- Risk: scipy Rotation API may not support batched/differentiable quaternion ops; may need PyTorch-native implementation
- Mitigation: Existing `quaternion_to_matrix` uses scipy only for initialization; closure uses PyTorch matrix ops (already differentiable)

## Phase C — Implementation & Validation
### Checklist
- [ ] C1: **Implement Hybrid Initialization** — Extend `build_mapping_stage_a_context` to extract `s₀` and `q₀` from mapping A* via Phase B helpers; add `isotropic_scale_params` trainable tensor.
- [ ] C2: **Implement Hybrid Closure** — Update `build_stage_a_lbfgs_closure` to apply `A* = isotropic_scale * quaternion_to_matrix(q_params) @ cell_matrix` when `use_hybrid_u_parameterization=True`.
- [ ] C3: **Extend Parity Probe** — Update `probe_crystal_matrix_parity.py` with `--use-hybrid-u` flag; validate parity <1e-6 at zero deltas with hybrid parameterization.
- [ ] C4: **Phase 5 Convergence Test (A_scale_only)** — Run `stage_a_mapping_adam_debug.py --use-hybrid-u --phases 5 --dof-variants A_scale_only --adam-steps 10`; validate CC ≥ 0.99, χ² drift ≤ 0.5%.
- [ ] C5: **Phase 5 Convergence Test (D_full)** — Run D_full variant with hybrid parameterization; validate monotonic χ² improvement, no large CC collapses.
- [ ] C6: **Regression Guard** — Run `test_stage_a_expansion` to ensure cell+misset default path unaffected; validate hybrid path if enabled by default.
- [ ] C7: **Findings Update** — Create GEOMETRY-004 in `docs/findings.md` documenting: (a) det(U) root cause from Phase A, (b) hybrid parameterization choice from Phase B, (c) convergence metrics from Phase C, (d) usage conventions for future Stage A refinement.

### Abort/Escalation Trigger
- If C3 parity fails (>1e-6): Re-examine Phase B factorization math; check for implementation bugs in scale extraction or quaternion conversion.
- If C4/C5 convergence fails (CC < 0.99 OR χ² drift > 0.5% for two consecutive attempts):
  - Attempt gradient flow debugging (check for NaN, inf, or extreme magnitudes in `isotropic_scale_params.grad`)
  - If gradients are pathological: Pivot to Option 3 (GL(3) with regularization) or mark blocked and escalate to TORCH-REFINE-003 (convergence stability initiative)

### Notes & Risks
- Risk: Isotropic scale DOF may absorb variance that should be in cell parameters, leading to unphysical parameter estimates
- Mitigation: Monitor per-parameter gradient norms and validate scale remains close to 1.0 (within ±1%) during refinement
- Risk: Hybrid parameterization increases code complexity; must maintain backward compatibility with GEOMETRY-003 cell+misset path
- Mitigation: Use feature flag (`use_hybrid_u_parameterization`) with default=False; extensive regression testing

## Artifacts Index
- Reports root: `plans/active/TORCH-GEOMETRY-PARITY-003/reports/`
- Latest run: `2025-11-22T121500Z/`
- Key deliverables:
  - Phase A: `phase_a_root_cause_determination.md`, `dxtbx_a_star_cell_audit.json`
  - Phase B: `phase_b_parameterization_choice.md`, `gradient_flow_analysis.md`
  - Phase C: `crystal_matrix_parity.json`, `phase_c_decision.json`, `phase_5_convergence_hybrid_u.json`
