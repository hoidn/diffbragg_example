### Turn Summary
Implemented 5 gradient diagnostic tests that systematically isolated the magnitude mismatch source; all synthetic tests pass while only real refGeom data fails.
The DBEX integration layer does not break cell parameter gradients for synthetic cubic crystals; the magnitude issue is specific to real experiment metadata.
Mosaic parameters (ML_half_mosaicity_deg, ML_domain_size_ang) extracted from experiment are suspected root cause; recommend trying mosaic_spread_deg=0.0 workaround.
Next: Verify mosaic hypothesis with diagnostic probe on real data values, or apply mosaic workaround to confirm coupling.
Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T232143Z/ (magnitude_audit.md, gradient_diagnostic.log, minimal_gradcheck.log)
