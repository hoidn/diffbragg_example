### Turn Summary
Refocused DB-AT-028/029 on diagnosis: drafted a probe and test diagnostics to compare Stage A bragg_before/after against the mapping forward stack on the smoke fixture.
Captured the persistent failure signature (chi²/pixel ~1e5, median ROI CC ~0.04) and refreshed fix_plan/input/galph_memory with the parity-probe runbook.
Next: Ralph builds the T2 parity probe, augments stage_a_smoke_result logging, runs the probe plus pytest selectors, and archives metrics for analysis.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/ (input.md, fix_plan entry, galph_memory update)
### Turn Summary
Implemented DB-AT-028/029 diagnostic instrumentation per Phase D.D; fixture now emits log_scale_effective, bragg stats, ROI CC baselines into metrics JSONs.
Tests FAILED as expected with chi²/pixel ~1e5 (vs 1e2 spec), median_corr ~-0.05 (vs 0.2 floor), isolating HKL/calibration mismatch; artifacts captured for analysis.
Next: diagnose root cause (HKL provenance/refined MTZ usage/spot_scale_override threading), implement fix, rerun DB-AT-028/029.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/ (db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json, pytest logs)
