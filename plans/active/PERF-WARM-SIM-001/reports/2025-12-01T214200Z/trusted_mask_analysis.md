# Stage C chi-squared drift root cause (2025-12-01T214200Z)

Evidence shows Stage C full-detector runs still regress REFINE-007 by +0.067% even after REFINE-011/012/013/015. Telemetry (`plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/telemetry_stage_c_full.json`) records `stage_a_final_chi2=2.10706464e+08` while every Stage C validation logs `2.10848512e+08` despite zero detector offsets, so the degradation exists before any optimization.

Code inspection pinpoints a masking mismatch:
- Stage A full validations explicitly combine the ROI/loss mask with DIALS trusted masks (`dbex/refinement/stage_a_impl.py:1336-1365`) before calling `_compute_variance_weighted_loss`, ensuring untrusted pixels never contribute to chi².
- Stage C’s `compute_loss_stage_c` never intersects `loss_mask_t` with the trusted mask when evaluating either ROI-mode closures or panel-mode validations (`dbex/refinement/stage_c_impl.py:512-580`). Warm-cache runs rely on StageAContext detectors that already zero out the mask inside the simulator, but Stage A still applies the boolean gate, so the Stage C chi² denominator includes pixels that Stage A already excluded.

Hypothesis: intersecting the trusted mask with Stage C’s loss mask before computing variance-weighted loss will align Stage C baseline with Stage A and eliminate the reproducible +0.067% drift. Implementation requires:
1. Reading `trusted_masks_t` from `StageAContext` (warm path) or tensorizing `inputs.trusted_mask` on demand (cold path).
2. Applying `torch.logical_and` in both the ROI slice loop and the panel-mode branch immediately before `_compute_variance_weighted_loss` so the same pixel population enters the metric.

Validation plan: rerun `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` for both detector sizes plus the warm-cache summarizer to prove Stage C chi² now matches Stage A within the REFINE-007 ≤0.05% gate while detector offsets still collapse.
