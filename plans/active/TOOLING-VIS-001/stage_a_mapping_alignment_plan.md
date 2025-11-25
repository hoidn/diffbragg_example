# TOOLING-VIS-001 — Stage A Mapping-Aligned Visualization Plan

## Initiative
- ID: TOOLING-VIS-001
- Title: Align Stage A Vis to Mapping Model
- Owner: Unassigned
- Spec Owner: docs/spec-db-vis.md, docs/spec-db-workflow.md §6–7
- Status: pending

## Goals
- Use the DB-AT-024 mapping forward model (`simulate_forward_once` with refined MTZ + calibration) as the canonical source of Stage A “before” ROI visuals.
- Add a vis-only refinement layer on top of the mapping model (scale-only initially, with tightly bounded geometric tweaks as a follow-up), without changing the canonical `run_nanobrag_refinement` engine or Stage A HKL grid.
- Provide reproducible, spec-aligned ROI triptychs and loss curves where “before” and “after” share the same forward model and variance-weighted loss.

## Phases Overview
- Phase A — Mapping Context Helper: Capture a reusable “mapping-based Stage A context” for vis.
- Phase B — Mapping-Based Refinement Layer: Implement a constrained refinement helper on top of the mapping model.
- Phase C — Integration & Validation: Wire the helper into TOOLING-VIS-001 drivers and validate behavior.
 - Phase D — Zero-Point Alignment: Ensure mapping-based Stage A helpers share the exact DB‑AT‑024 mapping geometry at zero parameters.

## Exit Criteria
1. A mapping context helper exists that loads refined geometry + mask, prepares `RefinementInputs`, and runs `simulate_forward_once` to produce a zero-iteration Bragg stack plus `sigma_floor_value`, and is used as the sole source of “before” ROI triptychs in TOOLING-VIS-001.
2. A vis-only refinement helper (e.g., `refine_on_mapping_model`) exists that:
   - Treats the mapping Bragg stack as the fixed base model.
   - Optimizes a constrained parameter subset (global scale; optional tightly bounded orientation/cell deltas) using the same variance-weighted chi-squared loss as `simulate_forward_once`.
   - Returns `bragg_after` and a loss trace suitable for plotting.
3. TOOLING-VIS-001 Stage A ROI drivers (`generate_stage_a_*_triptychs*.py`) are updated so that both “before” and “after” PNGs are derived from the mapping model + constrained refinement, not from a separate Stage A HKL grid, and the plan-local docs/summary files describe the unified forward model.
4. Test/selector documentation is updated where relevant:
   - `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` reference any new vis-only scripts/selectors or explicitly note that these helpers are plan-local and not part of the canonical test registry.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-vis.md — ROI triptych layout, `(slow, fast)` coordinates, and Z-score residual definition.
- [ ] **Spec Constraint:** docs/spec-db-core.md §Variance Model — Use `V = I_model + sigma_readout^2`, `sigma_floor` clamp, and detached denominator consistently in mapping-based refinement.
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §6–7 — Stage A staging and loss semantics; do not alter canonical engine behavior without a dedicated initiative.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row `[TOOLING-VIS-001]` (visual diagnostics library), plus any Stage A/DB-AT-024 findings referenced in this plan.
- [ ] **Finding/Policy ID:** POLICY-001 (Environment Freeze); CONFIG-001 (detector/geometry contracts); any relevant REFINE/MAP-SCALE findings exercised by mapping-based visuals.
 - [ ] **Spec Zero-Point Invariant:** docs/spec-db-conformance.md §“Mapping-Aligned Stage‑A Initialization” (zero-parameter Stage A MUST reproduce DB‑AT‑024 mapping Bragg); docs/spec-db-workflow.md §“Stage A (Geometry & Scale)” mapping zero-point invariant; docs/config_crosswalk.md Crystal section baseline-misset rules.

## Spec Alignment
- **Normative Spec:** docs/spec-db-vis.md, docs/spec-db-core.md, docs/spec-db-workflow.md
- **Key Clauses:**
  - spec-db-vis.md — ROI triptych layout, intensity/residual colormaps, Z-score definition.
  - spec-db-core.md — Variance model (`I_model + sigma_readout^2`, sigma_floor), masking, and IRLS behavior.
  - spec-db-workflow.md §Stage A — Loss and staging definitions; Stage A optimizer requirements (LBFGS for canonical engine).

## Context Priming (read before edits)
- docs/spec-db-vis.md — Triptych and Z-score requirements.
- docs/spec-db-core.md §Variance Model, Masking.
- docs/spec-db-workflow.md §6–7 — Stage A staging and loss semantics.
- docs/fix_plan.md — `[TOOLING-VIS-001]`, DB-AT-024 and Stage A-related rows.
- tests/dbex/test_mapping_consistency.py — DB-AT-024 mapping implementation and metrics.
- dbex/nanobrag_bridge.py — `simulate_forward_once`, `prepare_refinement_inputs`.
- Existing TOOLING-VIS-001 docs: `plans/active/TOOLING-VIS-001/implementation.md`, `stage_a_roi_before_after_plan.md`.

## Phase A — Mapping Context Helper

### Checklist
- [ ] A0: **Nucleus / Probe:** Write a small script (plan-local) that:
  - Loads refined geometry + mask via `DataLoad`.
  - Prepares `RefinementInputs` via `prepare_refinement_inputs`.
  - Runs `simulate_forward_once` (refined MTZ + calibration).
  - Computes per-ROI CC and localization, and verifies they match (within tolerance) the latest DB-AT-024 metrics for the same assets.
- [ ] A1: Implement a `build_mapping_stage_a_context` helper (plan-local or in `dbex.vis`) that returns:
  - `inputs` (RefinementInputs),
  - `bragg_zero_iter` from `simulate_forward_once`,
  - `sigma_floor_value` (and any other relevant diagnostics).
- [ ] A2: Update existing vis drivers so “before” triptychs for Stage A ROI visualization are sourced exclusively from `build_mapping_stage_a_context` (no alternate zero-iter paths).
- [ ] A3: Document the mapping context helper in `plans/active/TOOLING-VIS-001/implementation.md` and note how it relates to DB-AT-024.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dbex/data_load.py, dbex/nanobrag_bridge.py, dbex/vis (new mapping helper), plans/active/TOOLING-VIS-001/bin/*.
- **Circular Import Risks:** Keep mapping helpers in `dbex.vis` or plan-local modules that only import nanobrag_bridge and do not introduce new imports from `dbex.nanobrag_refinement` into bridge code.
- **State Migration:** None for production paths; the mapping context wraps existing helpers and is consumed only by TOOLING-VIS-001 vis scripts.

### Notes & Risks
- Risk: Divergence between DB-AT-024 mapping implementation and the mapping context helper. Mitigation: Keep the helper thin and reuse DB-AT-024 code paths directly where practical.
- Known gap (2025-11-25): `build_mapping_stage_a_context` still hardcodes the golden `tests/fixtures/golden_data/simple_cubic` calibration + refined HKL assets even when the caller supplies a different `DataLoad`. This is the immediate cause of the ROI CC collapse (0.62 → -0.04) once the probe/fixture began sharing the helper. Phase A work must route calibration/HKL provenance from the actual `DataLoad` (or explicit overrides such as `DBEX_SMOKE_HKL_PATH`) before any further diagnostics make sense.

## Phase B — Mapping-Based Refinement Layer

### Checklist
- [ ] B0: **Nucleus / Test-first:** Implement a unit-style probe (plan-local) that:
  - Uses the mapping context (`inputs`, `bragg_zero_iter`, `sigma_floor_value`).
  - Optimizes only a global scale parameter (Adam or SGD) for a small number of steps.
  - Asserts that the loss trace is stable and that per-ROI CC does not catastrophically degrade.
- [ ] B1: Implement `refine_on_mapping_model(inputs, bragg_zero_iter, sigma_floor_value, config)`:
  - Stage 1: scale-only optimization (global `log_scale`) with variance-weighted chi-squared loss, using the same variance and mask semantics as `simulate_forward_once`.
  - Stage 2 (optional extension): add tightly bounded geometric DoFs (small misset, small cell perturbations) with explicit clamps.
- [ ] B2: Ensure the helper returns:
  - `bragg_after` (same shape as `bragg_zero_iter`),
  - `loss_trace` (for plotting),
  - Optional per-ROI metrics (CC before/after; loss contributions).
- [ ] B3: Document the parameterization and bounds used by `refine_on_mapping_model` in TOOLING-VIS-001 docs, including explicit statements that it is vis-only and does not change canonical Stage A.

### Notes & Risks
- Risk: Even small geometric tweaks may reduce global chi-squared while degrading specific ROI visuals. Mitigation: Start with scale-only, then gate enabling of geometric DoFs on observed benefit in both loss and CC/visuals.
- Risk: Confusion between mapping-based refinement and canonical Stage A. Mitigation: Clearly label mapping-based refinement as vis-only and keep its code paths separate from `run_nanobrag_refinement`.

## Phase C — Integration & Validation

### Checklist
- [ ] C1: Update Stage A ROI vis drivers under TOOLING-VIS-001 (e.g., `generate_stage_a_refgeom_roi_triptychs*.py`) to:
  - Use `build_mapping_stage_a_context` for `bragg_before`.
  - Use `refine_on_mapping_model` to obtain `bragg_after` (mapping-based) for “after” triptychs.
- [ ] C2: Regenerate per-ROI triptychs, aggregate “all ROIs” grids, and loss-curve PNGs under a new timestamped reports directory; confirm visually that:
  - Peaks are aligned in “before” per DB-AT-024 expectations.
  - Mapping-based refinement does not introduce catastrophic degradation (and ideally improves or leaves CC unchanged).
- [ ] C3: Update TOOLING-VIS-001 docs:
  - Note the new mapping-aligned Stage A ROI pipeline.
  - Clarify that canonical Stage A (`run_nanobrag_refinement`) is unchanged and still uses its existing HKL grid.
- [ ] C4: If any scripts are exposed as dev tooling, add minimal notes in `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md` describing their purpose and indicating they are plan-local rather than part of the main test suite.

### Notes & Risks
- Risk: Developers may misinterpret mapping-based refinement results as canonical Stage A behavior. Mitigation: Keep naming and docs explicit (e.g., “mapping-based Stage A vis”) and avoid reusing engine names.
- Risk: Future changes to DB-AT-024 may drift away from this vis pipeline. Mitigation: revisit this plan when DB-AT-024 mapping semantics change and adjust helpers as needed.

## Artifacts Index
- Reports root: `plans/active/TOOLING-VIS-001/reports/`
- Mapping-based Stage A vis runs:
  - `stage_a_zero_iter_refined/<timestamp>/` — zero-iteration mapping context ROI triptychs.
  - `stage_a_refgeom_adam/<timestamp>/` — mapping-based scale-only refinement outputs (triptychs, loss curves, aggregate ROI grids).
  - Future mapping-based refinement runs (with geometry tweaks) should follow the same pattern under TOOLING-VIS-001.

## Phase D — Zero-Point Realignment (Mapping vs Stage A)

### Objective
Ensure that any mapping-based Stage A refinement/visualization helper (including plan-local Adam tools) satisfies the zero-point invariant:

- At zero geometry parameters (cell/angle/orientation deltas = 0) and baseline scale, the Stage A forward simulator MUST reproduce the DB‑AT‑024 `simulate_forward_once` Bragg stack for the same `RefinementInputs` and HKL grid, within numerical tolerance, and must match the mapping chi-squared within a small relative tolerance.

### Checklist
- [ ] D0: **Baseline contracts and “truth” configuration**
  - Record, without changing behavior, the mapping “truth” configuration in:
    - `dbex.vis.mapping.MappingStageAContext` (cell, A* path, `spot_scale_override`, `sigma_floor_value`, HKL source).
    - `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` docstring/comments, clarifying that `context.bragg_zero_iter` is the canonical Stage A zero point.
  - Ensure forward-model and loss invariants from Phase 1/2 of the debug plan are explicitly referenced here (mapping vs Stage‑A no-op parity, chi² equality).

- [ ] D1: **Baseline misset extraction helper**
  - Extract (or confirm and reuse) the baseline misset computation from `dbex.nanobrag_refinement` into `dbex.nanobrag_bridge.compute_baseline_misset_deg(crystal, baseline_crystal)` or an equivalent helper:
    - Use `baseline_crystal.get_U()` and `crystal.get_U()` to build `U_delta = U_perturbed @ U_baseline^{-1}`.
    - Decompose `U_delta` into XYZ extrinsic Euler angles, returning degrees.
  - Confirm via a focused probe that:
    - Using `create_crystal_config(crystal, expt, crystal_overrides=None, misset_deg_override=None)` plus MOSFLM A* injection, and
    - Using `create_crystal_config(crystal, expt, crystal_overrides=None, misset_deg_override=baseline_misset_deg)` with MOSFLM A* disabled,
    produce equivalent Bragg stacks (within numerical tolerance) for the canonical assets.

- [ ] D2: **Shared Stage‑A forward helper and zero point alignment**
  - Factor a single Stage‑A forward helper (plan-local) in `stage_a_mapping_adam_debug.py` (e.g., `_stage_a_forward`) that:
    - Reuses the existing HKL grid, beam_config, detector models, and `_compute_variance_weighted_loss` wiring.
    - Accepts `log_scale`, cell deltas, and orientation vector as inputs.
  - Update both `_build_stage_a_bragg_noop` and `_stage_a_adam_core` to call this helper so they share an identical forward path:
    - For the zero‑deltas path, call `create_crystal_config` with `crystal_overrides=None` and `misset_deg_override=None` so MOSFLM A* injection is active, matching `simulate_forward_once`.
    - Only when any delta is non‑zero should the helper disable A* and apply `misset_deg = baseline_misset_deg_tensor + delta_misset` plus cell overrides derived from the Stage‑A parameters.
  - Require that with `log_cell_*_delta = 0`, `angle_*_raw = 0`, `orientation_vec = 0`, and `log_scale = 0` (or `log(global_scale_hint or 1.0)`), the helper’s forward model produces a Bragg stack that matches `context.bragg_zero_iter` to within numerical tolerance.

- [ ] D3: **Zero-point equality probe and chi² gate**
  - Extend the debug driver to run an explicit zero‑point probe that:
    - Invokes `_stage_a_adam_core` (via the shared helper) with `n_steps=0` and all deltas zero.
    - Writes `zero_point_check.json` with:
      - `max_abs_diff`, `mean_abs_diff` between Stage‑A zero point and `bragg_zero_iter`.
      - `corr_median_vs_mapping` across ROIs.
      - Mapping vs Stage‑A chi² at zero parameters and their relative difference.
  - Define a conservative gate:
    - `max_abs_diff <= 1e-6` and
    - `rel_diff(chi2_stage_a, chi2_mapping) <= 1e-6` (or a similarly tight bound).
  - Wire this `zero_point_ok` flag into `stage_a_mapping_adam_debug.main` so geometry experiments (single-step Adam and block-wise DoF sweeps) are automatically skipped if the zero-point invariant fails.

- [ ] D4: **Validation runs (CPU mandatory, CUDA optional)**
  - Run the debug driver on CPU with full phases:
    - `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --device cpu --phases 1,2,3,4,5`
    - Confirm:
      - `forward_model_probe.json` remains aligned (mapping vs Stage‑A no‑op unchanged within numerical noise).
      - `loss_alignment.json` maintains chi² parity to ~1e‑8 relative.
      - `zero_point_check.json` reports `zero_point_ok = true`, tiny `max_abs_diff`, and `corr_median_vs_mapping` close to the mapping median CC (~0.62).
      - `single_step_adam.json` shows chi² not increasing on the first step (ideally decreasing or flat).
  - Optionally, repeat with CUDA if available:
    - `python ... --device cuda --phases 1,2,3,4,5`
    - Treat any torch runtime issues (e.g., `torch.compile` / simulator bugs) per `docs/pytorch_runtime_checklist.md`; do not block closure of this plan on CUDA parity.

- [x] D5: **Unify the Stage‑A forward implementation**
  - Refactor the plan‑local Stage‑A helpers in `stage_a_mapping_adam_debug.py` so that mapping, Stage‑A no‑op, and the Adam-based Stage‑A refinement all call a single shared forward helper (conceptually `_stage_a_forward`) that:
    - Accepts `log_scale`, cell deltas, and orientation vector parameters.
    - Reuses the HKL grid, calibration, beam_config, detector models, masks, and `_compute_variance_weighted_loss` wiring already validated against DB‑AT‑024.
  - Reduce `_build_stage_a_bragg_noop` to a thin wrapper that calls this shared helper with all deltas zero and baseline scale, rather than constructing its own forward path.
  - Ensure `_stage_a_adam_core` only differs by its choice of parameter tensors and optimizer settings; its forward pass MUST go through the same shared helper so that any zero‑point divergence vs mapping is impossible without failing the zero‑point gate.

- [ ] D6: **Audit other mapping-aligned helpers and update telemetry/docs**
  - Review any other Stage‑A mapping helpers (e.g., future `ExperimentModel(param_init="stage_a_mapping")` or related plan‑local tools) to ensure they either:
    - Reuse the shared Stage‑A forward helper / misset construction, or
    - Implement equivalent logic and pass a similar zero-point equality probe.
  - Extend `stage_a_mapping_adam_debug` telemetry and TOOLING‑VIS‑001 docs:
    - Ensure `zero_point_check.json` and `single_step_adam.json` are linked from TOOLING‑VIS‑001 documentation and the `[TOOLING‑VIS-001]` row in `docs/fix_plan.md`.
    - Summarize the final zero-point alignment results (e.g., “zero-point diff ≤ 1e−6; mapping chi² parity maintained; first Adam step non‑divergent”).
    - State the policy that mapping-based helpers MUST pass the zero-point gate before geometry DoFs are enabled in vis‑only refinement runs, and explicitly mark any non‑compliant helpers as non‑mapping‑aligned and out‑of‑scope for DB‑AT selectors.

## Phase E — Geometry Equivalence Investigation (Mapping vs Stage‑A Overrides)

### Objective
Identify and localize the source of the residual mismatch between the mapping path (MOSFLM A* injection) and the Stage‑A overrides path (cell+misset without A* injection) so that the Stage‑A zero point can be made exactly equivalent to the DB‑AT‑024 mapping solution when desired.

### Checklist
- [ ] E0: **Minimal repro probe**
  - Author a plan-local probe script under `plans/active/TOOLING-VIS-001/bin/` (e.g., `probe_stage_a_geometry_equivalence.py`) that:
    - Builds a `DataLoad` + `MappingStageAContext` on CPU.
    - For a single panel + ROI:
      - Evaluates bragg for:
        1. Mapping geometry (`bragg_zero_iter` slice).
        2. Stage‑A mapping branch (`_stage_a_forward(..., use_mapping_zero_geometry=True, log_scale=0, deltas=0)`).
        3. Stage‑A overrides branch (`use_mapping_zero_geometry=False, log_scale=0, deltas=0`).
      - Computes `max_abs_diff`, `mean_abs_diff`, and per‑ROI CC vs mapping for (2) and (3).
    - Writes a `phaseE_minimal_probe.json` artifact under the TOOLING‑VIS‑001 reports tree with these metrics.

- [ ] E1: **Compare mapping vs Stage‑A χ² at zero**
  - Reuse `_compute_variance_weighted_loss` on the three bragg variants from E0 with identical `target`, `sigma_readout`, `loss_mask`, and `sigma_floor_value`.
  - Record:
    - `chi2_mapping`, `chi2_stageA_mappingBranch` (use_mapping_zero_geometry=True), and `chi2_stageA_overridesBranch` (use_mapping_zero_geometry=False, deltas=0, log_scale=0).
  - Confirm that:
    - Mapping vs Stage‑A mappingBranch agree within numerical noise.
    - Any remaining mismatch is isolated to the overrides branch.

- [ ] E2: **Log crystal/A*/misset inputs for both branches**
  - Add temporary debug logging (plan-local; guarded or kept in a probe script) around `create_crystal_config` calls used by Stage‑A helpers to capture:
    - For the mapping branch: unit cell, `crystal.get_A()`, and `misset_deg` used when `crystal_overrides=None`.
    - For the Stage‑A overrides branch at zero deltas: overridden cell values, `baseline_misset_deg_tensor`, final `misset_deg_override`, and whether MOSFLM A* is injected or disabled.
  - Write a `phaseE_crystal_inputs.json` artifact that makes it easy to compare the effective `A`, cell, and misset used by the two paths.

- [ ] E3: **Round‑trip test for `compute_baseline_misset_deg`**
  - Construct a few synthetic dxtbx crystal pairs with known relative misset (simple rotations) and:
    - Run `compute_baseline_misset_deg(crystal, baseline_crystal)`.
    - Feed the resulting misset into `create_crystal_config(..., crystal_overrides=None, misset_deg_override=baseline_misset_deg)` with MOSFLM A* disabled.
    - Verify whether the resulting A (or simulated bragg) matches the “perturbed” crystal using A* injection within tight tolerance.
  - If the round-trip fails, document the Euler convention / sign discrepancies (GEOMETRY‑002) and propose corrected formulas or a more robust construction for baseline misset.

- [ ] E4: **Scale vs geometry separation**
  - Repeat the zero-point probes with:
    - `log_scale = 0` in both mapping and Stage‑A branches (bypassing `global_scale_hint`), and
    - The same `sqrt_spot_scale` as recorded in `context.diagnostics`.
  - Recompute χ² and CC to disentangle:
    - Pure geometry mismatches (A* + misset), from
    - Global scale differences (mapping vs Stage‑A use of `global_scale_hint`).

- [ ] E5: **Local sensitivity checks**
  - On the mapping branch and the Stage‑A overrides branch at zero:
    - Apply tiny perturbations in `log_scale` (e.g., ±1e‑3) and compare `dχ²/dlog_scale` between the branches.
    - Optionally, apply tiny perturbations to Stage‑A geometry DOFs (cell deltas/orientation_vec) and compare the resulting bragg and χ² changes to equivalent perturbations expressed directly in the mapping representation (e.g., small tweaks to U/A*).
  - Use these directional derivatives to identify which DOFs (and which representation) diverge most strongly from the mapping behavior at zero.

### Notes & Risks
- Keep instrumentation plan-local and guarded so it does not affect production Stage‑A code paths.
- Use small ROIs and limited panels for these probes to keep runs tractable.
- Treat any discovered discrepancies as candidates for targeted bridge fixes (e.g., improved baseline misset computation, conditional A* injection at zero deltas) and capture them as follow-up items in this plan and the `[TOOLING-VIS-001]` fix-plan ledger row.
