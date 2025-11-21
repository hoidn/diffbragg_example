### Turn Summary
Implemented the sigma-metadata manifest workflow plus docs/tests so fixtures now ship with reproducible hashes and operator guidance.
Regenerated the canonical `idx-0000_sigma_metadata` assets, captured the manifest/report under the loop, and ran the new pytest gate to show `_load_external_lookup_sigma_map` still reports `external_lookup`.
Next: wire the manifest selector into the Stage-smoke CI job once supervisors bless the workflow.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/ (pytest_sigma_metadata_fixture.log, sigma_metadata_manifest.json)
### Turn Summary
Scoped Phase G manifest/CI gate work for the metadata sigma fixtures by updating the implementation checklist (G4/G5) and recording the new attempt in docs/fix_plan.md.
Marked Phase I checklist rows complete and rewrote input.md with a ready-for-implementation Do Now covering the embed-script --manifest flag, manifest/README publishing, pytest gate, and doc updates.
Next: Ralph implements the manifest-aware embedding workflow, lands the pytest hash guard, and captures logs + manifest snapshots under the staged artifacts directory.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/ (input.md)
