### Turn Summary
Shipped masked-intensity telemetry instrumentation so reconstruction helper and probe emit baseline_stats.json with reconstructed-vs-telemetry ratios at every invocation; probe now correctly reads top-level telemetry fields instead of scraping dicts.
DB-AT-028/029 still fail (chi²≈2.1e5, ROI≈-0.05) but instrumentation reveals reconstruction produces outputs 9-30× smaller than telemetry model_mean_masked despite using recorded scale_factor.
Next: supervisor should analyze why reconstruction helper diverges from telemetry scale or escalate as suspected spec/architecture issue.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/ (baseline_stats.json, stage_a_baseline_probe.json, pytest logs)
