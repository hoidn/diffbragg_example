# Config Mapping and Refinement Crosswalk

Status: Normative by reference for detector/beam/crystal/config mapping when cited from `spec-db-core.md` §Geometry Mapping; otherwise informative.

This document is a one‑stop mapping between DIALS/dxtbx/simtbx inputs, DiffBragg concepts, and `nanobrag_torch` configuration/parameters. It also states which parameters we refine in v1, their parameterizations, initial values, and constraints.

Conventions and Units
- Array ordering: `[panel, slow, fast]`
- ROI bbox: `(x0, x1, y0, y1)` with exclusive upper bounds
- Detector distances/pixel sizes: millimeters at API, meters internally in torch
- Crystal: Angstroms/degrees
- Beam wavelength: Angstroms
- Beam vector: sample→source (for torch; compute as normalized `-s0`)
- Mask polarity: DIALS trusted mask (True=include); DiffBragg hot/bad mask is inverted; torch mask_array uses trusted polarity (1=include)
- Target units: ADU by default; can convert to photons with `--adu-per-photon`

Detector (per panel)
- dxtbx source
  - `panel.get_origin()` (mm), `panel.get_fast_axis()`, `panel.get_slow_axis()`, `panel.get_normal()`
  - `panel.get_directed_distance()` (mm)
  - `panel.get_beam_centre(beam.get_s0())` → (fast_mm, slow_mm)
  - `panel.get_pixel_size()` → (fast_mm, slow_mm)
  - `panel.get_image_size()` → (fast_px, slow_px)
- torch mapping (DetectorConfig)
  - `detector_convention = DIALS`
  - Detector rotations derived from panel axes: form rotation matrix with columns `[fast, slow, normal]`, validate via `scitbx.matrix.is_r3_rotation_matrix()`, convert to XYZ Euler angles in degrees via `r3_rotation_matrix_as_x_y_z_angles()`
  - `detector_rotx_deg`, `detector_roty_deg`, `detector_rotz_deg` set from computed Euler angles
  - `distance_mm = panel.get_directed_distance()`
  - `beam_center_s = slow_mm`, `beam_center_f = fast_mm`, `beam_center_source = "explicit"` (preserves BEAM pivot per `nanobrag_api.md`)
  - `pixel_size_mm = px_fast_mm` (guard: require `abs(px_fast_mm - px_slow_mm) <= 1e-9`)
  - `spixels = slow_px`, `fpixels = fast_px`
  - ROI defaults to full detector when omitted
- `mask_array = torch.as_tensor(trusted_mask[panel], dtype=torch.float32)` with shape `(spixels, fpixels)` (1=include); CLI-001 requires torch tensors so the simulator can call `.to(device, dtype)`
- Refined vs Fixed (Stage C)
  - Refine: translation along detector normal (distance offset) per panel
  - Fixed (v1): detector rotations (derived from dxtbx panel axes), beam center, pixel size
  - Constraints: small step sizes; optional L2 penalties

Beam
- dxtbx source
  - `beam.get_wavelength()` (Å)
  - `beam.get_s0()` (source→sample; used only to derive sample→source)
  - `beam.get_polarization_normal()`, `beam.get_polarization_fraction()`
  - `beam.get_sample_to_source_distance()` (optional, mm)
- torch mapping (BeamConfig)
  - `wavelength_A = beam.get_wavelength()`
  - `polarization_factor = 0.0`, `nopolar = False`
  - `polarization_axis = beam.get_polarization_normal()` if available else `[0,0,1]`
  - `polarization_fraction = beam.get_polarization_fraction()` if available else `0.999`
  - `dmin = 0.0` initially; adjust if needed
  - Multi‑source fields optional; not used in v1
- Refined vs Fixed
  - Fixed in v1 (no beam refinement). Consider later: divergence/dispersion via multi‑source.

Crystal
- dxtbx source
  - `crystal.get_unit_cell().parameters()` → `(a,b,c,α,β,γ)`
  - `crystal.get_A()` → columns are `(a*, b*, c*)` (Å⁻¹)
  - `expt.goniometer.get_rotation_axis()`; `expt.scan.get_oscillation_in_deg()`; `expt.scan.get_num_images()`
- torch mapping (CrystalConfig)
  - `cell_a/b/c, cell_alpha/beta/gamma` from unit cell
  - MOSFLM injection: `mosflm_a_star/b_star/c_star` = columns of `A`
  - `misset_deg` (XYZ extrinsic) applied after MOSFLM injection (set each forward from a quaternion)
  - Stills: `phi_steps=1`, `osc_range_deg=0`, `mosaic_domains=1`, `mosaic_spread_deg=0`
  - Lattice: `N_cells = (--nabc) or (20,20,20)`; `shape = SQUARE`; `fudge = 1.0`
- Mapping-aligned Stage A (DB‑AT‑024, TOOLING‑VIS‑001):
  - Baseline mapping orientation SHALL be defined by the DB‑AT‑024 pipeline:
    - Either via MOSFLM A* injection from `crystal.get_A()` with `misset_deg = [0,0,0]`, **or**
    - Via an equivalent baseline misset tensor when `crystal_overrides` are used and MOSFLM A* injection is disabled.
  - Stage‑A geometry parameterizations (cell logs/angles, quaternion→XYZ) used in mapping‑aligned refinement or visualization MUST treat their parameters as **deltas** around this baseline:
    - At zero deltas and baseline scale, the resulting `CrystalConfig` MUST reproduce the DB‑AT‑024 mapping Bragg tensor (up to numerical tolerance).
    - When `crystal_overrides` are non‑None, callers SHALL supply a `misset_deg_override` that includes the baseline misset (e.g., `misset_deg = baseline_misset_deg + delta_misset`) so that the zero point remains mapping‑aligned even though MOSFLM A* is omitted in that call.
- Refined vs Fixed (Stage A)
  - Refine: unit cell parameters (logs/bounded angles), orientation (quaternion→XYZ), global scale
  - Fixed: N_cells (v1), mosaic (0), phi scanning (stills)
  - Differences vs DiffBragg:
    - No `Ncells_def` in torch (defect envelope). Omit in v1.
    - No `no_Nabc_scale` in torch; use global scale to absorb lattice magnitude differences.

Structure Factors
- Source
  - cctbx Miller array from MTZ (`DataLoad.F`), typically after `generate_bijvoet_mates()`
- torch mapping
  - Build dense P1 tensor grid in memory:
    - Track `h_min..h_max`, `k_min..k_max`, `l_min..l_max`, allocate `[h_range, k_range, l_range]`, fill with |F|
    - Assign `crystal.hkl_data`, `crystal.hkl_metadata`
  - Enable tricubic via `crystal.interpolate = True`; requires ±1 halo (pad FDUMP-style or extend bounds)
  - Interpolation fallback: when halo incomplete, returns `default_F`
- Stage B refinement
  - Per-reflection multipliers SHALL map to unique Asymmetric Unit (ASU) indices so `(h,k,l)` and `(-h,-k,-l)` share the same parameter.
  - Implementation pattern: the bridge MUST emit an `asu_mapping_tensor` aligned to the dense grid. The refinement engine maintains a parameter vector `G_asu` sized to the number of unique ASU entries, scatters via `Grid[h,k,l] = Base[h,k,l] * G_asu[Map[h,k,l]]`, and gathers gradients back to `G_asu` after each backward pass.

ROI, Background, and Masks
- simtbx background
  - `image_data_from_expt(expt)` → `[panel, slow, fast]` ADU
  - `get_roi_background_and_selection_flags(...)` → background_image with −1 outside ROIs; bbox `(x0,x1,y0,y1)` exclusive; panel alignment with Detector order
- torch usage
  - Simulator mask: `DetectorConfig.mask_array = trusted_mask` (float 0/1)
  - Loss mask: `loss_mask = (background >= 0) & trusted_mask`
  - Optional parity: re-run simtbx background using the trusted mask rather than `data<0` for ROI hot‑pixel logic
- HDF5 outputs
  - Write `Bragg` as `[panel, slow, fast]` to mirror legacy path; reuse downstream viewer

Units and Scaling
- Inputs: ADU by default; convert to photons if `--adu-per-photon` is supplied
- Simulator output: photons
- Global scale
  - ADU mode: learn a global positive scale; initialize via mean(target)/mean(sim_initial) over a few ROIs
  - Photon mode: initialize near 1.0

Staging Summary (Refine vs Fixed)
- Stage A (Crystal + Scale): refine cell (logs/angles), orientation (quaternion→XYZ), global scale; N_cells fixed; mosaic/phi off for stills
- Stage B (ASU Fhkl modifiers): refine per-ASU multipliers with tricubic interpolation and ±1 halo.
- Stage C (Detector): refine per-panel translation along detector normal; rotations fixed initially; optional in-plane/rotational params later

References
- docs/dxtbx_api.md — Detector/Beam/Crystal/Scan extraction
- docs/simtbx_api.md — Image loading, background, ROI, masks
- docs/dials_api.md — Reflections, bbox, mask formats, shapes
- docs/nanobrag_api.md — torch configs, units, runtime, structure‑factor ingestion, ROI‑only compute

Notation ↔ Config Field Mapping (Informative)
- Crystal state:
  - `A*_0` (baseline setting matrix) — `crystal.get_A()`; columns are `(a*, b*, c*)` and are injected into `CrystalConfig.mosflm_a_star/b_star/c_star`.
  - `c₀ = (a₀, b₀, c₀, α₀, β₀, γ₀)` — `crystal.get_unit_cell().parameters()`; stored as `cell_a/b/c` and `cell_alpha/beta/gamma` on `CrystalConfig`.
  - `B₀ = B(c₀)` — constructed inside `nanobrag_torch` from `cell_*` using the Busing–Levy recipe; not stored as a separate field.
  - `U₀` — implicitly defined by `A*_0 = U₀ B₀`; not stored directly, but corresponds to the baseline orientation encoded by `mosflm_*` with `misset_deg = [0,0,0]` in mapping‑aligned runs.
- Stage‑A parameters:
  - Orientation increment `ΔR(params)` — trainable quaternion (or equivalent) in the Stage‑A model (e.g., `ExperimentModel(param_init="stage_a")`), converted each forward into extrinsic XYZ angles and written into `CrystalConfig.misset_deg`.
  - Cell increments `δc(params)` — trainable cell deltas (logs/angles) around `c₀`; forwarded each step by updating `CrystalConfig.cell_a/b/c` and `cell_alpha/beta/gamma` before building `B(c)`.
  - Setting matrix `A*(params)` — built in the simulator as `U(params) @ B(params)` from the updated `cell_*` and `misset_deg` per `docs/spec-db-core.md` and `docs/spec-db-workflow.md`.
- Arrays and loss:
  - `I_obs` (Spec‑DB) — the background‑subtracted target; in code this is `RefinementInputs.target` (`inputs.target`), shaped `[panel, slow, fast]` and sliced with `(x0,x1,y0,y1)` as `target[pid, y0:y1, x0:x1]`.
  - `I_model` — the model intensity on the same grid used in the variance‑weighted loss. For the DiffBragg backend this is the sum of the simulated Bragg tensor and the background image on raw data; for the current torch Stage‑A implementation it is the scaled Bragg tensor evaluated on background‑subtracted targets (see TODO‑PHYSICS (informative) below and the canonical definition in `spec-db-core.md` §Objective Function & Variance Model). The “Bragg‑only on background‑subtracted targets” formulation is non‑conformant and is described here only to document current behavior.
  - `sigma_readout` — detector readout noise in target units; represented as `RefinementInputs.sigma_readout` (`inputs.sigma_readout`), populated from the precedence chain config sigma map (`torch_config`) → `--sigma-map` (tensor) → `--sigma-rdout` (scalar) → Experiment external_lookup tiles (see `spec-db-core.md` §Variance inputs). Conflicts between sources SHALL fail fast (no silent override).
  - Variance `V = I_model + sigma_readout^2` — implemented in `dbex.physics.loss._compute_variance_weighted_loss` (detached and clamped to `sigma_floor^2`) and written to HDF5 as `variance/roiN` with companion `sigma_readout` and `sigma_floor` datasets, per `docs/spec-db-core.md` and `docs/spec-db-workflow.md`.
  - Masks: Spec‑DB `mask_array` / trusted mask correspond to `DetectorConfig.mask_array` (0/1 float, `[slow, fast]`) and `RefinementInputs.trusted_mask`; the loss mask `(background >= 0) ∧ trusted_mask` is `RefinementInputs.loss_mask`.
  - Scale composition (Stage A) — canonical policy:
    - Photon mode (`--adu-per-photon > 0`): convert targets/sigma to photons at ingest; `I_model_photons` from the simulator is scaled by `spot_scale_override * exp(log_scale_delta)` (log_scale_delta = 0 at baseline).
    - ADU mode (no gain provided): targets/sigma remain in ADU; simulator output is converted to ADU before loss and scaled by `spot_scale_override**0.5 * exp(log_scale_delta)` (log_scale_delta = 0 at baseline). There is no “ADU mode with gain.” See `spec-db-workflow.md` (Calibration & Unit Conventions) for the normative ADU/photon policy.

Naming Glossary — Loss, Targets, and Sigma (Informative)
- Observed data:
  - `I_obs` (Spec‑DB core/vis): raw experimental data in the run’s unit mode (ADU or photons). This is what the canonical loss and triptych “Data” panel use.
  - `target` / `inputs.target` (RefinementInputs): an implementation detail for some paths (e.g., background-subtracted targets). When present, this is `I_obs − I_bg_estimate` restricted to ROIs; it is not the canonical `I_obs` for Spec‑DB.
- Model:
  - `I_model` (Spec‑DB): full model prediction `Bragg + background` on the raw data grid; DiffBragg backend already writes this as model datasets. The current torch Stage‑A path uses a Bragg-only prediction on background-subtracted targets (non‑conformant; see note below).
  - `Bragg` alone (`bragg` tensors, `bragg/roiN` datasets) is the pure Bragg component.
  - Non‑conformant implementation note (temporary): The current torch Stage‑A implementation computes loss/viewer model using Bragg-only on background-subtracted targets; this is explicitly non‑conformant with `spec-db-core.md` and is slated for removal once the conformant path lands.
- Sigma / variance:
  - `sigma_readout` (Spec‑DB) ↔ `sigma_readout` / `sigma_readout_map` in `DataLoad`/`RefinementInputs`; CLI flags `--sigma-rdout` and `--sigma-map`; nanobrag docs may also refer to this as `sigma_r`.
  - `V` / “variance” (Spec‑DB) ↔ the detached, clamped denominator in `_compute_variance_weighted_loss` and the `variance/roiN` dataset in HDF5; VIS Z‑score maps use `z = (I_obs - I_model) / sqrt(V)` as described in `docs/spec-db-vis.md`.
