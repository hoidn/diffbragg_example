# simtbx/diffBragg Utilities API (dbex Usage)

This document captures the simtbx helpers dbex relies on for image loading and ROI/background estimation, and MTZ handling. Paths refer to cctbx_project/simtbx/diffBragg sources.

## Image Loading
- `simtbx.diffBragg.utils.image_data_from_expt(expt) -> np.ndarray`
  - Returns float64 NumPy stack shaped `[n_panels, slow, fast]`.
  - No pedestal/gain correction or unit conversion; values are raw ADU from the imageset.
  - Downstream (DiffBragg) converts ADU→photons via `params.refiner.adu_per_photon`. Mirror this if the model expects photons; otherwise keep ADU and use a scale factor.

## ROI/Background Estimation
- `simtbx.diffBragg.utils.get_roi_background_and_selection_flags(refs, imgs, ..., ret_cov=False)`
  - Returns `(bbox_list, panel_ids, tilt_coefs, selection_flags, background_image[, cov])`
    - `background_image`: same shape as `imgs` (`[panel, slow, fast]`), filled with −1 sentinel for invalid pixels; valid ROI pixels carry the plane/robust background estimate.
    - `bbox_list`: list of ROI tuples `(x1, x2, y1, y2)` in fast/slow order, with exclusive upper bounds; slice as `imgs[pid, y1:y2, x1:x2]`.
    - `panel_ids`: integer panel indices aligned to the first axis of `imgs` and the dxtbx `Detector` ordering.
    - `tilt_coefs`: one `(a,b,c)` triple per ROI for the plane model (with `ret_cov=True`, covariance is also returned).
    - `selection_flags` (aka `bg_is_good`): booleans indicating ROI quality; failing ROIs still populate `background_image` but are marked for filtering.
  - Background options:
    - `use_robust_estimation=False` yields a plane fit; when True, the plane becomes constant median but shape stays consistent.
    - `shoebox_sz`, `pad_for_background_estimation`, `weighted_fit`, `reject_roi_with_hotpix`: control fitting and rejection; none alters array ordering or sentinel convention.
  - Masks:
    - External “hot pixel” masks are loaded via `utils.load_mask(path)` and must be DIALS‑pickled (tuple of flex.bool per panel). Internally inverted for “bad pixel” semantics during ROI gathering.
    - See also `utils.save_numpy_mask_as_flex` to convert NumPy masks to the required pickled flex format.

## Noise / Sigma Handling
- Readout noise enters through `params.refiner.sigma_r` (ADU) and `params.refiner.adu_per_photon`. Hopper converts once per shot: `nominal_sigma_rdout = sigma_r / adu_per_photon` (`diffBragg/hopper_utils.py:517`), so downstream arrays are already in photon units.
- Detectors with per-pixel pedestal RMS (e.g., Jungfrau) override the nominal value by loading the calib image via `get_pedestalRMS_from_jungfrau`, scaling by the same `adu_per_photon`, and slicing per ROI (`diffBragg/hopper_utils.py:646`). When no map exists, the scalar nominal term is broadcast.
- Background fits weight pixels with `1 / (sigma_rdout^2 + rho_bg)` (rho_bg is the fitted plane intensity), so both Poisson and readout noise influence the covariance the same way the refiner expects (`diffBragg/utils.py:669`).
- For each ROI pixel, simtbx stores `all_sigma_rdout` (either scalar or per-pixel array) and computes `all_sigmas = sqrt(data + sigma_rdout^2)`; untrusted pixels include those with `NaN` sigmas (`diffBragg/hopper_utils.py:699` and `:746`). These arrays are exactly what Stage One/Two use when forming residual Z-scores and variance terms, so integrators should not recompute the variance model independently.
- When serializing ROI triptychs (e.g., for pandas artifacts), the same variance formula is applied: `sigma = sqrt(model + sigma_rdout^2)`. This ensures Z-scores match the refinement objective and keeps diagnostics aligned with the Poisson+readout contract formalized in `docs/spec-db-core.md`.

## MTZ / Structure Factors
- `simtbx.diffBragg.utils.open_mtz(mtzFile, mtzCol) -> cctbx.miller.array`
  - Returns a Miller array derived from the requested label(s) (`"F,SIGF"`, or `"F(+),SIGF(+),F(-),SIGF(-)"` etc.).
  - Call `miller_array.generate_bijvoet_mates()` for completeness when your downstream expects both Friedel mates.
  - Units/scales: |F| amplitudes; downstream DiffBragg stages scale internally. Preserve labels and ASU mapping if writing back MTZs mid‑refinement.

## Alignment and Shapes
- All simtbx/dxtbx tooling assume:
  - Arrays: `[panel, slow, fast]`
  - ROI bbox: `(x1, x2, y1, y2)` with exclusive upper bounds.
  - Panel indices align across `image_data_from_expt`, reflection table `panel` column, and simtbx ROI `panel_ids`.
