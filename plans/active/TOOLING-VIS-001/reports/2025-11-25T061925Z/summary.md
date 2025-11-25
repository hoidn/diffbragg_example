### Turn Summary
Sigma-source comparison confirmed mapping forward remains anti-correlated (ROI CC≈-0.04) for both metadata and cli_override despite parity between CPU/GPU and shared HKL counts.
DB-AT-028/029 still fail with chi²/pixel≈1.08e5 and median_corr_before≈-0.05, so the gap is now isolated to mapping HKL/geometry configuration rather than sigma sourcing.
Next: add HKL/MTZ override support to the probe and Stage A smoke fixture (scaled vs refined), then rerun the probes and DB-AT-028/029 with metadata sigma to see if correlation improves.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/ (summary.md)
