# Implementation Plan: TORCH-GEOMETRY-PARITY-002

## Initiative
- ID: TORCH-GEOMETRY-PARITY-002
- Title: Direct U-Matrix Parameterization for Stage A Geometry Refinement
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md
- Status: pending

## Goals
- Eliminate the 1.37e-3 symmetric strain component blocking Stage A refinement convergence at the mapping zero point.
- Enable Stage A to directly refine the 9-DOF crystal orientation matrix (U-matrix) or equivalent 3×3 rotation representation without the cell+misset decomposition.
- Achieve <1e-6 A* parity between mapping MOSFLM injection and explicit U-matrix parameterization at zero deltas.
- Restore convergent refinement behavior (CC ≥ 0.99, stable/improving χ²) for scale-only and full-DoF variants starting from the mapping zero point.

## Phases Overview
- Phase A — Analysis & Design: Review TORCH-REFINE-002E evidence, analyze current parameterization limitations, survey alternative U-matrix representations (quaternion, axis-angle, SO(3) exponential map), and design the minimal API changes required.
- Phase B — Implementation: Add U-matrix direct parameterization support to Stage A, implement proper SO(3) manifold constraints, wire into the refine closure, and update parity probes.
- Phase C — Validation & Integration: Re-run parity tests expecting <1e-6 gap, validate Phase 5 convergence (scale-only + full-DoF), ensure Stage A expansion smoke remains green, update findings/docs.

## Exit Criteria
1. `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py` extended with U-matrix path reports A* parity `max_abs_diff < 1e-6` when using direct U-matrix parameterization (no cell+misset decomposition).
2. `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` Phase 5 with U-matrix parameterization shows:
   - A_scale_only: median ROI CC ≥ 0.99, χ² stable (≤0.5% drift) after 10 Adam steps
   - D_full (or equivalent U-matrix+scale variant): monotonic χ² improvement without large CC collapses
3. `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` regression guard passes with U-matrix path enabled.
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new selectors; `pytest --collect-only` logs saved under `plans/active/TORCH-GEOMETRY-PARITY-002/reports/<timestamp>/`.
5. Findings ledger updated with new GEOMETRY-004 (or extension to GEOMETRY-003) documenting U-matrix parameterization conventions and SO(3) manifold handling.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md` §Stage A — mapping zero-point invariant
- [ ] **Spec Constraint:** `docs/spec-db-core.md` §Geometry Mapping
- [ ] **Spec Constraint:** `docs/spec-db-conformance.md` (Mapping-Aligned Stage-A Initialization)
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [TORCH-GEOMETRY-PARITY-002]`
- [ ] **Finding/Policy ID:** `GEOMETRY-001` (detector mapping)
- [ ] **Finding/Policy ID:** `GEOMETRY-002` (Euler inversion)
- [ ] **Finding/Policy ID:** `GEOMETRY-003` (B_ideal-based mapping misset) — to be superseded/extended
- [ ] **Finding/Policy ID:** `REFINE-001` (LBFGS scale warm-start)
- [ ] **Escalation Source:** `TORCH-REFINE-002E` decision.json (2025-11-22T120000Z) — Phase C1 validation confirmed all DoF variants degrade from mapping zero due to 1.37e-3 symmetric strain in cell+misset parameterization

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md, docs/spec-db-core.md
- **Key Clauses:**
  - spec-db-workflow.md §Stage A: "Trainable (normative): Unit cell logs/angles, orientation (quaternion → XYZ), global scale."
  - spec-db-core.md §Geometry Mapping: Crystal orientation must reproduce MOSFLM A* injection at mapping zero point.
  - spec-db-conformance.md: Mapping-aligned initialization ensures explicit parameterization matches mapping geometry.

## Architecture / Interfaces

### Current State (GEOMETRY-003, cell+misset)
- Stage A parameterizes crystal orientation as:
  - `cell_logs`: 3-DOF (log a, log b, log c)
  - `angle_raws`: 3-DOF (bounded α, β, γ via wrapped transform)
  - `orientation_vec`: 3-DOF (XYZ Euler angles for additional misset on top of baseline)
- Baseline misset derived from `U = A* · B_ideal^{-1}` projected to proper rotation, then inverted to XYZ Euler
- **Problem:** This decomposition cannot express the 1.37e-3 symmetric strain embedded in the mapping MOSFLM A*, causing 24.5% χ² gap at zero deltas and blocking convergence.

### Proposed State (GEOMETRY-004, U-matrix direct)
- Stage A offers **alternative parameterization** (opt-in via crystal_overrides or flag):
  - `u_params`: 3-DOF or 4-DOF SO(3) representation (quaternion preferred, or axis-angle, or Lie algebra)
  - `cell_logs`: 3-DOF (unchanged)
  - `angle_raws`: 3-DOF (unchanged)
  - `log_scale`: 1-DOF (unchanged)
- At zero deltas, `u_params → U_matrix` exactly reproduces the MOSFLM A* injected by `crystal_overrides` (no decomposition via B_ideal)
- U-matrix updates applied directly to `crystal_overrides['A_star']` without round-tripping through Euler angles

### Key Data Types / Protocols
- `CrystalConfig` from nanobrag_torch: accepts `A_star` (3×3 reciprocal matrix) via `crystal_overrides`
- New: `UMatrixParams` dataclass or dict with `{quaternion: torch.Tensor[4], cell_logs: torch.Tensor[3], angle_raws: torch.Tensor[3]}`
- Constraints: Quaternion normalization (‖q‖=1), SO(3) projection for numerical stability

### Boundary Definitions
- `dbex/nanobrag_bridge.py`: Add `derive_u_matrix_from_mosflm_a_star(A_star, cell)` helper to extract baseline U-matrix
- `dbex/nanobrag_refinement.py`: Extend `StageAContext` with `use_u_matrix_parameterization: bool` flag
- `build_stage_a_lbfgs_closure`: Branch on parameterization mode; U-matrix path skips `compute_baseline_misset_deg` and directly applies quaternion → rotation matrix → A*

### Sequence Sketch (Happy Path, U-matrix mode)
1. `build_mapping_stage_a_context` ingests MOSFLM A* from mapping
2. `derive_u_matrix_from_mosflm_a_star` extracts U₀ = A* · B_ideal^{-1} (no projection, preserve strain)
3. Convert U₀ to quaternion q₀ via matrix_to_quaternion (scipy or PyTorch)
4. Initialize trainable params: `q = q₀.clone().requires_grad_()` (4-DOF)
5. LBFGS closure:
   - Normalize q: `q_norm = q / torch.norm(q)`
   - Convert to rotation matrix: `U = quaternion_to_matrix(q_norm)`
   - Recompute A*: `A_new = U @ B_ideal_reciprocal`
   - Update `crystal_overrides['A_star']` with A_new
   - Forward pass, compute χ², backward, return loss
6. After convergence, extract final U from quaternion, log deltas if needed

### Data-Flow Notes
- Input: MOSFLM A* (3×3 numpy array from dxtbx)
- Intermediate: quaternion q (torch.Tensor[4], GPU/CPU)
- Output: Updated A* via U @ B_ideal_reciprocal (3×3 torch.Tensor)
- Parity artifacts: JSON with {q_initial, q_final, A_star_parity_error, max_abs_diff}

## Context Priming (read before edits)
- **Primary docs/specs:**
  - `docs/spec-db-workflow.md` §Stage A (orientation parameterization clause)
  - `docs/spec-db-core.md` §Geometry Mapping + Variance Model
  - `docs/spec-db-conformance.md` (mapping-aligned initialization)
- **Required findings:**
  - GEOMETRY-001, GEOMETRY-002, GEOMETRY-003 (current baseline misset path)
  - REFINE-001 (LBFGS scale warm-start pattern to replicate for U-matrix)
- **Related telemetry/attempts:**
  - `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/decision.json` (escalation trigger)
  - `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json` (Phase A0 strain decomposition)
  - `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json` (Phase B1 massive gradients at zero)
  - `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json` (Phase A3 24.5% χ² gap)

## Abort/Escalation Trigger
- If quaternion parameterization still shows >1e-6 A* parity gap after Phase B implementation, escalate to TORCH-GEOMETRY-PARITY-003 investigating numerical precision limits or MOSFLM A* injection bugs.
- If Phase C validation shows convergence degradation despite <1e-6 parity, pivot to optimizer/learning-rate sensitivity analysis (TORCH-REFINE-003).

## Phase A — Analysis & Design

### Hypothesis
The 1.37e-3 symmetric strain component in `log_u_symmetric` (from Phase A0 extended probe) originates from the cell+misset decomposition enforcing `U = proper_rotation(A* · B_ideal^{-1})`. The projection to SO(3) discards the strain embedded in MOSFLM A*, creating a fundamentally different crystal orientation. Direct U-matrix parameterization (quaternion or axis-angle) will preserve the mapping geometry exactly, eliminating the strain gap.

### Checklist
- [ ] A0: **Evidence synthesis** — Re-read TORCH-REFINE-002E artifacts (Phase A0/A2/A3/B1/C1) and confirm the root cause is cell+misset decomposition, not simulator parity or loss function bugs. Document the causal chain: MOSFLM A* → GEOMETRY-003 decomposition → symmetric strain → 24.5% χ² gap → convergence failure. (Galph, artifact: `phase_a0_evidence_synthesis.md`)
- [ ] A1: **SO(3) parameterization survey** — Research and document 3 candidate U-matrix representations: (1) quaternion (4-param, unit norm constraint), (2) axis-angle (3-param, compact but gimbal lock near θ=π), (3) Lie algebra so(3) exponential map (3-param, local chart). Compare: gradient flow quality, numerical stability, PyTorch ops availability. Recommend one for Phase B. (Galph, artifact: `so3_parameterization_survey.md`)
- [ ] A2: **API design** — Draft the minimal API changes required to add U-matrix mode to Stage A:
  - New `use_u_matrix_parameterization: bool` flag in `RefinementConfig`
  - `derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray, cell: CellParams) -> np.ndarray[3,3]` helper in `nanobrag_bridge.py`
  - Extend `build_stage_a_lbfg_closure` with branching logic (if use_u_matrix: {...} else: {...existing cell+misset path...})
  - Document the zero-point initialization contract and parity expectations
  (Galph, artifact: `api_design_u_matrix.md`)
- [ ] A3: **Risk analysis** — Identify risks: quaternion normalization drift, SO(3) projection numerical errors, interaction with existing scale/cell parameterizations, backward compatibility for cell+misset users. Document mitigation strategies. (Galph, artifact: `phase_a_risks.md`)

### Dependency Analysis
- **Touched Modules:**
  - `dbex/nanobrag_bridge.py` (new helper: `derive_u_matrix_from_mosflm_a_star`)
  - `dbex/nanobrag_refinement.py` (`build_mapping_stage_a_context`, `build_stage_a_lbfgs_closure`)
  - `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py` (extend with U-matrix path)
  - `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (add `--use-u-matrix` flag)
- **Circular Import Risks:** None — U-matrix helpers are self-contained geometry utilities
- **State Migration:** Existing GEOMETRY-003 cell+misset path remains default; U-matrix mode is opt-in via config flag

### Notes & Risks
- **Risk 1:** Quaternion normalization drift during LBFGS updates. **Mitigation:** Normalize quaternion every closure call before converting to rotation matrix.
- **Risk 2:** Gimbal lock or singularities in axis-angle near θ=π. **Mitigation:** Prefer quaternion (no gimbal lock) or Lie algebra (local chart only).
- **Risk 3:** Interaction between U-matrix and cell/angle parameterizations if both are trainable. **Mitigation:** Phase B validates U-matrix+scale+cell combo; if ill-conditioned, document and gate.

## Phase B — Implementation

### Checklist
- [ ] B1: **U-matrix helper** — Implement `derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray, cell: CellParams) -> np.ndarray[3,3]` in `dbex/nanobrag_bridge.py`. Extract B_ideal from cell, compute `U = A* @ inv(B_ideal_reciprocal)`, return U (no projection to SO(3) at initialization). Add docstring citing GEOMETRY-004. (Ralph, target: `dbex/nanobrag_bridge.py::derive_u_matrix_from_mosflm_a_star`)
- [ ] B2: **Quaternion ops** — Add `matrix_to_quaternion(U: torch.Tensor) -> torch.Tensor[4]` and `quaternion_to_matrix(q: torch.Tensor[4]) -> torch.Tensor[3,3]` helpers using PyTorch3D or scipy + torch conversion. Validate roundtrip: `torch.allclose(quaternion_to_matrix(matrix_to_quaternion(U)), U, atol=1e-6)`. (Ralph, target: `dbex/nanobrag_bridge.py::matrix_to_quaternion`, `::quaternion_to_matrix`)
- [ ] B3: **Config flag** — Add `use_u_matrix_parameterization: bool = False` to `RefinementConfig` dataclass in `dbex/config.py` (or inline in `nanobrag_refinement.py` if no central config). Update CLI `--use-u-matrix` flag and plumb to `build_mapping_stage_a_context`. (Ralph, target: `dbex/config.py::RefinementConfig`, `dbex/nanobrag_refinement.py::build_mapping_stage_a_context`)
- [ ] B4: **U-matrix initialization** — Extend `build_mapping_stage_a_context` with U-matrix branch: when `use_u_matrix_parameterization=True`, call `derive_u_matrix_from_mosflm_a_star`, convert to quaternion, initialize trainable `q_params = torch.tensor(q0, requires_grad=True)`. Store in `StageAContext`. (Ralph, target: `dbex/nanobrag_refinement.py::build_mapping_stage_a_context`)
- [ ] B5: **Closure branching** — Extend `build_stage_a_lbfgs_closure` with U-matrix path: (1) normalize `q_params`, (2) convert to rotation matrix, (3) compute `A_star_new = U @ B_ideal_reciprocal`, (4) update `crystal_overrides['A_star']`, (5) forward, loss, backward. Leave existing cell+misset path intact (else branch). (Ralph, target: `dbex/nanobrag_refinement.py::build_stage_a_lbfgs_closure`)
- [ ] B6: **Parity probe extension** — Extend `probe_crystal_matrix_parity.py` with `--use-u-matrix` flag. When enabled, initialize U-matrix path, run forward, compare A* against mapping MOSFLM A*, emit `max_abs_diff` and `quaternion_delta_norm`. (Ralph, target: `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py`)
- [ ] B7: **Gradcheck** — Add targeted gradcheck for quaternion_to_matrix and U-matrix closure on a minimal synthetic crystal config. Ensure gradients flow correctly through SO(3) normalization. (Ralph, artifact: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/<timestamp>/gradcheck_u_matrix.log`)

### Notes & Risks
- **Risk:** Quaternion → matrix conversion introduces numerical error >1e-6. **Mitigation:** Use double precision for initialization, validate roundtrip error <1e-8.
- **Risk:** LBFGS updates push quaternion off unit sphere faster than normalization can correct. **Mitigation:** Monitor `‖q‖` in telemetry; if drift >1e-3, switch to projected gradient descent or reparameterize.

## Phase C — Validation & Integration

### Checklist
- [x] C1: **Parity validation** — Run `probe_crystal_matrix_parity.py --use-u-matrix --device cpu` on canonical refGeom. Verify `max_abs_diff < 1e-6`. If not, diagnose (numerical precision? B_ideal mismatch? quaternion conversion bug?). (Ralph, artifact: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/<timestamp>/crystal_matrix_parity_u_matrix.json`) — **COMPLETE (2025-11-22T113409Z)**: Raw U-matrix achieves perfect parity (3.469e-18), but det(U₀)=1.000557 (NOT in SO(3)); quaternion projection degrades to ~4e-05. Proceed with Alternative Path 3 (convergence sensitivity test).
- [ ] C2: **Phase 5 convergence (scale-only)** — Run `stage_a_mapping_adam_debug.py --use-u-matrix --phases 5 --dof-variants A_scale_only --adam-steps 10 --device cpu`. Verify median CC ≥ 0.99, χ² stable (≤0.5% drift). (Ralph, artifact: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/<timestamp>/block_dof_results_u_matrix.json`) — **BLOCKED (2025-11-22T114945Z)**: Shape bug in B_ideal_reciprocal (cctbx returns flat (9,) not (3,3)); FIXED (2025-11-22T120500Z) by adding .reshape(3,3). Ready for rerun.
- [ ] C3: **Phase 5 convergence (full-DoF)** — Run Phase 5 with `D_full` or new `U_full` variant (U-matrix + scale + cell + angles). Verify monotonic χ² improvement, no large CC collapses. (Ralph, artifact: same as C2) — **BLOCKED**: Same shape bug as C2; ready for rerun after bugfix.
- [ ] C4: **Regression guard** — Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` with U-matrix path enabled (or as separate selector). Ensure no regressions. (Ralph, artifact: `pytest_stage_a_u_matrix.log`)
- [ ] C5: **Findings update** — Add GEOMETRY-004 to `docs/findings.md` documenting U-matrix parameterization, quaternion conventions, SO(3) normalization, and parity results. Cross-ref TORCH-GEOMETRY-PARITY-002. (Galph, target: `docs/findings.md`)
- [ ] C6: **Doc sync** — Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with any new selectors (e.g., `test_stage_a_u_matrix_parity`). Run `pytest --collect-only` and archive logs. (Ralph, artifact: `collect_u_matrix_tests.log`)
- [ ] C7: **Unblock TORCH-REFINE-002E** — Update `docs/fix_plan.md` to mark TORCH-REFINE-002E as `done` (alternative path: strain identified + impact quantified, convergence restored via TORCH-GEOMETRY-PARITY-002). Update Attempts History with final Phase C decision. (Galph, target: `docs/fix_plan.md`)

### Notes & Risks
- **Risk:** U-matrix path passes parity (<1e-6) but Phase 5 still degrades. **Escalation:** Open TORCH-REFINE-003 for optimizer/LR sensitivity analysis.
- **Risk:** Full-DoF variant (U + cell + angles) is ill-conditioned due to redundant DoFs. **Mitigation:** Document in findings, recommend U+scale-only or freeze cell/angles at mapping values.

## Artifacts Index
- Reports root: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`
- Key artifacts:
  - `phase_a0_evidence_synthesis.md` (Phase A0)
  - `so3_parameterization_survey.md` (Phase A1)
  - `api_design_u_matrix.md` (Phase A2)
  - `phase_a_risks.md` (Phase A3)
  - `gradcheck_u_matrix.log` (Phase B7)
  - `crystal_matrix_parity_u_matrix.json` (Phase C1)
  - `block_dof_results_u_matrix.json` (Phase C2/C3)
  - `pytest_stage_a_u_matrix.log` (Phase C4)
  - `collect_u_matrix_tests.log` (Phase C6)
