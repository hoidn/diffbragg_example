### Turn Summary
Instrumented `simulate_forward_once` plus Stage A/DB-AT coverage so zero-iteration diagnostics now emit canonical chi-squared + sigma-floor telemetry and Stage A smoke asserts the propagated metadata on the full detector.
Resolved the PHYSICS-LOSS-001 Do Now by running the full-detector Stage A smoke and DB-AT-024 mapping selectors (chi^2_A=1.223e8, chi^2_DB-AT=1.65e6, clamp fractions 0.0/0.697) with artifacts logged under the report directory.
Next: carry the refreshed diagnostics into the downstream parity evidence (DB-AT-010/Stage B) once the supervisor queues that loop.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/ (pytest_stage_a_full.log, pytest_db_at_024.log, telemetry_stage_a.json, mapping_metrics.json)

### Turn Summary
Converted Phase D checklists to done and scoped Phase C validation work for Stage A + DB-AT diagnostics so variance-weighted chi-squared evidence flows end-to-end.
Captured the new Do Now (simulate_forward_once diagnostics + Stage A/DB-AT-024 assertions) in docs/fix_plan.md, refreshed implementation plan, and rewrote input.md with strict env/test commands plus artifact paths.
Next: Ralph implements the simulate_forward_once + test updates, runs the Stage A full-detector smoke and DB-AT-024 selector with telemetry logging, and archives the resulting logs/JSON in the new report directory.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/ (telemetry_stage_a.json, pytest_stage_a_full.log placeholder)
