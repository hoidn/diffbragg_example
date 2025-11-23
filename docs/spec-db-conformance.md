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
  - DB‑AT‑025 HKL interpolation conformance (tricubic halo): when `crystal.interpolate=True`, the dense |F| grid MUST include a ±1 halo; any default_F fallback is a failure. Stage A SHALL disable interpolation.
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
  - Expectation: halo present in metadata; default_F fallback count == 0 (no out‑of‑bounds lookups while interpolating). Stage A SHALL disable interpolation; this test applies to Stage B and forward runs where interpolation is enabled.
  - Command: (selector TBD; activate once telemetry and halo flag are exposed)

Notes (Informative)
- Provide real commands in the test suite once scaffolding is in place; these are placeholders for the conformance contract.

References (Informative)
- docs/spec-db-core.md; docs/spec-db-runtime.md; docs/spec-db-workflow.md.
