# spec-db-conformance.md — Acceptance Tests (Normative)

Overview (Normative)
- Purpose: Define executable acceptance tests (DB‑AT‑XXX) that collectively certify a build as conformant with Spec DB.

Status
- These acceptance tests target the forthcoming `nanobrag_torch` backend and are currently placeholders. They are not wired to the existing DiffBragg CLI.
- Until the torch backend is available, use `python -m dbex.refine_one` (see `dbex/refine_one.py:5-26`) and treat these tests as future work.
Conformance Profiles (Normative)
- Forward Equivalence Profile:
  - DB‑AT‑001 Forward equivalence smoke (DiffBragg vs `nanobrag_torch` forward pass; run without refinement and compare coarse ROI metrics per `plans/nanobrag_integration_plan.md` Phase 1).
- Gradient‑Safe Profile:
  - DB‑AT‑010 Gradcheck on refined parameters (cell logs/angles, quaternion seed → XYZ).
  - DB‑AT‑011 No graph breaks under runtime mask/loss operations.
- Workflow Integration Profile:
  - DB‑AT‑020 DIALS reflection ingestion (bbox exclusivity, panel ordering) sanity.
  - DB‑AT‑021 Mask polarity and shape conformance (trusted mask → simulator/loss).
  - DB‑AT‑022 ROI background semantics (−1 outside ROI, masked MSE).
  - DB‑AT‑023 ADU vs photons policy (flag honored; scale init for ADU mode).
  - DB‑AT‑024 Mapping consistency (zero‑iteration forward vs data‑minus‑background overlay).
  - DB‑AT‑025 HKL interpolation conformance (tricubic halo): when `crystal.interpolate=True`, the dense |F| grid MUST include a ±1 halo; any default_F fallback is a failure. Stage A is canonically `interpolate=False`; any Stage‑A run that enables interpolation is non‑canonical and SHALL be flagged in telemetry per `docs/spec-db-workflow.md`.
  - DB‑AT‑026 Stage‑A UB parameterization round-trip (zero-point UB/A* consistency).

Acceptance Tests (Normative)
- DB‑AT‑001 Forward equivalence smoke
  - Setup: Using the same `DataLoad` inputs, generate a single forward `Bragg` tensor with the legacy DiffBragg pipeline and the torch bridge (no parameter updates). Compare coarse metrics (ROI correlation ≥ 0.2, localized intensity per `plans/nanobrag_integration_plan.md` Phase 1) and capture visual overlays/logs. Optional trace capture for representative pixels is described in `docs/forward_equivalence.md`. If thresholds are not met, emit diagnostic artifacts instead of failing the run.
  - Expectation: median ROI correlation ≥ 0.2 and ≥90% of sampled ROIs contain a local intensity maximum within the central half-box; failing runs SHOULD attach diagnostic overlays instead of asserting.
  - Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001` (selector MAY xfail when only diagnostic evidence is captured).
- DB‑AT‑020 Reflection ingestion sanity
  - Setup: load .expt/.refl; extract first ROI; slice data with bbox; verify shape, exclusivity, panel ordering.
  - Expectation: `shoebox.shape == (y1-y0, x1-x0)`; panel indices align.
  - Command: `pytest -v tests -k DB_AT_020`
- DB‑AT‑021 Mask polarity and shape
  - Setup: load DIALS trusted mask; convert to simulator mask; verify mask/loss application on sample ROIs.
  - Expectation: simulator zeros masked pixels post‑compute; loss excludes masked/background‑invalid pixels.
  - Command: `pytest -v tests -k DB_AT_021`
- DB‑AT‑022 ROI background semantics
  - Setup: run simtbx background; confirm −1 sentinel outside ROIs; optional recompute with trusted mask.
  - Expectation: sentinel logic correct; ROI coverage matches reflection metadata.
  - Command: `pytest -v tests -k DB_AT_022`
- DB‑AT‑023 Calibration policy
  - Setup: run with and without `--adu-per-photon`; compare scale behavior and loss.
  - Expectation: photon mode yields scale near 1; ADU mode learns positive scale with stable initialization.
  - Command: `pytest -v tests -k DB_AT_023`
- DB‑AT‑024 Mapping consistency
  - Setup: build per‑panel configs from a real Experiment; run a forward pass with initial parameters; evaluate K ROIs (e.g., 32) for correlation and localization.
  - Expectation: median ROI correlation ≥ 0.2 and ≥90% ROIs contain a local intensity maximum within the central half‑box.
  - Command: `pytest -v tests -k DB_AT_024`

- DB‑AT‑026 Stage‑A UB parameterization round-trip
  - Setup:
    - Use a canonical `RefinementInputs`+crystal (e.g., refGeom.expt) and extract the baseline crystal state:
      `U₀ = crystal.get_U()`, `B₀ = crystal.get_B()`, `A*_mapping = U₀ @ B₀`.
  - Procedure:
    1. Initialize the Stage‑A parameterization at `params=0` (all deltas zero; baseline scale).
    2. Construct `U(0), B(0), A*(0)` according to the implementation's parameterization.
    3. Compare `U(0)` vs `U₀`, `B(0)` vs `B₀`, and `A*(0)` vs `A*_mapping` using a specified tolerance (e.g., max_abs_diff and Frobenius norms).
  - Expectation:
    - All three comparisons MUST fall within the documented tolerance; any systematic deviation is a conformance failure.
  - Command (informative example):
    - `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_026` (or equivalent), which runs a small UB round‑trip probe using the Stage‑A parameterization.

## Canonical DIALS→Torch Mapping (DB‑AT‑024)

**Scope (Normative)**
- Defines the canonical pipeline for mapping DIALS geometry and ROIs into `nanobrag_torch` for zero‑iteration forward simulation.
- DB‑AT‑024 SHALL implement this exact pipeline. Implementations claiming conformance to Spec‑DB mapping semantics MUST pass DB‑AT‑024.

**Canonical Assets and Precedence (Normative)**

1. **Experiment / reflections**
   - Primary: `tests/fixtures/golden_data/simple_cubic/refined.expt` and `refined.refl`.
   - Fallback: `refGeom.expt` and `refGeom.refl` at the repository root.
   - The loader SHALL prefer refined assets when present; falling back to legacy `refGeom` SHALL be treated as a degraded mode and annotated in telemetry.

2. **Trusted mask**
   - Source: `747_mask.pkl` at the repository root.
   - Format: DIALS‑pickled tuple of `flex.bool` per panel, True=trusted polarity.
   - The canonical mapping MUST convert this mask to a NumPy stack `[panel, slow, fast]` and use it as the trusted mask when preparing refinement inputs.

3. **Structure factors (MTZ)**
   - Primary: `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz` (refined HKL).
   - Fallback: `scaled.mtz` at the repository root.
   - When the refined MTZ is present, telemetry (`hkl_telemetry`) MUST record `hkl_source="refined"` and the corresponding `hkl_path`. When only `scaled.mtz` is used, the source SHALL be `"raw"`.

4. **Calibration metadata**
   - Source: `tests/fixtures/golden_data/simple_cubic/config_torch.json`.
   - Required fields:
     - `spot_scale_override` (scalar),
     - `beam_flux`, `beam_exposure`,
     - optional `beamsize_mm`,
     - optional `N_cells` (per‑panel domain counts).
   - The calibration dict SHALL be passed verbatim into `simulate_forward_once`, and the simulator MUST honor `spot_scale_override`, flux/exposure, beamsize, and `N_cells` per SCALE‑003/SCALE‑005.

5. **Sigma / readout noise**
   - Primary: external‑lookup sigma map embedded in `sp.proc/idx-0000_sigma_metadata.expt` / `idx-0000_sigma_metadata.sigma_tiles.pkl` (if present), loaded via `DataLoad` → `sigma_readout_map`.
   - Fallback: a scalar sigma_r in ADU (e.g., 3.0 ADU) broadcast to `data.shape`.
   - In either case, `sigma_readout` SHALL be aligned with the target units (ADU for DB‑AT‑024 baseline) and MUST be strictly positive on trusted pixels per `spec-db-core.md`.

**Canonical Pipeline (Normative)**

1. **DataLoad construction**
   - Construct `DataLoad(args)` with:
     - `args.exptName = expt_path` (refined or legacy per precedence above),
     - `args.reflName = refl_path`,
     - `args.exptIdx = 0`,
     - `args.mtzFile = scaled.mtz`,
     - `args.mtzCol = "F,SIGF"`,
     - `args.maskFile = 747_mask.pkl`.
   - `DataLoad` SHALL:
     - Load pixel data via `simtbx.diffBragg.utils.image_data_from_expt(expt)` as `[panel, slow, fast]` (ADU).
     - Compute ROI background and bbox via `get_roi_background_and_selection_flags` with sentinel `background_image == -1` outside ROIs.
     - Load and validate the trusted mask from `747_mask.pkl`, preserving True=trusted polarity.
     - Populate `sigma_readout_map` from external_lookup metadata when available.

2. **RefinementInputs preparation**
   - Let `dl = DataLoad(args)` as above.
   - Define `sigma_readout` as:
     - `dl.sigma_readout_map` (if non‑None and `sigma_readout_map_source == "external_lookup"`), or
     - `np.full_like(dl.data, sigma_r_ADU, dtype=np.float32)` otherwise.
   - Call:
     ```python
     inputs = prepare_refinement_inputs(
         data=dl.data,
         background_image=dl.background_image,
         trusted_mask=dl.trusted_mask,
         bbox=dl.bbox,
         pids=dl.pids,
         detector=dl.detector,
         adu_per_photon=None,  # ADU mode per DB-AT-024 baseline
         sigma_readout=sigma_readout,
         sigma_readout_provenance=(
             "external_lookup" if using_metadata_sigma else "cli_override"
         ),
     )
     ```
   - `prepare_refinement_inputs` MUST:
     - Enforce `[panel, slow, fast]` ordering and bbox `(x0, x1, y0, y1)` semantics.
     - Construct `loss_mask = (background_image >= 0) ∧ trusted_mask`.
     - Background‑subtract ROI pixels (`target = data - background_image` where `background >= 0`, else 0).
     - Zero out `target` and `sigma_readout` where `loss_mask` is False.
     - Return `RefinementInputs` with `target`, `loss_mask`, `panel_slices`, `trusted_mask`, and `sigma_readout` all aligned per `spec-db-core.md`.

3. **Zero‑iteration forward simulation**
   - Determine structure factors:
     - If refined MTZ is present and loadable: `hkl_indices, hkl_amplitudes = load_refined_mtz(refined_mtz)`, `hkl_source="refined"`.
     - Else: `hkl_indices, hkl_amplitudes = dl.F.indices(), dl.F.data()`, `hkl_source="raw"`.
   - Load calibration via `calibration = load_calibration_metadata(config_torch.json)`.
   - Call:
     ```python
     bragg, diagnostics = simulate_forward_once(
         inputs=inputs,
         detector=dl.detector,
         beam=dl.beam,
         crystal=dl.crystal,
         experiment=dl.Expt,
         hkl_indices=hkl_indices,
         hkl_amplitudes=hkl_amplitudes,
         calibration=calibration,
         hkl_source=hkl_source,
         hkl_path=str(mtz_path),
         device="cpu",
     )
     ```
   - `simulate_forward_once` MUST:
     - Build `BeamConfig`, `CrystalConfig`, and `DetectorConfig` per `docs/dxtbx_api.md` and `docs/nanobrag_api.md` (distance from `panel.get_directed_distance()`, beam centre mm from `panel.get_beam_centre(s0)` with (fast,slow)→(s,f) swap, A* from `crystal.get_A()`, etc.).
     - Attach a dense P1 |F| grid built from `hkl_indices/hkl_amplitudes` (with halo and interpolation semantics per `spec-db-core.md` / `docs/nanobrag_api.md`).
     - Produce a Bragg stack `bragg` shaped `[panel, slow, fast]` in target units matching `inputs.target`.
     - Compute diagnostics including `masked_mse`, `chi_squared`, `variance_floor_clamp_fraction`, and `hkl_telemetry` fields.

**DB‑AT‑024 as Enforcement (Normative)**

- DB‑AT‑024 SHALL instantiate this exact pipeline (asset precedence, `DataLoad` construction, `prepare_refinement_inputs`, `simulate_forward_once`) and then evaluate per‑ROI metrics:
  - Correlation between `bragg[pid, y0:y1, x0:x1]` and `inputs.target[pid, y0:y1, x0:x1]` on the loss mask.
  - Localization success (whether the brightest model pixel lies within the central half‑box of each ROI), as defined above.
- The following thresholds are normative for conformance:
  - Median ROI correlation ≥ 0.2.
  - Localization success rate ≥ 90% of sampled ROIs.
- Any implementation that diverges from this mapping (e.g., different geometry source, different trusted mask, alternate loaders) SHALL either:
  - Prove equivalence by still satisfying DB‑AT‑024 under the same thresholds, or
  - Be documented as non‑canonical and NOT advertised as Spec‑DB‑conformant for DIALS→Torch mapping.

**Mapping-Aligned Stage‑A Initialization (Normative)**

- For any Stage‑A–style refinement or visualization that claims mapping parity (including TOOLING‑VIS‑001 Stage‑A ROI visuals), the initial configuration SHALL be derived from this DB‑AT‑024 mapping pipeline:
  - Geometry, mask, sigma, and `RefinementInputs` MUST be constructed exactly as above.
  - The initial model (`bragg_zero_iter`) used for “before” loss and visuals SHALL be the `simulate_forward_once` Bragg output for that configuration.
- Stage‑A geometry parameterizations that refine unit cell and/or orientation (cell logs/angles, quaternion→XYZ) over this mapping baseline SHALL satisfy the following zero‑point invariant:
  - At zero geometry parameters (all cell deltas and orientation deltas equal to zero) and baseline scale, the Stage‑A forward simulator MUST reproduce the DB‑AT‑024 `simulate_forward_once` Bragg tensor for the same `RefinementInputs` and HKL grid, within numerical tolerance. Implementations MAY use either:
    - MOSFLM A* injection from `crystal.get_A()` with `misset_deg = [0,0,0]`, **or**
    - A baseline misset tensor (e.g., `baseline_misset_deg`) that encodes the mapping orientation, combined with geometry deltas (e.g., `misset_deg = baseline_misset_deg + delta_misset`) when `crystal_overrides` are used and MOSFLM A* injection is disabled.
  - Any mapping‑aligned Stage‑A helper that introduces `crystal_overrides` or orientation deltas MUST enforce this zero‑point equality as part of its initialization; helpers which cannot reconstruct the DB‑AT‑024 mapping Bragg at zero parameters SHALL NOT be advertised as mapping‑aligned and SHALL NOT be used as the “before” reference in DB‑AT selectors or TOOLING‑VIS‑001 visuals.
  - Mapping, Stage‑A “no‑op”, and mapping‑aligned Stage‑A refinement SHALL be implemented as parameterizations of a single forward simulator path: introducing a new forward implementation for mapping‑aligned helpers is only permitted when that implementation demonstrably satisfies the same zero‑point equality against `simulate_forward_once` for the canonical `RefinementInputs` and HKL grid.
- Stage‑A refinements that start from different initial configurations (e.g., perturbed geometry or alternate MTZ) MAY exist for robustness/performance experiments, but MUST NOT be treated as canonical mapping‑aligned runs, and MUST NOT be used as the baseline for DB‑AT selectors or mapping‑aligned visualization initiatives.

- DB‑AT‑025 HKL interpolation conformance (tricubic halo)
  - Setup: enable `crystal.interpolate=True` and run a forward pass using a dense |F| grid built with a declared ±1 halo (metadata flag). Capture telemetry for default_F fallback count.
  - Expectation: halo present in metadata; default_F fallback count == 0 (no out‑of‑bounds lookups while interpolating). Applies to every stage that enables interpolation. Canonical Stage A is `interpolate=False`; any Stage‑A run that turns interpolation on is non‑canonical and SHALL record that mode in telemetry.
  - Command: (selector TBD; activate once telemetry and halo flag are exposed)

- DB‑AT‑027 Stage‑A zero‑point mapping equivalence
  - Goal: Ensure the Stage‑A zero‑parameter forward model is equivalent to the DB‑AT‑024 mapping forward model at the same geometry, HKL grid, and calibration.
  - Setup:
    - Dataset: canonical refGeom/simple_cubic golden data used by DB‑AT‑024.
    - Build `DataLoad` over refined geometry (`refined.expt`/`refined.refl` when present, else legacy `refGeom.{expt,refl}`).
    - Build `RefinementInputs = prepare_refinement_inputs(...)` with the same sigma policy as DB‑AT‑024 (external sigma tiles or 3.0 ADU default).
    - Build `MappingStageAContext = build_mapping_stage_a_context(DataLoad, device="cpu")` and reuse its:
      - `inputs`, `bragg_zero_iter`, `sigma_floor_value`,
      - refined HKL indices/amplitudes, calibration dict (`spot_scale_override`, `beam_flux`, `beam_exposure`, `beamsize_mm`, `N_cells`).
  - Procedure:
    1) Mapping baseline (reuse DB‑AT‑024):
       - Let `bragg_mapping = bragg_zero_iter` and `diagnostics = context.diagnostics` from `build_mapping_stage_a_context`.
       - Define `masked_pixels = diagnostics["variance_floor_masked_pixels"]`.
       - Define `chi2_mapping = diagnostics["chi_squared"]` and `chi2_mapping_per_pixel = chi2_mapping / masked_pixels`.
    2) Stage‑A zero‑point forward:
       - Build a dense HKL grid using the same HKL indices/amplitudes as mapping:
         `hkl_grid, hkl_metadata, _ = build_structure_factor_grid(indices=context.hkl_indices, amplitudes=context.hkl_amplitudes, device="cpu", halo=<matching mapping>)`.
       - Construct Stage‑A forward components (beam_config, detector models, crystal config) using the same calibration dict as mapping (including `spot_scale_override`/N_cells).
       - Evaluate the Stage‑A forward at zero parameters (log_scale=0.0, all cell/angle/orientation deltas = 0, no detector/beam offsets) to obtain `bragg_stagea_zero`.
       - Zero‑point MUST honor the Stage‑A mapping invariant: `U(0)=U₀`, `B(0)=B₀`, `A*(0)=A*_mapping` as defined in `spec-db-workflow.md`.
    3) Stage‑A χ² at mapping stack:
       - Using `inputs.target`, `inputs.loss_mask`, `inputs.sigma_readout`, and `sigma_floor_value` from mapping, compute Stage‑A’s variance‑weighted χ² on the mapping stack:
         `chi2_stagea_at_mapping = _compute_variance_weighted_loss(bragg_mapping, target, loss_mask, sigma_readout, sigma_floor_sq)`.
  - Expectations (all normative):
    - Forward‑model equality:
      - `max_abs_diff(bragg_stagea_zero − bragg_mapping) ≤ 2.0e2` (ADU units), calibrated to existing TOOLING‑VIS zero‑point probes for the simple_cubic fixture. This bound MAY be tightened in future once Stage‑A and mapping share an exact forward implementation.
      - `mean_abs_diff(bragg_stagea_zero − bragg_mapping) ≤ 1e‑3`.
    - Variance‑weighted χ² equality:
      - `|chi2_stagea_at_mapping − chi2_mapping| / chi2_mapping ≤ 1e‑3`, where the χ² is the canonical PHYSICS‑LOSS variance‑weighted objective with detached denominator (`V = I_model + sigma_readout²`, clamped to `sigma_floor²`); the current helper implementing this is `dbex.physics.loss._compute_variance_weighted_loss` (informative).
    - χ² per pixel sanity:
      - `chi2_mapping_per_pixel ≤ 1e2` for the canonical simple_cubic mapping fixture (value calibrated to current DB‑AT‑024 metrics; future tightening is permitted once the forward model and calibration are refined).
  - Command: a dedicated Stage‑A mapping test (e.g. `pytest -v tests -k DB_AT_027`) SHALL enforce this contract for the simple_cubic fixture.

- DB‑AT‑028 Stage‑A loss‑scale and clamp sanity
  - Goal: Ensure Stage‑A χ² values remain in a physically reasonable regime on the canonical Stage‑A smoke dataset, and that sigma_floor acts as a guardrail rather than the dominant regime.
  - Setup:
    - Dataset: Stage‑A smoke dataset from `test_stage_a_expansion` (sp.proc refGeom_small/refGeom_full).
    - Geometry: deterministic perturbation from `create_perturbed_geometry` (+2/+1/+1% cell stretch, +1.5° Z‑misset).
    - HKL grid: canonical Stage‑A policy uses nearest‑neighbor (`interpolation=False`). Haloed tricubic (`enable_hkl_interpolation=True`) MAY be exercised as a non‑canonical, explicitly tagged mode; selectors SHALL treat it as such.
    - Sigma policy: same as Stage‑A smoke (external tiles when available, else 3.0 ADU).
    - Config: Stage‑A LBFGS `RefinementConfig` as used by the smoke test (ROI sampling, warm cache enabled).
  - Procedure:
    1) Run `run_nanobrag_refinement` with Stage‑A enabled and Stage B/C disabled under the canonical Stage‑A expansion configuration.
    2) From Stage‑A telemetry (`telemetry_A`):
       - Extract `chi_squared_trace_full = [(iter, chi2)]`.
       - Extract `variance_floor_masked_pixels` and `variance_floor_clamp_fraction`.
    3) Define:
       - `chi2_initial = chi_squared_trace_full[0][1]`, `chi2_final = chi_squared_trace_full[-1][1]`.
       - `chi2_per_pixel_initial = chi2_initial / variance_floor_masked_pixels`.
       - `chi2_per_pixel_final = chi2_final / variance_floor_masked_pixels`.
  - Expectations (normative for the Stage‑A smoke dataset):
    - Static χ² per masked pixel:
      - `chi2_per_pixel_initial ≤ 1e2`.
      - `chi2_per_pixel_final   ≤ 1e2`.
      - `chi2_per_pixel_final ≤ chi2_per_pixel_initial` (Stage‑A SHALL not make χ² per pixel worse).
    - Sigma‑floor clamp sanity:
      - `0.0 ≤ variance_floor_clamp_fraction ≤ 1.0`.
      - For canonical refGeom smoke, `variance_floor_clamp_fraction < 0.5` at both initial and final points; other datasets MAY adopt different fixture‑specific bands, documented alongside their acceptance tests.
      - If `variance_floor_clamp_fraction → 1.0` at any point, DB‑AT‑028 SHALL fail regardless of χ² trends (this indicates a model that is effectively “zero everywhere”).
    - Dynamic improvement linkage:
      - The existing relative improvement gate from TORCH‑REFINE‑002D (≥0.2% χ² drop) remains normative; DB‑AT‑028 adds absolute χ²‑per‑pixel and clamp‑fraction bounds to forbid pathological low‑signal configurations from passing.
  - Command: DB‑AT‑028 MAY be enforced by extending `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` or via a dedicated selector `pytest -v tests -k DB_AT_028`.

- DB‑AT‑029 Stage‑A intensity and structure parity vs experiment
  - Goal: Guarantee that Stage‑A predictions have reasonable intensity scale and ROI structure relative to experimental data, not just a decreasing scalar loss.
  - Setup:
    - Dataset and `RefinementInputs` as in DB‑AT‑028 (Stage‑A smoke dataset with perturbed geometry and canonical sigma_readout).
    - HKL grid and `RefinementConfig` identical to `test_stage_a_expansion` (haloed grid, interpolation enabled, LBFGS Stage‑A only).
  - Procedure:
    1) Run Stage‑A refinement once under the smoke configuration to obtain Stage‑A telemetry (`telemetry_A`) and the final Bragg image (`bragg_after`).
    2) Reconstruct Stage‑A initial and final images using the same canonical reconstruction path the engine uses (currently implemented by `dbex.nanobrag_refinement._build_final_bragg_from_stage_a_telemetry`):
       - `bragg_before`: call the reconstruction helper with `param_deltas[*]['final']` overridden to their `['initial']` values, so that geometry and scale reflect the Stage‑A initial state.
       - `bragg_after`: call the reconstruction helper with the actual telemetry (no overrides).
    3) Per‑ROI metrics:
       - For each ROI `(pid, (x0, x1, y0, y1))` from `RefinementInputs.panel_slices`, slice:
         - `data_roi = target[pid, y0:y1, x0:x1]`.
         - `model_before_roi = bragg_before[pid, y0:y1, x0:x1]`.
         - `model_after_roi = bragg_after[pid, y0:y1, x0:x1]`.
         - `mask_roi = loss_mask[pid, y0:y1, x0:x1]`.
       - Compute ROI correlations `corr_before_i`, `corr_after_i` against data using the canonical parity harness or `_compute_pearson_cc` with masking.
       - Collect:
         - `corr_before = {corr_before_i over all valid ROIs}`.
         - `corr_after = {corr_after_i over all valid ROIs}`.
    4) Global intensity scale:
       - Compute `mean_data = mean(target[loss_mask])`.
       - Compute `mean_model_before = mean(bragg_before[loss_mask])`.
       - Define `scale_ratio_before = mean_model_before / mean_data`.
  - Expectations (normative on the Stage‑A smoke dataset):
    - ROI correlation floor:
      - `median(corr_before) ≥ 0.2`. Stage‑A models whose initial prediction is effectively uncorrelated with the experimental ROIs SHALL fail DB‑AT‑029.
    - No catastrophic structural regression:
      - `median(corr_after) ≥ median(corr_before) − 0.05`. Stage‑A refinement SHALL NOT collapse median ROI correlation by more than 0.05.
    - Global intensity scale sanity:
      - `scale_ratio_before ∈ [1e‑2, 1e2]`. Ratios outside this band indicate the kind of multi‑order‑of‑magnitude mismatch observed in broken TOOLING‑VIS configurations and SHALL fail DB‑AT‑029.
      - For the canonical refGeom smoke fixture, a tighter expectation (O(0.1–10)) MAY be documented informatively, but the [1e‑2, 1e2] band is a hard spec‑level floor.
  - Command: DB‑AT‑029 SHALL be enforced via a dedicated test (e.g. `pytest -v tests -k DB_AT_029`) exercising Stage‑A reconstruction and ROI parity metrics on the Stage‑A smoke dataset.

Notes (Informative)
- Provide real commands in the test suite once scaffolding is in place; these are placeholders for the conformance contract.

References (Informative)
- docs/spec-db-core.md; docs/spec-db-runtime.md; docs/spec-db-workflow.md.
