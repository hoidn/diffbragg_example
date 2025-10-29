# Torch Capture Playbook

## Overview
Leverage the ROI bbox catalog to drive canonical `[panel, slow, fast]` tensor exports via `nanobrag_torch`, aligning with docs/forward_equivalence.md:21-52.

## Steps
1. Activate Environment Freeze-compliant simtbx env (`which python`) and verify `import nanobrag_torch` succeeds.
2. Load detector/beam/crystal configs via `dbex.prepare_refinement_inputs` and honor mapping rules from docs/config_crosswalk.md:15-72.
3. Run per-panel forward pass with deterministic seed + device (`CUDA_VISIBLE_DEVICES=0`, `torch.manual_seed(1337)`) and write tensors to `golden_dataset/torch/bragg_panel_{panel:02d}.npy`.
4. Slice ROI tensors using bbox entries from `roi_bbox_catalog.json`, persisting ROI extracts and documenting ordering.
5. Capture metrics (`metrics.json`) and config snapshots for parity harness ingestion.

## Preconditions
- DIFFBRAGG-001 still blocks legacy fallback; avoid rerunning broken diffBragg capture.
- Confirm ROI catalog covers exactly the legacy ROI groups (92 entries).

## Artifacts
- Tensor dumps under `plans/active/NANOBRAG-GOLDEN-001/reports/<loop>/golden_dataset/torch/`.
- Logs: `torch_capture.log`, `metrics.json`, ROI overlay placeholders.
