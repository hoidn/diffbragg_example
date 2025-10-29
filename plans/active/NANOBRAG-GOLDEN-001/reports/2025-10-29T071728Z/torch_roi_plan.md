# Torch ROI Replay Plan

Existing torch capture script present: True at plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_torch_only.py

## Proposed Steps
1. Reuse capture_torch_only.py to emit per-panel `[panel, slow, fast]` tensors under a new golden_dataset/torch/ directory.
2. Emit ROI slices by reading roi_hdf5_scout.md bbox definitions and slicing torch tensors before serialization.
3. Save numpy outputs with deterministic filenames (`bragg_panel_{idx:02d}.npy`) and matching loss masks.
4. Record torch command invocations, device selection, and seed values in capture logs for reproducibility.

## Preconditions
- Confirm `nanobrag_torch` import availability inside the frozen environment before scheduling execution.
- Ensure `KMP_DUPLICATE_LIB_OK=TRUE` and `CUDA_VISIBLE_DEVICES` policy alignment to avoid runtime divergence.

Artifacts will be staged under plans/active/NANOBRAG-GOLDEN-001/reports/<loop>/golden_dataset/torch/ once capture is authorized.
