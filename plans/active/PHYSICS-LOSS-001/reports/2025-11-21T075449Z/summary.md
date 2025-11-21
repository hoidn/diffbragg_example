### Turn Summary
Implemented metadata-aware DB-AT-024 plumbing and CLI diagnostics assertions so sigma_readout provenance and clamp telemetry align with spec without dropping refined geometry.
DB-AT-024 now consumes external_lookup tiles through prepare_refinement_inputs and records chi-squared + sigma lineage in mapping_metrics.json, while tests/dbex/test_refine_one_cli.py verifies `/torch_diagnostics` attrs for both cli_override and metadata runs.
Next: flow the same metadata handling into the remaining acceptance gates once scheduled (Stage A regression + CLI parity hooks).
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/ (collect_db_at_024_metadata.log, pytest_db_at_024_metadata.log, mapping_metrics.json, collect_cli_metadata.log, pytest_cli_metadata.log)

### Turn Summary
Closed Phase H by logging the Stage B/C metadata artifacts and expanded `plans/active/PHYSICS-LOSS-001/implementation.md` with a new Phase I targeting DB-AT-024 + CLI diagnostics metadata coverage.
Updated docs/fix_plan.md Attempts History and rewrote input.md so Ralph now has a ready-for-implementation Do Now to plumb `smoke_sigma_source` through the DB-AT harness, assert metadata provenance/clamp telemetry, extend CLI diagnostics coverage, and refresh the Testing Guide/Test Suite Index.
Staged plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/ for upcoming pytest logs plus mapping_metrics artifacts so execution evidence lands in one place.
Next: Ralph implements the DB-AT/CLI metadata changes and reruns the mapped selectors before we tackle the remaining Phase G fixture-manifest tasks.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/ (summary.md)
