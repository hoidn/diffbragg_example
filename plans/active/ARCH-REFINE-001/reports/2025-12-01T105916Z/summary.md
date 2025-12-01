### Turn Summary
Implemented auto-disable ROI mode threshold (default 32) so Stage A/B/C switch to panel mode when ROI count is small, ensuring convergence on refGeom_small (29 ROIs).
Stage B passes with auto-panel mode + warm cache; Stage C blocked by gradient tracking error ("element 0 of tensors does not require grad") in panel mode.
Next: investigate Stage C gradient issue - likely detector offset parameter not properly connected to gradient graph in panel mode with warm cache.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/ (pytest_stage_bc_small_v3.log, telemetry_stage_bc_small_v3.json)
