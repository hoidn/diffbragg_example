### Turn Summary
Reviewed Phase A reality check results (i=182): 12/15 tests pass, 3 fail due to compute_z_scores() signature mismatch.
Root cause confirmed: parity_loader.py:604 missing required `variance` argument; fix is single-line per spec-db-core.md.
Next: Ralph applies fix (variance = predicted + sigma_readout²), re-runs tests expecting 15/15 PASS.
Artifacts: plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T120000Z/ (input.md delivered)
