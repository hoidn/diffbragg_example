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

