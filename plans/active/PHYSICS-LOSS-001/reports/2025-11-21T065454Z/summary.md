### Turn Summary
Implemented metadata sigma embedding support and Stage A smoke plumbing so Stage A can prove `external_lookup` provenance without CLI overrides.
Grounded changes in spec-db-core.md:32-68 (variance provenance) and the Stage Smoke dataset policy, refreshed docs/fix_plan, and reran the full-detector Stage A smoke under metadata (13.4 s pass).
Next: extend the metadata sigma source knob through Stage B/C smokes and DB-AT selectors to validate the entire staged refinement chain.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/ (pytest_stage_a_metadata.log, sigma_metadata.json)

### Turn Summary
Scoped Phase G to deliver a reusable refGeom metadata fixture plus Stage A smoke plumbing so `external_lookup` sigma tiles can be exercised without CLI overrides.
Updated the PHYSICS-LOSS-001 plan/fix-plan entry with the embedding script + smoke knob deliverables and marked the Phase F checklist complete while closing PERF-SMOKE-DETSIZE.
Next: Ralph builds the metadata embedding script, updates the smoke fixtures/tests/docs, and runs the Stage A full-detector selector with `DBEX_SMOKE_SIGMA_SOURCE=metadata` to capture telemetry.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/ (input.md, summary.md)
