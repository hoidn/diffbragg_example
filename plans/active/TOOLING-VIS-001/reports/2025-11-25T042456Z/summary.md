### Turn Summary
Fixed mapping forward HKL wiring so parity probe and DB-AT-028/029 selectors successfully extract indices/amplitudes from miller arrays when refined MTZ is unavailable, clearing the KeyError blocker.
The mapping forward pass now succeeds with `mapping_forward_success=true` in both parity probe (ROI CC=0.6206) and pytest fixtures, capturing diagnostic metrics even though Stage A reconstruction still shows poor correlation (separate physics issue).
Next: investigate why parity probe shows good mapping ROI CC (0.62) while pytest fixture shows poor mapping ROI CC (-0.04), then address Stage A reconstruction/calibration alignment for DB-AT-028/029.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T042456Z/ (parity_probe.log, parity_metrics.json, db_at_028/, db_at_029/)
