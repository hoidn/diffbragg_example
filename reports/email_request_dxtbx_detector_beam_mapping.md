Subject: Help Mapping dxtbx Experiment (Detector/Beam/Crystal) to `nanobrag_torch` Configs

Hello,

We’re replacing the optimizer with `nanobrag_torch` but must map DIALS/dxtbx geometry 1:1 into the PyTorch simulator. You’re not a dxtbx maintainer, but you have the source—could you confirm the mapping details below and provide code snippets? This will unblock our Phase 1 bridge.

What we need to extract from a dxtbx Experiment:
1) Detector panel geometry → `nanobrag_torch.DetectorConfig/Detector`
   - From a `dxtbx.model.Detector` panel:
     - `get_origin()` (mm), `get_fast_axis()` (unit), `get_slow_axis()` (unit),
       `get_pixel_size()` (mm), `get_image_size()` (pixels).
   - Confirm units and coordinate frames: lab frame vectors/positions, mm for origin, pixels for size.
   - Beam center:
     - Canonical way to compute panel beam center from `beam.get_s0()`. dxtbx has `panel.get_beam_centre(s0)`—units returned (mm or pixels) and axis ordering (slow/fast)?
     - If only origin/axes are used, how to derive “distance_mm” and beam center s/f in pixels to match `nanobrag_torch` expectations?
   - Distance definition:
     - Should “distance_mm” be projection of panel origin onto the detector normal, or specifically along the beam direction?
     - Edge cases for panels not orthogonal to the beam (tilted or curved future cases): any special handling?
   - Panel ordering:
     - Confirm that panel index in `Detector` corresponds 1:1 to:
       - First dimension index in `utils.image_data_from_expt(expt)` output,
       - `pids` returned by simtbx ROI/background helper.
   - Trusted range, gain, saturation:
     - Where to read these (Panel API) and whether they should influence mask construction or loss. Pointers to code or docs appreciated.

2) Beam model → `nanobrag_torch.BeamConfig`
   - Wavelength:
     - `beam.get_wavelength()` units (Angstroms) and variability across scans. For stills, we plan to use a single value; for scans, is there a canonical per-image value?
   - Polarization:
     - Does dxtbx expose polarization direction/factor? If yes, where and in what units/coordinates? If no, recommended default for typical beamlines?
   - s0 vector:
     - `beam.get_s0()`—confirm unit length, direction/sign convention (does it point from source to sample or opposite)? We need to align this with `nanobrag_torch` beam vector conventions.

3) Crystal orientation/cell → `nanobrag_torch.CrystalConfig/Crystal`
   - Orientation matrices:
     - `crystal.get_U()`, `crystal.get_B()`, `crystal.get_A()`—definitions (frames/units).
     - Preferred mapping to nanobrag_torch:
       - Option A: Convert A (or A*) to a quaternion/Euler consistent with Detector/Beam frames,
       - Option B: Populate MOSFLM A* via `CrystalConfig.mosflm_*`.
     - Any source code pointers or formulae that confirm the reference frames so we avoid sign flips and gimbal lock.
   - Unit cell:
     - `crystal.get_unit_cell().parameters()`—confirm we can pass directly as triclinic (a,b,c,α,β,γ) in Angstroms/degrees to nanobrag_torch.
   - Spindle/phi/mosaic:
     - For still images vs scans:
       - `goniometer.get_rotation_axis()` frame/units,
       - `scan.get_oscillation()` (phi start, range in degrees),
       - Best practice to derive `phi_steps` and `delta_phi` for parity with C defaults.

What to return to us (ideal deliverables)
- A short code snippet that:
  1) Loads a real Experiment (.expt),
  2) For one panel, prints origin (mm), fast/slow axes, pixel size, image size, beam center (s,f) in pixels, and distance_mm per your recommended definition,
  3) Shows the mapping to `nanobrag_torch.DetectorConfig` (using DIALS or CUSTOM convention, whichever you deem correct), including pivot selection,
  4) Extracts wavelength and s0 from dxtbx Beam and maps to `BeamConfig` (units checked),
  5) Extracts cell + orientation from dxtbx Crystal and maps to `CrystalConfig` (quaternion or MOSFLM A* route), noting any unit/frame conversions.
- A brief confirmation that panel indices match across `image_data_from_expt`, `pids` from simtbx ROI, and dxtbx’s Detector index order.

Why this matters
- This mapping is the highest‑risk step: any sign/unit mismatch will misplace peaks and break convergence. Your confirmation will let us finalize the bridge with confidence.

Many thanks,
[Your Name]

