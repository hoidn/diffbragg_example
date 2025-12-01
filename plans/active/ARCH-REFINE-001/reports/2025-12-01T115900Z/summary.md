### Turn Summary
Implemented RefinementContext dataclass scaffolding per ARCH-REFINE-001 Phase B.1; context builder validates inputs and all three stages now consume context.
Encountered blocker when creating `_build_final_bragg_from_stage_a_telemetry` helper: `create_crystal_config()` API signature mismatch (doesn't accept `log_cell_a_delta` keyword arguments).
Next: inspect `create_crystal_config()` signature in `dbex/nanobrag_bridge.py`, correct parameter names in `_build_final_bragg_from_stage_a_telemetry`, then rerun Stage A smoke test.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/ (pytest_stage_a.log, context.py created)
