### Turn Summary
Exited maintenance mode after analyzing Phase B.8 findings: all synthetic tests pass, only real refGeom data fails, isolating the issue to experiment metadata.
Identified mosaic code path as suspected root cause — `ML_half_mosaicity_deg` sets `mosaic_spread_deg > 0`, triggering a different simulation path with incorrect gradients.
Delegated Phase B.9 to Ralph: create `test_db_at_010_gradcheck_cell_a_no_mosaic` that bypasses mosaic extraction via `experiment=None`.
Next: Run new no-mosaic test; if PASS confirms mosaic coupling hypothesis and cell magnitude issue is fully attributable to upstream mosaic bug.
Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/ (input.md written, summary.md)
