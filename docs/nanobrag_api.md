# nanobrag_torch API (Integration-Oriented)

This document summarizes the public, integration‑ready API surface of `nanobrag_torch` for use as a differentiable diffraction simulator in dbex. It captures conventions, units, and best practices confirmed by the maintainer responses.

Scope: `src/nanobrag_torch/{simulator.py, models/{crystal.py,detector.py}, config.py, io/hkl.py}`

Import name

- Python import module: `nanobrag_torch`
- Quick example:
  ```python
  import nanobrag_torch as nbt
  from nanobrag_torch import Simulator, DetectorConfig, CrystalConfig, BeamConfig
  ```

## Runtime and Environment
- torch.compile: Simulator compiles physics kernels; reuses compiled graphs when tensor shapes are unchanged. GPU defaults to mode="max-autotune"; CPU may use "reduce-overhead".
- Reuse warmed Simulator across iterations when panel dimensions/oversample do not change; rebuild if geometry affects shapes.
- Set `KMP_DUPLICATE_LIB_OK=TRUE` before importing torch in long‑lived processes.
- Set `NANOBRAGG_DISABLE_COMPILE=1` to force eager mode (useful for debugging).

## Units and Conventions
- Detector geometry (distance, pixel size): meters internally; API accepts millimeters and converts.
- Crystal cell: Angstroms and degrees.
- Beam wavelength: Angstroms; `BeamConfig.wavelength_A`.
- Output intensity: physical “photons” with r_e² × fluence scaling.
- Beam vector direction: pass sample→source as `DetectorConfig.custom_beam_vector` (normalize −s0).
- Beam center ordering: DetectorConfig expects `(beam_center_s, beam_center_f)`. dxtbx returns `(fast, slow)`; swap.
- Variance contract: the downstream loss MUST reuse the spec’d `V = model_Lambda + sigma_r^2` (shot noise from the model plus readout noise supplied in photon units). See `docs/spec-db-core.md`.

## Public Configuration Dataclasses

### DetectorConfig (key fields)
- `distance_mm` (float): from `panel.get_directed_distance()` (mm).
- `pixel_size_mm` (float): square pixel pitch only (fast/slow share a value).
  - Rectangular pixels: not supported in a single detector; instantiate separate Detectors per unique pitch until `pixel_size_s_mm/pixel_size_f_mm` is available.
- `spixels`, `fpixels` (int): image dimensions (slow, fast).
- `beam_center_s`, `beam_center_f` (float, mm): beam center in mm; set `beam_center_source="explicit"` to skip MOSFLM +0.5 px offset.
- Conventions:
  - Use `DetectorConvention.DIALS` with rotation angles derived from dxtbx panel axes (fast/slow/normal). Form rotation matrix with columns `[fast, slow, normal]`, validate via `scitbx.matrix.is_r3_rotation_matrix()`, and convert to XYZ Euler angles via `r3_rotation_matrix_as_x_y_z_angles()`.
  - Set `detector_rotx_deg`, `detector_roty_deg`, `detector_rotz_deg` from computed angles (in degrees).
  - DIALS convention with BEAM pivot preserves beam center position without drift.
- ROI and mask:
  - `roi_xmin/xmax/ymin/ymax`: optional; default is full detector when omitted. Must be within `[0..spixels-1]`/`[0..fpixels-1]`.
  - `mask_array`: tensor (0/1) with shape `(spixels, fpixels)`; multiplied post‑compute to zero masked pixels.
  - Shapes: ROI bounds and `mask_array` must match `spixels`/`fpixels`.
- Sampling and corrections:
  - `oversample` (int; -1 = auto), `oversample_omega` (solid angle per subpixel), `oversample_polar` (polarization per subpixel), `oversample_thick` (absorption per subpixel).
  - `point_pixel=True` applies 1/R^2 solid angle only; `curved_detector=True` enables spherical mapping (if supported by build).
  - Absorption: `detector_abs_um`, `detector_thick_um`, `detector_thicksteps` control sensor absorption model.

### CrystalConfig (key fields)
- Cell parameters: `cell_a/b/c` (Å), `cell_alpha/beta/gamma` (deg). Triclinic supported.
- Orientation:
  - MOSFLM A*: inject via `mosflm_a_star/b_star/c_star` (columns of dxtbx `A`).
  - `misset_deg`: extrinsic XYZ rotations applied after MOSFLM injection.
  - Recommended: manage a unit quaternion in your model, convert to XYZ angles each forward, and set `misset_deg`.
- Rotation/mosaic (for scans):
  - `phi_start_deg`, `osc_range_deg`, `phi_steps`, `spindle_axis`.
  - Stills parity: `phi_steps=1`, `osc_range_deg=0`, `mosaic_domains=1`, `mosaic_spread_deg=0`.
- N_cells and shape: `N_cells`, `shape`, `fudge` control lattice factor.

### BeamConfig (key fields)
- `wavelength_A` (Å), `dmin` cutoff.
- Polarization:
  - For parity: `polarization_factor=0.0`, `nopolar=False`.
  - When metadata exists: set `polarization_axis` and fraction; otherwise default axis `[0,0,1]`, fraction `0.999`.
- Flux/fluence/exposure: recomputed in `__post_init__` when any pair is set along with beam size.
- Multi‑source: `(n,3)` directions, optional wavelengths and weights; sources summed equally per spec.

## Core Classes

### Detector
- Construct with `DetectorConfig`. Internally caches:
  - `pixel_coords` (S,F,3) on device/dtype of Simulator on first use.
  - `roi_mask` (S,F) from config and mask_array; applied after intensity computation.
- Square pixels only; for rectangular pixels, use separate Detectors.

### Crystal
- Cell tensors computed honoring MOSFLM A*, then applying `misset_deg` (XYZ extrinsic).
- Structure factors:
  - Dense P1 grid expected; see IO section.
  - Stage A (geometry): set `crystal.interpolate = False` (nearest‑neighbor |F|). Gradients flow via kinematics/lattice factors; avoids halo/OOB artifacts.
  - Stage B (Fhkl): set `crystal.interpolate = True` and ensure the grid includes a ±1 halo in h/k/l.
  - Without halo, tricubic will fall back to `default_F` and zero gradients near bounds.

### Simulator
- Constructor: `Simulator(crystal, detector, crystal_config=None, beam_config=None, device=None, dtype=torch.float32, debug_config=None)`
  - Normalizes device/dtype; moves detector to simulator’s device/dtype.
  - Caches pixel coordinates and ROI mask.
- `run() -> torch.Tensor`:
  - Returns intensity image `(spixels, fpixels)` on the simulator device/dtype.
  - Applies dmin, polarization, solid angle, absorption, and ROI/mask per config.
  - Use one Simulator per panel; stitch results into `[panel, slow, fast]`.
  - Changing shapes (panel dims, oversample) requires re‑instantiation; numeric parameter tweaks don’t.
- Debug/trace:
  - `debug_config` supports `printout`, `printout_pixel`, and `trace_pixel` for diagnostics.
  - Enabling trace incurs overhead; use sparingly (e.g., tracing a single pixel).

## IO: Structure Factors (HKL/FDUMP)
- `read_hkl_file(filepath, default_F, device, dtype) -> (F_grid, metadata)`
  - Returns a dense 3D P1 tensor `[h_range, k_range, l_range]` and min/max metadata.
- In‑memory path from cctbx:
  - Iterate reflections, track min/max, allocate `F_grid`, fill by indices, assign:
    - `crystal.hkl_data = F_grid`
    - `crystal.hkl_metadata = {'h_min':..., 'h_max':..., ...}`
  - Tricubic needs a ±1 halo; pad grid or include extra indices beyond the sampled range. Grid bounds should derive from the MTZ index envelope; UB changes do not require rebuilds.

## ROI‑Only Compute (Performance)
- ROI/mask zeroes pixels post‑compute; to compute only an ROI:
  - Build a cropped `DetectorConfig` with `spixels/ fpixels` equal to ROI dimensions and beam center shifted by crop offsets in mm.
  - Create a `Detector` from that config and a new `Simulator`; stitch ROI output back into the panel image.

## ADU vs Photons
- image_data are typically ADU; either:
  - Convert to photons using known `adu_per_photon`, or
  - Keep ADU and include a learnable global scale; multiplicative physics corrections still apply.
