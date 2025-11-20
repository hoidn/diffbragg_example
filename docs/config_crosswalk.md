# Config Mapping and Refinement Crosswalk

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
  - Per-reflection multipliers SHALL map to unique ASymmetric Unit (ASU) indices so `(h,k,l)` and `(-h,-k,-l)` share the same parameter.
  - Implementation pattern: maintain parameter vector `G_asu` sized to `N_unique`, scatter into the dense P1 grid before simulation, and gather/sum gradients back into `G_asu` after backpropagation.

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
- Stage B (Optional Fhkl): refine a small number of per‑shell/global scale parameters; tricubic on
- Stage C (Detector): refine per‑panel translation along detector normal; rotations fixed initially; optional in‑plane/rotational params later

References
- docs/dxtbx_api.md — Detector/Beam/Crystal/Scan extraction
- docs/simtbx_api.md — Image loading, background, ROI, masks
- docs/dials_api.md — Reflections, bbox, mask formats, shapes
- docs/nanobrag_api.md — torch configs, units, runtime, structure‑factor ingestion, ROI‑only compute
