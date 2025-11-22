## Initiative
- ID: TORCH-REFINE-002E
- Title: Fix Stage A Zero-Point Geometry Discontinuity (Diagnostic Phase)
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md
- Status: in_progress

## Goals
- Separate **geometry mismatch** (A*/B strain vs pure rotation) from **optimization artifacts** (scale/Adam behavior) at the mapping zero point.
- Determine which combination of:
  - residual B-matrix/strain differences,
  - scale parameterization mismatch,
  - variance-weighted loss details,
  - and optimization hyperparameters
  actually causes:
  - `probe_crystal_matrix_parity.py` to report `max_abs_diff≈4e‑5` (not <1e‑6), and
  - `stage_a_mapping_adam_debug.py` Phase 5 A_scale_only / D_full to increase χ² and degrade CC.
- Decide, based on evidence, whether to:
  - (A) adjust the **geometry mapping** (baseline cell/B_ideal alignment),
  - (B) adjust the **Stage‑A parameterization** (scale/misset/delta conventions),
  - (C) adjust the **debug driver** (LR, gating, or DoF subsets), or
  - (D) accept a documented residual and scope future work accordingly.

## Phases Overview
- Phase A — Geometry Characterization: Quantify and localize the remaining A*/B mismatch.
- Phase B — Gradient & Optimizer Diagnosis: Probe loss/gradient behavior at the mapping zero point across DoFs.
- Phase C — Action & Re‑validation: Apply the minimal fix (geometry vs parameterization vs tooling) and re‑run parity tests.

## Exit Criteria
1. For the canonical mapping crystal, `probe_crystal_matrix_parity.py` plus extended diagnostics show either:
   - A pure‑rotation discrepancy with `max_abs_diff < 1e‑6` and `U_error` within numerical tolerance **or**
   - A clearly identified non‑rotational strain component with quantified magnitude and documented impact on gradients.
2. Stage‑A mapping debug Phase 5:
   - A_scale_only: χ² stays within a small band (e.g. ≤0.5% drift) and median ROI CC remains ≥0.99 after 10 steps **or** we have a justified, tested rationale for constraining/removing this variant.
   - D_full: either shows clear χ² improvement without large CC collapses, or we explicitly gate/disable it with an evidence-backed reason (e.g. geometry DoFs demonstrably ill‑conditioned at mapping).
3. A decision log (in `plans/active/TORCH-REFINE-002E/reports/…/decision.json`) captures which hypothesis was confirmed and what code/doc changes (if any) are required.
4. Test registry synchronized and `pytest --collect-only` logs for:
   - `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
   - any new selectors added for these probes
   are saved under `plans/active/TORCH-REFINE-002E/reports/<timestamp>/`.

## Compliance Matrix (Mandatory)
> List the specific Spec constraints, Fix-Plan ledger rows, and Findings/Policies this initiative must honor. Missing a relevant entry is a plan defect per ARRP.
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md` §Stage A — mapping zero-point invariant
- [ ] **Spec Constraint:** `docs/spec-db-core.md` §Geometry Mapping + Variance Model
- [ ] **Spec Constraint:** `docs/spec-db-conformance.md` (Mapping‑Aligned Stage‑A Initialization)
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [TORCH-REFINE-002E]`
- [ ] **Finding/Policy ID:** `GEOMETRY-001` (detector mapping)
- [ ] **Finding/Policy ID:** `GEOMETRY-002` (Euler inversion)
- [ ] **Finding/Policy ID:** `GEOMETRY-003` (B_ideal-based mapping misset)
- [ ] **Finding/Policy ID:** `GRADIENT-001` (tensor overrides)
- [ ] **Finding/Policy ID:** `REFINE-004/005` (Stage‑A gate, HKL halo/interpolation)

## Spec Alignment
- **Normative Spec:** `docs/spec-db-workflow.md`
  - Stage‑A mapping zero-point invariant
- **Normative Spec:** `docs/spec-db-core.md`
  - Geometry Mapping, Variance Model
- **Normative Spec:** `docs/spec-db-conformance.md`
  - Mapping‑Aligned Stage‑A Initialization (DB‑AT‑024)
- **Key Clauses:** mapping forward model must match refinement zero point; when `crystal_overrides` are used, baseline misset must encode mapping orientation and parameters must be true deltas.

## Context Priming (read before edits)
- Primary docs/specs to re-read:
  - `docs/spec-db-workflow.md` §Stage A
  - `docs/spec-db-core.md` §Geometry Mapping, Variance
  - `docs/spec-db-conformance.md` mapping sections
  - `docs/config_crosswalk.md` crystal mapping section
- Required findings/case law:
  - `docs/findings.md` rows GEOMETRY‑001/002/003, REFINE‑004/005
- Related telemetry/attempts:
  - `plans/active/TOOLING-VIS-001/stage_a_mapping_adam_debug_plan.md`
  - `plans/active/TORCH-REFINE-002E/reports/20251121T234012Z/crystal_matrix_parity.json`
  - `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/20251121T234215Z/{zero_point_check.json,block_dof_results.json}`

## Phase A — Geometry Characterization

### Hypotheses
- **H1 (Residual strain):** The remaining A* gap is not purely rotational; B_ideal differs from the effective mapping B, leaving a small strain the misset can’t absorb.
- **H2 (Baseline cell mismatch):** Mapping uses a slightly different effective unit cell (via MOSFLM A* + cctbx internals) than the Stage‑A baseline cell, so we’re rotating about the “wrong” B_ideal.

### Checklist
- [ ] A0: **Probe extension:** Extend `probe_crystal_matrix_parity.py` to compute and report:
  - `A*_pathA` and `A*_pathB` eigenvalues/singular values.
  - Symmetric/antisymmetric decomposition of `logm(U_error)` to separate pure rotation from symmetric strain.
  - Per‑column norms and angles between corresponding a*, b*, c*.
- [ ] A1: **Multi‑config sweep:** Run the probe for:
  - Baseline refGeom vs refined.expt geometry (if available).
  - Small synthetic cell perturbations (e.g. ±1% on a/b/c) without orientation change. Record whether `U_error` remains close to a pure rotation in each case.
- [ ] A2: **Baseline B_ideal variants:** Construct alternative B_ideal candidates:
  - From mapping MOSFLM A* (via a “recovered” cell) instead of the pure unit cell.
  - From the refined.expt crystal instead of refGeom. Recompute misset with each B_ideal, re‑run the probe, and compare `max_abs_diff` and rotation/strain metrics.
- [ ] A3: **Mapping forward vs Stage‑A configs:** For a single panel and a short HKL subset:
  - Build a `CrystalConfig` using the mapping path (MOSFLM A* + `misset=[0,0,0]`).
  - Build a config using explicit cell+misset with the new robust baseline. Numerically compare reciprocal vectors and real‑space vectors from `compute_cell_tensors()`. Decide whether the geometry gap is dominated by strain or is within acceptable rotational noise.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py` (tooling only).
- **Circular Import Risks:** None (script already uses top‑level bridge imports).
- **State Migration:** None; probe reads existing assets, no pipeline changes.

### Notes & Risks
- If H1 is confirmed (non‑negligible strain), we must decide whether to:
  - encode a baseline strain in Stage‑A `crystal_overrides`, or
  - accept that mapping vs refinement use slightly different physics and adjust the mapping debug expectations.

## Phase B — Gradient & Optimizer Diagnosis

### Hypotheses
- **H3 (Scale zero-point mismatch):** Even when geometry tensors match, the combination of `spot_scale_override`, `global_scale_hint`, and `log_scale` leaves Stage‑A zero slightly off the true χ² optimum, so scale‑only Adam legitimately walks away (but our LR/steps are too aggressive).
- **H4 (Gradient dominated by outliers):** A small number of ROIs/pixels with higher residuals (e.g. where sample clipping or interpolation differs) dominate the Stage‑A gradients, causing global CC degradation while median CC was initially ~1.0.
- **H5 (Loss/variance subtlety):** The variance‑weighted loss (detached denominator and sigma_floor clamp) is not perfectly identical between mapping diagnostics and Stage‑A, so “same image” does not mean “zero gradient”.

### Checklist
- [ ] B1: **Local gradient probe at mapping zero:** In `stage_a_mapping_adam_debug.py`, add an optional “gradient probe” mode that:
  - Evaluates χ² and ∂χ²/∂θ for θ ∈ {log_scale, cell logs, angle raws, orientation_vec} at the zero‑parameter point.
  - Emits per‑parameter gradient magnitudes and signs, both globally and restricted to a “trusted ROI subset” (e.g. top N ROIs by mapping CC).
- [ ] B2: **Scale analytical optimum check:** With geometry frozen at mapping:
  - Derive the closed‑form optimal scale α* for a simplified variance model around the mapping point.
  - Compare α* to `global_scale_hint` and the initial `exp(log_scale)`; check whether zero log_scale is already near optimal.
- [ ] B3: **LR / step sensitivity sweep:** Use the existing Phase 5 driver but:
  - Run A_scale_only and D_full with a grid of learning rates (e.g. 1e‑5, 5e‑5, 1e‑4, 5e‑4) and step counts (1, 3, 10).
  - Log χ² and median CC after each step to see whether some configurations improve χ², indicating a tuning issue rather than geometry.
- [ ] B4: **Outlier ROI analysis:** Using `zero_point_check.json` and `block_dof_results.json`:
  - Identify ROIs with largest negative CC deltas and largest positive local χ² contribution change.
  - For these ROIs, dump per‑ROI loss contributions over Adam steps and inspect whether they correspond to edge cases (mask edges, halo boundaries, extreme intensities).
- [ ] B5: **Loss parity re‑audit:** For a fixed configuration (mapping zero point), explicitly recompute χ²:
  - via the mapping diagnostics path (`simulate_forward_once`),
  - via Stage‑A `_compute_variance_weighted_loss` using identical `target`, `sigma_readout`, `sigma_floor`. Confirm they agree to machine precision; if not, quantify and document the discrepancy.

### Notes & Risks
- If we find non‑zero gradients at mapping zero w.r.t. certain DoFs that are *expected* to be frozen by the mapping spec, that implies a deeper parity or configuration bug.
- If χ² can be improved with smaller LR or fewer steps, the problem may be strictly about debug‑driver settings, not the underlying geometry.

## Phase C — Action & Re‑validation

### Decision Branches (based on Phases A/B)

- **Branch G (Geometry fix):**  
  If Phase A shows meaningful strain and Phase B shows non‑zero gradients even with conservative Adam settings:
  - Adjust baseline geometry so that the Stage‑A explicit path uses the same effective cell as the mapping path (e.g. derive `crystal_overrides` baseline from mapping’s reconstructed cell/B).
  - Keep misset as a pure rotation around this new baseline.
- **Branch P (Parameterization / scale fix):**  
  If gradients are mostly in the scale and χ² vs log_scale is clearly convex around zero:
  - Re‑express Stage‑A scale so that `log_scale=0` is the true argmin at mapping, e.g. by solving for α* and baking it into `global_scale_hint`.
- **Branch T (Tooling/driver fix):**  
  If zero‑point gradients are near zero and small steps don’t degrade χ², but the documented Phase 5 settings do:
  - Retune Phase 5 defaults (LR, steps, gating), and/or
  - Reduce geometry DoFs enabled in the mapping debug driver (e.g. keep scale‑only, gate full geometry behind an explicit flag).

### Checklist
- [ ] C1: **Select branch and implement minimal change:**  
  Based on Phases A/B artifacts, choose G, P, T (or a combination) and implement the smallest change needed to:
  - either zero the gradients at mapping, or
  - ensure Phase 5 experiments behave monotonically/non‑pathologically.
- [ ] C2: **Re‑run core selectors:**  
  Re‑run:
  - `pytest -q tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  - `stage_a_mapping_adam_debug.py --phases 1,2,4,5 --device cpu`  
  Save artifacts under `plans/active/TORCH-REFINE-002E/reports/<timestamp>/`.
- [ ] C3: **Update findings and fix_plan:**  
  - If a geometry or parameterization change is made, update `docs/findings.md` (GEOMETRY‑003 text) and the TORCH‑REFINE‑002E row in `docs/fix_plan.md` with the final rationale and artifacts.
  - If only tooling changed (debug driver), document that the mapping spec is satisfied but the driver runs with a safer configuration.

### Notes & Risks
- Geometry changes affect all refinement flows; prefer to localize fixes to mapping‑aligned helper paths unless specs demand otherwise.
- Any change that substantially alters Stage‑A χ² must be cross‑checked against DB‑AT selectors once they’re wired to the torch backend.

## Artifacts Index
- Reports root: `plans/active/TORCH-REFINE-002E/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`
