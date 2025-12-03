### Turn Summary
Verified baseline_crystal fix already applied (line 326: baseline_crystal=crystal), test infrastructure blocked by sigma source mismatch (cli_map vs external_lookup).
Test SKIPPED because fixture passes sigma via CLI args (source="cli_map") but test requires external_lookup embedding in experiment imageset metadata.
Documented blocker in test_blocker_analysis.md; requires running embed_sigma_external_lookup.py to embed tiles in idx-0000_sigma_metadata.expt before parity validation can proceed.
Artifacts: plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/ (pytest_stage_b_fixed.log, test_blocker_analysis.md)
