# TOOLING-VIS-001 — Stage A Mapping Adam Debug Plan

## Problem Statement

- Initiative: `TOOLING-VIS-001` — Standardize visual diagnostics (Z-scores & triptychs).
- Context: Mapping-aligned Stage A helpers now reuse the DB-AT-024 forward model
  (`simulate_forward_once`) to generate "before" ROI triptychs from refined MTZ
  + calibration. An experimental Adam-based full Stage A refinement helper was
  added on top of this mapping context to drive a vis-only "after" image.
- Observed issue: When the full Stage A parameterization (scale + unit cell deltas
  + orientation) is optimized with Adam on the mapping context, median per-ROI
  correlation against the mapping "before" model degrades catastrophically
  (e.g. 0.61→≈0.0) even after matching HKL grid and calibration/sqrt-spot-scale
  behavior to `simulate_forward_once`. Safeguards in the driver script correctly
  raise `RuntimeError` when this happens.

Goal: Systematically diagnose whether this degradation is caused by a remaining
forward-model mismatch, a loss-definition mismatch, or pathological optimizer
behavior in the full Stage A parameter space, and then decide whether to
constrain, fix, or retire the full-DoF mapping helper.

## Phase 0 — Environment Lockdown

Checklist:
- [ ] P0.1: Fix runtime knobs for all debug runs:
  - `CUDA_VISIBLE_DEVICES=''`
  - `NANOBRAG_DISABLE_COMPILE=1`
  - `KMP_DUPLICATE_LIB_OK=TRUE`
- [ ] P0.2: Use a small, fixed number of Adam steps (e.g. 10–20) and log all
  runs to a dedicated reports subtree:
  - `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/<timestamp>/`.
- [ ] P0.3: Record exact command lines and seeds in a `commands.txt` inside each
  debug run directory to ensure reproducibility.

## Phase 1 — Forward-Model Equality Probe

Objective: Prove that, with zero Stage A perturbations, the mapping helper's
Stage A simulator produces the same Bragg stack as `simulate_forward_once`.

Normative UB anchor (informative for this plan):
- The mapping-aligned Stage A parameterization for geometry SHOULD match the incremental UB conventions in `writeups/torch_geometry_incremental_ub_parameterization.tex` and GEOMETRY-004:
  - Baseline mapping state is defined by `A*_0 = crystal.get_A()`, baseline cell `c₀`, `B₀ = B(c₀)` (Busing–Levy), and `U₀ = A*_0 @ B₀⁻¹`.
  - Orientation increments are encoded as a unit quaternion misset `q_delta` such that `U(q_delta) = R(q_delta) @ U₀` with identity quaternion `(1,0,0,0)` representing “no misset”.
  - Cell increments perturb the baseline cell (log-deltas for lengths, additive deltas for angles) and always recompute `B(c)` directly from the cell, never from `A*`.
  - Forward mapping is strictly `(q_delta, δc) → (U,B) → A* = U @ B`, with zero point `(q_delta_id, δc=0)` recovering `A*_0`.
  - DB-AT-026 tests (UB/A* round-trip) and DB-AT-027 (Stage-A zero-point mapping equivalence) SHALL be treated as the authoritative checks that this parameterization is wired correctly before enabling any full-DOF mapping experiments in this plan.

Checklist:
- [ ] P1.1: Add a plan-local probe (or extend `probe_mapping_stage_a_context_metrics.py`)
  to:
  - Call `build_mapping_stage_a_context` to obtain `context.bragg_zero_iter`.
  - Build the Stage A simulator path (HKL grid, beam_config, crystal_config,
    detector configs) using the same HKL indices, calibration, and
    `sqrt(spot_scale_override)` as `simulate_forward_once`, with:
    - `log_scale = 0.0`
    - `log_cell_*_delta = 0.0`
    - `angle_*_raw = 0.0`
    - `orientation_vec = 0.0`
  - Run this "no-op Stage A" once to obtain `bragg_stage_a_noop`.
- [ ] P1.2: Compute diagnostics:
  - Global: `max_abs_diff`, `mean_abs_diff` between `bragg_zero_iter` and
    `bragg_stage_a_noop`.
  - Per-ROI: CC(data, `bragg_zero_iter`) vs CC(data, `bragg_stage_a_noop`), using
    the loss mask from `RefinementInputs`.
- [ ] P1.3: If discrepancies are non-negligible, compare:
  - Detector configs (pixel size, beam center, ROI cropping).
  - Beam configs (flux, exposure, beamsize).
  - N_cells usage and sample clipping flags.
  - Any differences in HKL grid device/dtype.
  Resolve these until `bragg_stage_a_noop` is numerically close to
  `bragg_zero_iter` at the ROI level.

Artifacts:
- `stage_a_refgeom_adam_debug/<ts>/forward_model_probe.json` with global and
  per-ROI metrics.

## Phase 2 — Loss-Definition Alignment

Objective: Ensure the Stage A helper's chi-squared loss matches the mapping
diagnostics at the mapping point.

Checklist:
- [ ] P2.1: At the mapping point (no Stage A deltas), compute:
  - `chi2_mapping`: from `simulate_forward_once` diagnostics (`diagnostics["chi_squared"]`).
  - `chi2_stage_a`: using `_compute_variance_weighted_loss` on
    `bragg_zero_iter` vs `inputs.target` with the Stage A tensors:
    `sigma_readout`, `loss_mask`, `sigma_floor_value`.
- [ ] P2.2: Confirm `chi2_stage_a ≈ chi2_mapping` within numerical tolerance.
  If not, inspect:
  - Variance calculation: `bragg + sigma^2` vs mapping's `variance_raw`.
  - Floor/clamp behavior: `max(variance_raw, sigma_floor^2)` and
    `sigma_floor_value` consistency.
  - Loss mask: same pixels included in both computations.

Artifacts:
- `stage_a_refgeom_adam_debug/<ts>/loss_alignment.json` capturing both chi-squared
  values and their difference.

## Phase 3 — Local Sensitivity Around Mapping Solution

Objective: Understand how small perturbations of each Stage A parameter affect
Stage A chi-squared and per-ROI mapping CC.

Checklist:
- [ ] P3.1: For each parameter block:
  - `log_scale`
  - `log_cell_a_delta`, `log_cell_b_delta`, `log_cell_c_delta`
  - `angle_alpha_raw`, `angle_beta_raw`, `angle_gamma_raw`
  - components of `orientation_vec`
  perform small ±ε perturbations around zero (e.g. ε chosen so that physical
  changes are ~1%) while keeping all other parameters at zero.
- [ ] P3.2: For each perturbation:
  - Rebuild the crystal config and run a single forward pass (matching the
    mapping forward model).
  - Compute Stage A chi-squared (`_compute_variance_weighted_loss`) and per-ROI
    CC vs `bragg_zero_iter`.
- [ ] P3.3: Summarize directions where:
  - Chi-squared decreases but CC systematically drops.
  - Gradients appear extremely steep (suggesting the optimizer step size should
    be reduced or that regularization is needed).

Artifacts:
- `stage_a_refgeom_adam_debug/<ts>/local_sensitivity.json` capturing per-parameter
  deltas in chi-squared and median CC.

## Phase 4 — Single-Step Adam Experiment

Objective: Inspect the very first Adam step and its effect on parameters,
chi-squared, and CC.

Checklist:
- [ ] P4.1: Modify the mapping Adam helper to support "single-step debug" mode:
  - Run Adam for exactly 1 iteration (or a very small number) starting from
    the mapping solution.
  - Use a small learning rate (e.g. 1e-4).
- [ ] P4.2: Log:
  - Parameter values before/after (`log_scale`, cell deltas, angles,
    orientation_vec).
  - Stage A chi-squared before/after.
  - Median CC_before/CC_after vs `bragg_zero_iter`.
- [ ] P4.3: Determine whether the first step already moves into a CC-degrading
  region and which parameters dominate the change.

Artifacts:
- `stage_a_refgeom_adam_debug/<ts>/single_step_adam.json` with parameter deltas
  and metrics.

## Phase 5 — Block-wise DoF Isolation

Objective: Identify which subset of Stage A parameters is responsible for CC
collapse when using Adam on the mapping context.

Checklist:
- [ ] P5.1: Run a small set of mapping Adam variants, all using the matched
  forward model and loss:
  - Variant A: scale-only (log_scale).
  - Variant B: scale + cell deltas (fixed orientation).
  - Variant C: scale + orientation (fixed cell).
  - Variant D: full Stage A (current).
- [ ] P5.2: For each variant, run a short Adam sequence (e.g. 10–20 steps with
  conservative learning rates) and record:
  - Stage A chi-squared initial/final.
  - Median CC_before/CC_after vs mapping "before".
- [ ] P5.3: Identify the first variant that produces a significant CC degradation
  and focus subsequent debugging on its DoFs.

Artifacts:
- `stage_a_refgeom_adam_debug/<ts>/block_dof_results.json` summarizing
  chi-squared and CC deltas per variant.

## Phase 6 — Decision and Mitigation

Objective: Decide how mapping-based vis helpers should treat Stage A geometry,
based on findings from Phases 1–5.

Checklist:
- [ ] P6.1: If full Stage A geometry appears fundamentally unstable for
  mapping-based CC (e.g. many directions where chi-squared improves while CC
  collapses), document this as a limitation:
  - Prefer scale-only refinement for mapping-based visuals.
  - Consider disabling geometry DoFs in mapping helpers by default and gating
    them behind an explicit debug flag.
- [ ] P6.2: If a stable parameter subset is identified (e.g. tightly bounded
  cell deltas with small angles), update the mapping helper configuration:
  - Narrow bounds.
  - Reduce learning rates for sensitive parameters.
  - Optionally add regularization terms or trust-region heuristics.
- [ ] P6.3: Update TOOLING-VIS-001 docs (`implementation.md` and this plan) and
  the fix-plan ledger entry in `docs/fix_plan.md` with a concise summary of
  the decision, rationale, and any changes to mapping-based vis behavior.

Artifacts:
- Updated docs and ledger entries; final debug run telemetry under
  `stage_a_refgeom_adam_debug/<ts>/`.
