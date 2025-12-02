### Turn Summary
Implemented RefinementSharedContext and StageATelemetryState dataclasses to replace 11-parameter data clump in Stage A LBFGS closure builders; compatibility shim preserves legacy dict-based callers (Stage B/C continue working).
Resolved the data-clump design smell flagged in problems.md (2025-12-01); Stage A now constructs typed context via .from_inputs() and threads it through _build_stage_a_lbfgs_closure with telemetry marker context_schema_version="v1".
Next: Extend RefinementSharedContext to Stage B and Stage C helpers so all stages use typed contexts instead of parameter clumps (Phase A.2/A.3).
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/ (collect_stage_a_small.log, pytest_stage_a_small.log, collect_stage_b_small.log, pytest_stage_b_small.log)
