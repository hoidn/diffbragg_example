### Turn Summary
Implemented geometry zero-point comparison script to quantify drift between refGeom and refined experiments; discovered ~1° U-matrix rotation explaining Stage A mapping failure.
The ~1° orientation discrepancy causes the forward model to predict Bragg spots at systematically wrong positions, yielding negative ROI correlations (−0.04) even with correct HKL/calibration; validates that spot_scale_override≈3.1e+17 is expected, not pathological.
Next: Determine which experiment geometry is canonical (refGeom vs refined), apply minimal rotation correction to align geometries, then rerun DB-AT-028/029 to validate recovery.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/ (geometry_deltas/geometry_deltas.json with U rotation ~0.95°, summary.md, db_at_028_metrics.json, db_at_029_metrics.json)
