Subject: Help Verifying simtbx/diffBragg Background, ROI, and MTZ Interfaces (for PyTorch Integration)

Hello,

We’re integrating `nanobrag_torch` as the refinement backend while keeping simtbx/DIALS for data prep in dbex. To keep loss definitions and masks scientifically consistent, we need to lock down the exact simtbx background/ROI and MTZ interfaces. You’re not expected to be a simtbx expert, but since you have the source code, the pointers below should make this tractable.

Context in our code:
- We call `simtbx.diffBragg.utils.image_data_from_expt(expt)` to get full-frame images.
- We call `simtbx.diffBragg.utils.get_roi_background_and_selection_flags(refs, data, ...)` to build ROI bboxes, panel IDs, and a “background_image” whose invalid pixels are sentinel-marked and valid pixels carry the estimated background.
- We call `utils.open_mtz(mtzFile, mtzCol)` and then `generate_bijvoet_mates()` to get a `cctbx.miller.array` with starting |F|.

What we need confirmed (and where to look)
1) ROI/background API contract
   - Function: `simtbx.diffBragg.utils.get_roi_background_and_selection_flags`
   - Confirm exact return tuple types and shapes:
     - `bbox`: order and slicing semantics. Our pipeline treats it as `(x1, x2, y1, y2)` with Python slice semantics (x2, y2 exclusive). Please verify.
     - `pids`: dtype and meaning (panel indices). Confirm 1:1 mapping to dxtbx `Detector` panel indices and the first dimension of the “data” array returned by `image_data_from_expt`.
     - `tilt_coefs`: dimensionality (per-ROI plane fit coefficients?) and whether it is used anywhere else in the ROI algorithm.
     - `bg_is_good`: boolean flags. Define what “good” means and edge cases (e.g., hot pixels, saturation).
     - `background_image`: fill value for invalid pixels (we assume −1), dtype, and whether any other sentinel values appear; confirm same panel ordering and shape as `data`.
   - Options we pass today: `use_robust_estimation=False`, `shoebox_sz=12`, `reject_roi_with_hotpix=False`, `pad_for_background_estimation=3`, `hotpix_mask=self.data < 0`, `weighted_fit=False`. Please confirm these defaults don’t change the fill-value contract or bbox semantics.

2) Image units and calibration
   - Function: `simtbx.diffBragg.utils.image_data_from_expt(expt)`
   - Are returned pixels pedestal/gain corrected? Units: ADU, electrons, or photons?
   - Any per-panel gain/saturation metadata we should honor when building masks? Where is this read from (dxtbx Panel trusted range, gain, etc.)?

3) Hot pixel / external mask formats
   - In our DiffBragg refinement calls we set `prm.roi.hotpixel_mask = args.maskFile` (file path).
   - What formats are accepted (NumPy .npy/.npz, DIALS mask .pickle/.json, HDF5)? Expected shape(s) and ordering (per panel).
   - Pointer in source where this is parsed and applied (likely inside `simtbx.diffBragg.hopper` or refiner IO): file reader and validation code paths.

4) MTZ and structure factors
   - Function: `simtbx.diffBragg.utils.open_mtz(mtzFile, mtzCol)`
   - Column label semantics:
     - “F,SIGF” vs “F(+),SIGF(+),F(-),SIGF(-)”: what cctbx arrays are produced?
     - Should we always call `generate_bijvoet_mates()` for parity with refinement stages, or only when we have separate (+/−) columns?
   - Units/scales: expected |F| magnitude conventions; any implicit scaling we should mirror upstream/downstream.

5) Energy/flux usage
   - We see `utils.ENERGY_CONV` used to map wavelength to energy. Any other implicit fluence/flux handling in simtbx background/ROI routines we should be aware of (to keep target vs. model on comparable scales), or is scale entirely absorbed by refinement?

Deliverables (what would unblock us)
- A short note confirming each bullet above (especially bbox ordering and background_image fill/shape/ordering).
- If possible, a ~20 line code snippet that:
  - Loads a simple Experiment/refl set,
  - Calls the two utils functions,
  - Prints shapes and min/max/sentinels of `data` and `background_image`,
  - Prints the first few `bbox`/`pids` entries and confirms the slicing convention works (data[pid, y1:y2, x1:x2]).

Thanks a lot—this will let us keep the loss and masking logic consistent with the current pipeline.

Best,  
[Your Name]

