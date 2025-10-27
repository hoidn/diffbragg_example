# DIALS API (Reflections, Masks, Shapes)

This document focuses on reflection table semantics, ROI bbox conventions, and mask formats relevant to dbex and simtbx background estimation.

## Reflection Tables (.refl)
- Minimal columns for simtbx ROI/background:
  - `id` → matches `ExperimentList` index.
  - `panel` → panel index aligned with `Experiment.detector` and image stack first axis.
  - `bbox` → tuple with fast/slow, z extents: commonly `(x0, x1, y0, y1, z0, z1)`.
    - For ROI slicing of 2D stills, use `(x0, x1, y0, y1)`; `x1`/`y1` are exclusive bounds.
  - Optional: `xyzobs.px.value`, `shoebox` may be present but are not strictly required by simtbx ROI helper when bbox is provided.
- Alignment:
  - Panel indices in reflection tables align with `image_data_from_expt(expt)` stack and simtbx ROI `panel_ids`.

## Mask Generation and Formats
- Trusted mask:
  - DIALS tooling can generate “trusted” masks per panel based on detector metadata (trusted range, gain, saturation).
  - DiffBragg expects a pickled DIALS mask file (tuple of flex.bool per panel) at `prm.roi.hotpixel_mask`.
  - During ROI gathering, this “trusted” mask is inverted to a “hot/bad” mask for rejection counts.
- Conversions:
  - When starting from NumPy boolean masks, use `simtbx.diffBragg.utils.save_numpy_mask_as_flex()` to produce the compatible pickled flex format.
- Shapes:
  - Masks and images are `[panel, slow, fast]`; ensure panel count and per‑panel shapes match the detector.

## Shapes and Slicing
- Image stacks: `[n_panels, slow, fast]` (NumPy arrays when via simtbx).
- ROI bbox: `(x0, x1, y0, y1)` with exclusive upper bounds; slice images as `imgs[pid, y0:y1, x0:x1]`.
- Reflection alignment: Ensure all three—reflection `panel`, image stack panel axis, and detector index—use the same ordering.

