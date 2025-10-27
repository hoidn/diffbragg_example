# dxtbx API (Geometry, Beam, Crystal, Scan)

This document summarizes the dxtbx objects dbex consumes, focusing on parameters needed to build `nanobrag_torch` configs and to interpret images and ROIs correctly.

## Detector Panels
- Geometry (lab frame):
  - `panel.get_origin()` → (mm) 3‑vector (panel origin).
  - `panel.get_fast_axis()`, `panel.get_slow_axis()` → unit 3‑vectors.
  - `panel.get_normal()` → unit 3‑vector (fast × slow).
- Pixel metrics:
  - `panel.get_pixel_size()` → (fast_mm, slow_mm).
  - `panel.get_image_size()` → (fast_px, slow_px).
- Beam center:
  - `panel.get_beam_centre(s0)` → (fast_mm, slow_mm).
  - `panel.get_beam_centre_px(s0)` → (fast_px, slow_px).
- Distance and pivot:
  - `panel.get_directed_distance()` → scalar (mm), signed wrt normal; use this for DetectorConfig.distance_mm.
- Masking metadata:
  - Trusted range, gain, pedestal, thickness, absorption length are available on Panel; use for mask construction and loss weighting.
- Ordering:
  - Indexing of `Experiment.detector[i]` aligns with first axis of `simtbx.utils.image_data_from_expt(expt)` output and reflection table `panel` column.

## Beam
- Wavelength:
  - `beam.get_wavelength()` → float (Å).
- Incident wavevector:
  - `beam.get_s0()` → 3‑vector with magnitude 1/λ, pointing source→sample.
  - For `nanobrag_torch`, supply sample→source to `DetectorConfig.custom_beam_vector`: `-s0 / ||s0||`.
- Polarization:
  - `beam.get_polarization_normal()` → unit 3‑vector.
  - `beam.get_polarization_fraction()` → scalar in [0,1].
- Optional:
  - `beam.get_sample_to_source_distance()` → float (mm).

## Crystal
- Unit cell:
  - `crystal.get_unit_cell().parameters()` → (a, b, c, alpha, beta, gamma) in Å/deg.
- Orientation matrices:
  - `crystal.get_U()` → orthonormal rotation.
  - `crystal.get_B()` → reciprocal metric.
  - `crystal.get_A()` → U·B; columns are (a*, b*, c*) in Å⁻¹; copy into `CrystalConfig.mosflm_*`.

## Goniometer and Scan
- Rotation axis:
  - `expt.goniometer.get_rotation_axis()` → unit 3‑vector (lab frame).
- Oscillation:
  - `expt.scan.get_oscillation_in_deg()` → (phi_start_deg, osc_range_deg) per image.
  - `expt.scan.get_num_images()` → phi steps.
- Stills:
  - When no scan, use `phi_steps=1` and `osc_range_deg=0` for still frames.

