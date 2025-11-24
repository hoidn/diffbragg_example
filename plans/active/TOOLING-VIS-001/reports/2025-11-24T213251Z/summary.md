### Turn Summary
Implemented Stage A mapping telemetry capture and diagnostic analysis per DB-AT-027/028/029 specs; extended refGeom driver with --out-dir flag and JSON metric emission capturing chi²_per_pixel, ROI correlations, and intensity ratios.
All three conformance tests FAILED with pathological gaps: zero-point equivalence mean_abs_diff=77.43 ADU (spec ≤1e-3), chi²_per_pixel ~1000x too large (109,022 initial vs spec ≤100), and median ROI correlation 0.128 below 0.2 floor; root cause likely missing spot_scale_override calibration (3.18e+17) in Stage A reconstruction path.
Next: Phase D.B0 zero-point probe to isolate calibration/geometry misalignment between Stage A forward model and mapping baseline.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/ (stage_a_mapping_diagnosis.md, stage_a_mapping_gap_metrics.json, db_at_024/)
