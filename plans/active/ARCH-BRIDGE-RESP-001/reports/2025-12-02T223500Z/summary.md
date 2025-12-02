### Turn Summary
Implemented reusable ROI scoring helper (score_roi_payloads) that runs Nelder-Mead + roiCheck to populate typed payloads with scores/scales/variance; no writer/CLI changes yet.
Created 5 unit tests validating scale recovery, variance floor, injected hooks, and sigma validation (all PASSED); existing CLI metadata test remains green.
Next: Phase B.2 — wire CLI and engine paths to call score_roi_payloads before write_torch_outputs, then remove inline scoring from writer.
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/ (pytest_roi_analysis.log, pytest_torch_writer_metadata.log, pytest_collect_roi_analysis.log)
