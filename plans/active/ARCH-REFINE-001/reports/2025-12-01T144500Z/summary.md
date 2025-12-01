### Turn Summary
Removed deprecated use_engine_delegation parameter from Stage A tooling and docs, making RefinementEngine the sole execution path (ARCH-REFINE-001 Phase D.2).
Fixed pre-existing TypeError in _build_final_bragg_from_stage_a_telemetry (invalid create_detector_config parameter); both DB-AT-027 and Stage A telemetry selectors now pass.
Next: Phase D complete; advance to Phase E (torch writer+physics IDL documentation, already landed in D.1) or next planned initiative.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/ (collect_db_at_027.log, pytest_db_at_027.log, collect_stage_a_engine_telemetry.log, pytest_stage_a_engine_telemetry.log, docs_diff.md)
