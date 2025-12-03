### Turn Summary
Debugged Ralph's Phase C.1 implementation (commit a00d42c7): he correctly extracted sqrt_spot_scale but forgot to apply the multiplication.
Confirmed via metrics: bragg_after_mean=5711 vs expected ~0.24, missing factor ~23,800 ≈ sqrt(spot_scale_override).
Next: One-line fix (add `* sqrt_spot_scale` at reconstruction.py:239) to match Stage A post-run scaling pattern (stage_a.py:443).
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T010500Z/ (debug_analysis.md, corrective input.md)
