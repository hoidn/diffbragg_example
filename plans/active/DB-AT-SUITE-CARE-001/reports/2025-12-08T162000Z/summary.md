### Turn Summary
Received upstream response confirming nanobrag_torch gradient fixes landed; re-ran DB-AT-010 tests showing 5/5 FAIL with Jacobian magnitude mismatch (5000-127000×).
Deep investigation confirmed autograd graph IS connected (analytical gradients non-zero) but magnitudes wrong; isolated component probes (Detector.distance, Crystal.cell_a) pass individually.
Next: escalate to nanobrag_torch maintainers for physics/gradient chain audit of B-matrix → q-vector → sincg computation.
Artifacts: plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T162000Z/ (gradient_investigation_summary.md, pytest_db_at_010.log)
