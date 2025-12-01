### Turn Summary
Fixed Stage C warm-cache gradient tracking by preserving tensor offsets through detector retargeting (GRADIENT-004); both Stage B and Stage C smokes now pass with warm cache and panel mode.
The root issue was .item() conversions detaching distance_offset_raw tensors from autograd, causing LBFGS to fail with "element 0 does not require grad"; fix involved keeping tensors through _retarget_stage_a_detectors and correcting telemetry ROI counts.
Next: Phase A.4 complete - all Stage helpers extracted, engine-only routing operational; ready for Phase B (RefinementContext/JobContext dataclasses) or RefinementConfig attribute cleanup.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/ (pytest_stage_bc_small.log, pytest_stage_bc_small_v2.log, telemetry_stage_bc_small_v2.json)
