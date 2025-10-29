Subject: Help Verifying DIALS Reflection/ROI Column Semantics and Mask Formats

Hello,

We use DIALS reflection tables and masks upstream of simtbx background estimation. To keep behavior identical in the new PyTorch refinement loop, we need to lock down reflection column and mask semantics. You’re not a DIALS maintainer, but you have the source—could you confirm or extract the details below?

Scope in our code:
- Reflection table from `.refl` is filtered by `id == exptIdx` and passed with the Experiment to simtbx utilities.
- simtbx background routine uses bbox/panel information to define ROIs and generates a `background_image` with sentinel values for non‑ROI pixels.
- We also pass an external hot pixel mask file path into DiffBragg’s `prm.roi.hotpixel_mask`.

What we need confirmed (and where)
1) Reflection table minimal schema for ROI background
   - Which columns are strictly required by simtbx’s `get_roi_background_and_selection_flags`?
     - `id`, `panel` (or equivalent), `bbox` (format), possibly `shoebox`, `xyzobs.px.value`?
   - Column types and shapes (e.g., `bbox`): definition of inclusivity/exclusivity (is bbox `[x1, x2, y1, y2]` with x2,y2 exclusive or inclusive?).
   - Source code pointers in DIALS where these columns are defined/consumed for ROI extraction that simtbx mirrors.

2) BBox semantics and array slicing
   - Confirm that the bbox produced/consumed yields correct Python slicing with our usage:
     - We currently do `x = slice(x1, x2)` and `y = slice(y1, y2)` and index `data[pid, y, x]`.
   - If DIALS treats bbox as inclusive on the upper bound, we need to adjust to `x2+1`, `y2+1`. Please confirm correct convention.

3) Mask creation and formats (external hot pixel/bad pixel masks)
   - Canonical way in DIALS to create a per‑panel mask compatible with simtbx/DiffBragg (e.g., `dials.generate_mask`).
   - File formats typically emitted/consumed (Pickle/JSON/NPY/NPZ/HDF5), shapes, dtype (0/1 vs boolean), and how panel ordering maps to Experiment.Detector panels and to `image_data_from_expt` output.
   - Any “trusted_range” related masking DIALS performs by default that we should mimic.

4) Image calibration and units
   - Typical state of the images when accessed via dxtbx/Experiment in our pipeline:
     - Are values pedestal/gain corrected? Units (ADU/electrons/photons)?
     - If there’s no standard guarantee, which metadata fields expose gain/saturation for us to build masks or a calibration factor?

5) Full-frame shapes and panel ordering
   - Confirm the exact shapes for arrays returned by upstream helpers:
     - `data`: `(n_panels, slow, fast)`
     - `background_image`: same shape, invalid pixels sentinel‑filled (we assume −1).
   - Confirm that reflection table `panel` indices, `pids` array from simtbx, and the first axis of `data` all use the same panel ordering.

Deliverables
- A concise write‑up answering the above, with code pointers to the relevant DIALS/dxtbx modules.
- If possible, a small code snippet that:
  1) Reads a .refl file,
  2) Prints columns/types we need (id/panel/bbox/...),
  3) Validates bbox slicing against an image array (i.e., pulls out a shoebox from `data` using the reported bbox),
  4) Demonstrates reading/applying a mask file matching what DiffBragg expects.

Why this matters
- Consistent ROI/mask interpretation is essential for the masked MSE loss and for matching DiffBragg convergence. Clarifying these conventions removes ambiguity and reduces failure risk during validation.

