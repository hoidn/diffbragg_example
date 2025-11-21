### Turn Summary
Enabled Stage B/C smoke selectors to consume the metadata sigma fixtures, guard the assets in tests/conftest.py/refinement_inputs, and updated Stage B/C telemetry asserts plus docs/fix-plan.
Ran the metadata collect-only gate and full Stage B/C smoke command under DBEX_SMOKE_SIGMA_SOURCE=metadata to capture provenance evidence in plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/.
Next: extend the metadata sigma knob to DB-AT-024 and CLI diagnostics selectors so acceptance gates log the same provenance.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/ (collect_stage_b_metadata.log, pytest_stage_bc_metadata.log)

### Turn Summary
Scoped Phase H for metadata-backed Stage B/C coverage, updated the implementation plan and fix-plan ledger, and rewrote input.md with a ready-for-implementation Do Now for the Stage B/C smokes.
Captured evidence that Stage B/C still skip when metadata is selected (missing markers + hard-coded provenance) and documented the remediation path plus artifact targets under the new report directory.
Next: Ralph implements the Stage B/C metadata plumbing/tests and reruns the Stage B/C smoke selectors with `DBEX_SMOKE_SIGMA_SOURCE=metadata` to capture logs + telemetry.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/ (input.md, summary.md)
