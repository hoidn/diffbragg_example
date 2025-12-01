### Turn Summary
Extended RefinementContext with asu_map/hkl_indices_grid/halo_mask fields and threaded CLI-built HKL metadata through all three engine branches so Stage B/C no longer recompute ASU mappings when JobContext provides them.
Both Stage B shell modifiers and Stage C detector microslip smokes pass cleanly on small detector (PASSED in 22.4s and 7.6s respectively), proving REFINE-005 ASU reuse works without breaking warm-cache gradient tracking (GRADIENT-004).
Next: Phase B.4 will wire the simulator factory for forward-only helpers once shared context metadata stabilizes.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/ (pytest_stage_b_small.log, pytest_stage_c_small.log, telemetry_stage_b_small.json, telemetry_stage_c_small.json, context.idl.md)
