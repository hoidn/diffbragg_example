### Turn Summary
Extended RefinementSharedContext with optional baseline_detector field and threaded it through Stage A/B/C helpers via compatibility shims, collapsing 11-parameter data clumps into typed dataclasses.
Stage C small-detector test and Stage A engine delegation test both passed, validating the typed context path works correctly without regressing telemetry enrichment. Stage C full-detector test failed due to pre-existing PERF-WARM-SIM-001 ROI-mode disparity (panel 0 offset 0.465mm, same signature as prior loop), which is orthogonal to the context refactoring.
Next: Phase A complete (all stages accept RefinementSharedContext); move to Phase B to introduce StageArtifacts dataclass for typed artifact emission.
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/ (collect_stage_c.log, pytest_stage_c_small.log, pytest_stage_c_full.log, pytest_stage_a_engine.log, telemetry_stage_c_small.json, telemetry_stage_c_full.json)
