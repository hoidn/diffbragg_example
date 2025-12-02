### Turn Summary
Hoisted Stage A/B/C helper imports to module scope, eliminating lazy-import pattern per ARCH-REFINE-001.
Deleted `_lazy_import_refinement` from Stage A; all runtime dependencies now declared explicitly at module top.
Next: Stage B/C smoke tests passed; Stage A smoke failed on pre-existing test gate (log_scale delta magnitude), not import issue.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/ (collect_stage_a_small.log, pytest_stage_a_small.log, collect_stage_b_small.log, pytest_stage_b_small.log, collect_stage_c_small.log, pytest_stage_c_small.log, telemetry_stage_c_small.json)
