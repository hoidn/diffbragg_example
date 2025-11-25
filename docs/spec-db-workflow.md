# spec-db-workflow.md — Workflow and Staging (Normative)

Overview (Normative)
- Purpose: Specify the end‑to‑end pipeline from data ingestion through masking/calibration to simulation, loss, and staged refinement.

Status
- Applies to the `nanobrag_torch` backend, which is implemented but non‑default. The CLI currently defaults to DiffBragg (`--backend diffbragg`); `--backend nanobrag` enables the torch path (Stage A by default, Stage B/C behind flags). DiffBragg may diverge from these steps.

Pipeline (Normative)
1) Ingest Experiment/Reflections (DIALS/dxtbx)
   - Read `.expt` and `.refl`; filter by `id == exptIdx`.
   - Extract panel geometry (origin, axes, pixel size, image size, directed distance, beam centre) and beam/crystal parameters.
2) Background Estimation (simtbx)
   - Call `get_roi_background_and_selection_flags` to produce `background_image` with −1 outside ROIs and collect ROI bboxes + pids.
   - Optional parity: recompute background using a DIALS trusted mask rather than `data < 0`.
3) Mask Preparation
   - Trusted mask (tuple of flex.bool per panel) SHALL be converted to boolean arrays `[panel, slow, fast]`.
   - Simulator mask SHALL be 0/1 floats (1=include). Loss mask SHALL be `(background >= 0) ∧ trusted_mask`.
4) Calibration Policy (ADU vs Photons)
   - If `--adu-per-photon` is provided, target SHALL be converted to photons by dividing by this factor; else target remains in ADU.
   - A learnable global positive scale SHALL be included when training in ADU; recommended initialization is mean(target)/mean(sim_initial) over a small ROI sample.
5) Per‑Panel Simulation
   - Build one Detector per panel using the DIALS convention, with:
     - Square‑pixel guard and explicit beam centre (swap dxtbx order from `(fast, slow)` to `(beam_center_s, beam_center_f)` in mm).
     - Rotation angles derived from panel axes (fast/slow/normal) via analytic inversion or scitbx helpers (XYZ extrinsic), validated by reconstruction.
   - Note on incident direction: In current engines, `custom_beam_vector` is ignored under DIALS. Mapping fidelity comes from beam‑centre (mm) and panel rotations. For use‑cases requiring an explicit incident direction (normalized −s0), projects MAY build CUSTOM detectors with full custom basis vectors and `custom_beam_vector` behind a feature flag; CUSTOM forces SAMPLE pivot and MUST be parity‑validated on fixtures.
   - Run Simulator per panel and stitch into a full‑frame `Bragg` tensor matching `[panel, slow, fast]`.
   - ROI‑only compute MAY be used by constructing cropped Detectors per ROI (with beam centre shifted by crop offsets in mm) and stitching outputs.
6) Loss (Variance-Weighted / Chi-Squared)
   - Loss SHALL be `L = Sum( (I_model - I_obs)^2 / V_detached )` over trusted pixels, where `I_model` is the current Bragg+background prediction and `I_obs` is the background-subtracted target from `prepare_refinement_inputs`.
   - The variance term SHALL follow `docs/spec-db-core.md`: `V = I_model + sigma_readout^2`, with `sigma_readout` strictly positive and supplied in the same units as `I_obs` (typically via `--sigma-rdout` and/or calibrated sigma maps).
   - `V_detached` denotes this variance term detached from the computation graph (IRLS) with a physical lower bound `V = max(I_model + sigma_readout^2, sigma_floor^2)`. The clamp exists to prevent infinite weights when `I_model → 0`; telemetry SHALL record `sigma_floor` and the fraction of pixels where the clamp engaged. Implementations MAY reuse the canonical helper `dbex.physics.loss._compute_variance_weighted_loss` to avoid divergence from `docs/spec-db-core.md`.

Calibration & Unit Conventions (Normative Addendum)
- Precedence ladder (highest → lowest): torch_config (if provided) → CLI overrides → external_lookup payloads → refined MTZ metadata → raw MTZ defaults → hardcoded defaults. When torch_config and CLI both define the same field (gain/adu_per_photon, sigma_floor, spot_scale_override, beam flux/exposure, beamsize_mm, N_cells) and disagree, the run SHALL fail with a clear error (no silent overrides). Otherwise, pick the highest available tier and emit provenance; refined MTZ, when requested, SHALL be consumed or the run SHALL fail fast (no silent fallback to raw). Sigma_readout SHALL follow the canonical ladder in `spec-db-core.md` §Variance inputs (map → scalar → external tiles → error); MTZ metadata and hardcoded defaults MUST NOT be used as sigma sources.
- ADU↔photon policy: A run SHALL choose a single unit mode. If `adu_per_photon > 0`, targets, sigma_readout, and sigma_floor SHALL be converted at ingest; the chosen unit_mode (ADU|photon) and gain MUST be recorded in telemetry. Spot-scale application in ADU mode SHALL use `sqrt(spot_scale_override)` post-sim with log_scale as a delta around that baseline; in photon mode, spot_scale_override applies directly (no sqrt).
- Sigma sourcing (Spec‑DB conformance): sigma_readout MUST come from (in order) sigma map, sigma scalar, or external tiles. If none are present, the CLI SHALL fail. Shapes must match the target or the run fails. Legacy hardcoded defaults (e.g., ~3 ADU) are non‑conformant. See `spec-db-core.md` §Variance inputs for the canonical precedence.
- sigma_floor precedence is CLI > external_lookup > instrument default (≥1 photon or ADU-equivalent) and MUST be recorded with provenance; a missing sigma_floor is non‑conformant even if the run executes.
- Geometry/mask/ROI invariants (shared across backends): arrays are `[panel, slow, fast]`, beam-centre swap per config_crosswalk, mask polarity True=trusted; ROI bboxes `(x0, x1, y0, y1)` with x1/y1 exclusive. Background sentinels (e.g., -1) MUST be masked consistently in loss/variance computations.
- Required calibration fields for Spec‑DB conformance:
  - `spot_scale_override`: MUST be provided (typically via `torch_config`).
  - `sigma_floor`: MUST be provided via CLI or config; instrument defaults are allowed only when explicitly surfaced in telemetry.
  - `sigma_readout`: MUST follow the precedence in `spec-db-core.md`.
  - `beam_flux` and `beam_exposure`: SHOULD be provided via calibration config; if absent, implementations MAY use documented fallbacks but MUST record provenance (e.g., `calibration_source_flux`).
  - `beamsize_mm` and `N_cells`: MAY default to `None` and `1`, respectively, but the effective values and provenance MUST be recorded.
- Telemetry/provenance: `/torch_diagnostics` SHALL include the required keyset defined in `spec-db-interfaces.md` (HDF5 Output Schema), covering calibration sources/values (spot_scale_override, sigma_readout/sigma_floor with provenance, beam flux/exposure, beamsize_mm, N_cells, unit_mode/gain), HKL source/path, interpolation/halo flags, device profile, scale baselines/clamps, and any precedence conflicts or fallbacks.
- Normative conversion sequence: (1) ingest metadata, decide unit_mode/gain; (2) apply gain if needed to target/sigma*; (3) resolve calibration payload via precedence; (4) build HKL grid (refined preferred, else raw; fail if refined requested but missing); (5) construct configs/context with calibration (log_scale_baseline = log(sqrt(spot_scale_override)) in ADU mode, 0 in photon mode); (6) apply variance model `V = max(I_model + sigma_readout^2, sigma_floor^2)`; (7) emit full telemetry.

7) Refinement Protocol Architecture
   - **Engine Contract:** The internal Python API (`RefinementEngine` or equivalent) SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow.
   - **Standard Stages (Normative Definitions):**
     - **Interpolation policy (normative)** — canonical Stage physics across shards (see also `spec-db-core.md` §Interpolation Policy):
       - Stage A (geometry/scale): `interpolation=False` (nearest‑neighbor |F|) is canonical, matching the legacy DiffBragg geometry loop. Tricubic with a haloed |F| grid MAY be used as an explicitly tagged experimental mode; such runs are non‑canonical and SHALL record the mode in telemetry.
       - Stage B: `interpolation=True` REQUIRED; halo REQUIRED. Any `default_F` fallback with interpolation enabled is a failure.
       - Stage C: `interpolation=True` REQUIRED; halo REQUIRED. Any `default_F` fallback with interpolation enabled is a failure.
     - **Stage A (Geometry & Scale):**
       - Trainable (normative): Unit cell logs/angles, orientation (quaternion → XYZ), global scale. Implementations SHOULD align their parameterization with the `ExperimentModel(param_init="stage_a")` interface in `nanobrag_torch.models.experiment` (see `docs/nanobrag_api.md`).
       - Fixed: Structure factors, detector geometry, source spectrum (unless an explicit Stage‑A detector/beam extension is enabled per implementation-specific initiative).
       - Physics (Normative): For canonical Stage‑A geometry refinement and all Spec‑DB conformance selectors (DB‑AT‑024/027/028/029), the simulator SHALL use nearest‑neighbor |F| sampling of the dense |F| grid (`interpolation=False`). This matches the legacy dbex→DiffBragg configuration (`interpolate=0` in the Python wrappers). Tricubic (`interpolation=True`) is non‑canonical and MAY be used only in explicitly tagged experimental modes; such runs SHALL NOT claim Spec‑DB Stage‑A conformance and SHALL record interpolation/halo status in telemetry.
       - Mapping zero-point invariant (normative for mapping‑aligned runs):
         - For any Stage‑A configuration that claims DB‑AT‑024 mapping parity (see `docs/spec-db-conformance.md`), zero geometry parameters (all cell/angle/orientation deltas equal to zero) and baseline scale MUST reproduce the DB‑AT‑024 mapping Bragg tensor produced by `simulate_forward_once`.
         - Implementations SHALL satisfy, at the Stage‑A zero point:
           - `U(0) = U₀`, `B(0) = B₀`, and `A*(0) = U₀ @ B₀ = A*_mapping`,
             where `A*_0 = crystal.get_A()`, `c₀` is the baseline unit cell from dxtbx, `B₀ = B(c₀)` is the Busing–Levy reciprocal metric tensor, and `U₀ = A*_0 @ B₀⁻¹` as defined in `spec-db-core.md`.
         - When `crystal_overrides` are used instead of MOSFLM A* injection, Stage‑A implementations SHALL encode the mapping orientation via a baseline misset (e.g., `baseline_misset_deg`) and apply only deltas on top of that baseline (e.g., `misset_deg = baseline_misset_deg + delta_misset`), so that the Stage‑A zero point is identical to the mapping forward model.
       - Stage‑A parameterization constraints (normative):
         - Orientation and cell parameterizations SHALL be expressed as increments relative to the mapping baseline:
           - Orientation DOFs (Euler, axis‑angle, quaternion, etc.) MUST represent a small rotation `ΔR(params)` such that `U(params) = ΔR(params) @ U₀`.
           - Cell DOFs MUST produce `B(params)` via a metric‑tensor computation consistent with Busing–Levy and dxtbx conventions, applied to a perturbed cell around the baseline.
         - The Stage‑A forward simulator SHALL consume `A*(params)` constructed only as `U(params) @ B(params)` from those increments.
         - Implementations SHALL NOT:
           - derive a new `(Ū,B̃)` pair by decomposing `A*` at runtime and then use `(Ū,B̃)` in place of `U₀,B₀`, or
           - rely on cached `A*` at the zero point while using a different `U,B` reconstruction for non‑zero parameters in the same mapping‑aligned run.
         - Quaternion‑based schemes are permitted, but only when they encode `ΔR` on top of `U₀` and satisfy the zero‑point and incremental invariants above.
       - Stage‑A “no‑op” definition (normative for mapping‑aligned tooling): a Stage‑A configuration with all geometry deltas equal to zero and baseline scale that, when passed through the Stage‑A forward simulator, produces a Bragg tensor that matches the DB‑AT‑024 `simulate_forward_once` output for the same `RefinementInputs` and HKL grid (within numerical tolerance). Any plan‑local Stage‑A helper (e.g., debug/vis drivers under TOOLING‑VIS‑001) that claims mapping parity SHALL treat this Stage‑A no‑op as its zero point and SHALL validate zero‑point equality against the mapping Bragg as part of its initialization checks.
     - **Stage B (Structure Factors — optional):**
       - Trainable: Per-reflection Fhkl multipliers mapped to unique ASU indices SHALL be the default (Parity Mode).
       - Fallback: Aggregated per-shell modifiers (Shell Mode) are PERMITTED as an optimization or regularization strategy but MUST NOT be the default.
       - Physics: Tricubic interpolation (`interpolation=True`) with ±1 HKL halo is MANDATORY.
       - **Implementation Status (2025-11-24):** Per-reflection mode implemented in TORCH-REFINE-004 (Phases 6-9). ASU mapping via cctbx.miller symmetry operations, dynamic optimizer selection (LBFGS <10K params, Adam ≥10K params per spec:107), gradient flow validated. Shell mode remains available as fallback via `stage_b_mode="shell"` config parameter per spec:60.
     - **Stage C (Detector):**
       - Trainable: Per-panel translation along detector normal (distance offsets).
       - Fixed: Crystal, scale, Fhkl.
       - Physics: Tricubic interpolation (`interpolation=True`) is MANDATORY so detector motion yields differentiable HKL gradients.

### Canonical Initial Configuration (Normative)

Mapping-aligned configuration (normative): Any run claiming mapping parity SHALL reuse the DB‑AT‑024 DIALS→Torch mapping pipeline (geometry, masks, sigma, HKL grid, calibration) and satisfy the Stage‑A zero-point invariant enforced by DB‑AT‑027 (zero deltas + baseline scale reproduce the mapping Bragg tensor within tolerance). The bullets below define the canonical assets for that configuration.

For workflows whose goal is to validate physics and mapping fidelity (DB‑AT‑024, DB‑AT‑02x selectors, and Stage‑A visualization under TOOLING‑VIS‑001), the initial configuration for Stage‑A–style refinement and diagnostics SHALL be the “mapping configuration” defined in `docs/spec-db-conformance.md` (§DB‑AT‑024 DIALS→Torch Mapping), i.e.:

- Geometry:
  - Prefer DiffBragg-refined fixtures when available:
    - `tests/fixtures/golden_data/simple_cubic/refined.expt`
    - `tests/fixtures/golden_data/simple_cubic/refined.refl`
  - Otherwise fall back to canonical `refGeom.expt` / `refGeom.refl` under the repository root.
- Structure Factors:
  - Prefer refined structure factors:
    - `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz`
  - Otherwise fall back to the canonical `scaled.mtz`.
- Calibration:
  - Use `tests/fixtures/golden_data/simple_cubic/config_torch.json` to provide `spot_scale_override`, beam flux/exposure, beamsize, and `N_cells` to the mapping helper.
- Trusted Mask and Sigma:
  - Trusted mask: `747_mask.pkl` decoded as `[panel, slow, fast]` with True=trusted.
  - Sigma: external-lookup `sigma_readout_map` when present and valid; otherwise a documented constant ADU floor per `spec-db-core.md`.
- RefinementInputs:
  - Prepared exactly as specified for DB‑AT‑024 in `docs/spec-db-conformance.md` (loss mask `(background >= 0) ∧ trusted_mask`, background-subtracted targets, sigma broadcast and zeroed outside the loss mask).
- Zero-Iteration Model:
  - The canonical zero-iteration Bragg stack used for Stage‑A “before” diagnostics SHALL be the output of `simulate_forward_once` applied to the configuration above (refined MTZ + calibration when available, or raw MTZ + calibration fallback), and SHALL use the same variance-weighted chi-squared loss and variance model as the Stage‑A objective.

Implementations MAY explore alternative initial configurations (e.g., deliberately perturbed geometry or unrefined MTZ) for robustness or performance experiments, but:

- Such configurations MUST NOT be used when running DB‑AT‑024 / DB‑AT‑02x selectors or TOOLING‑VIS‑001 canonical Stage‑A visuals.
- Any divergence from the mapping configuration in those contexts MUST be treated as non‑canonical and documented explicitly (including thresholds and artifacts) before being considered Spec‑DB‑conformant.

### Stage Smoke Dataset Policy (Normative)
- Purpose: Provide a fast-running refinement harness that exercises the Stage A/B/C code paths without exhausting GPU VRAM. The canonical `refGeom` assets remain authoritative for DB‑AT selectors and parity work; the cropped `refGeom_small` fixture is only for smoke/perf loops.
- `refGeom_small` assets SHALL live under `sp.proc/refGeom_small/` with provenance recorded via `plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py`. The README in that directory SHALL capture the crop window, ROI count, and checksums.
- The crop window is 1024×1024 pixels centered on the detector. When filtering by `id == exptIdx` (the still used by Stage smokes) this preserves 29 ROIs. This satisfies the smoke-test requirement (exercise the refinement code and telemetry) while cutting tensor area by ~76%. Full-detector runs (all 92 ROIs) remain mandatory for DB‑AT/DB‑PARITY selectors.
- Pytest harnesses SHALL expose a dataset selector: `--smoke-detector-size={small,full}` with matching env override `DBEX_SMOKE_DETECTOR_SIZE`. Small is the default and SHALL relax improvement gates (structural telemetry checks still apply). Full must preserve all Stage A/B/C gates and parity thresholds.
- Stage smokes SHALL emit telemetry artifacts (JSON) when `DBEX_SMOKE_TELEMETRY_PATH` is set so perf deltas and runtime samples are recorded. DB‑AT selectors MAY disable this logging.
- DB‑AT and workflow selectors (DB-AT-02x) SHALL assert `--smoke-detector-size=full` (or `DBEX_SMOKE_DETECTOR_SIZE=full`) before execution to guarantee canonical detector dimensions. A failing selector MUST error if a small-detector dataset is detected.

Optimization Strategy (Normative)
- Default optimizer SHALL be L‑BFGS for Stage A and Stage C, implemented via `torch.optim.LBFGS` with a closure that recomputes the full loss.
- Parameterization MUST enforce constraints without bound constraints (e.g., logs for lengths, bounded map for angles, quaternion→XYZ for misset).
- ROI minibatching MAY be used inside the L‑BFGS closure for cost control, provided periodic full‑image validation confirms descent (documented in logs).
- Stage B (structure-factor modifiers) MAY use L‑BFGS or Adam; default SHOULD be L‑BFGS unless per-reflection parameter counts make limited-memory methods impractical.

Gradient Hygiene (Normative)
- Inputs to optimization MUST be torch tensors constructed at loop start; the loss MUST be computed purely from torch tensors on the same graph.
- The optimization path (LBFGS closure and any functions it calls) MUST NOT call `.cpu()`, `.detach()`, `.numpy()`, `.item()`, or run under `with torch.no_grad()` for values that influence the forward pass.
- HDF5 persistence and viewer artifacts MUST be written from detached copies outside the optimization step.
- Stage parameter sets MUST be enumerated per stage; non‑active parameters are treated as constants.
- Stage B assumes differentiable HKL interpolation in nanobrag_torch; if it is unavailable or broken, treat this as an upstream defect rather than introducing non‑differentiable fallbacks in the optimization path.

Outputs (Normative)
- Full‑frame `Bragg` tensor on the simulator device; HDF5 outputs MAY mirror viewer layout for ROIs.

References (Informative)
- docs/spec-db-core.md; docs/config_crosswalk.md; plans/nanobrag_integration_plan.md.
