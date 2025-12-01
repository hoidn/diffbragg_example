### Turn Summary
Implemented env-gated panel-loss diagnostics for Stage A and Stage C, capturing per-panel chi², mask, sigma, and target checksums via `DBEX_STAGE_C_PANEL_DIAG_DIR`.
Confirmed chi² regression (+0.063-0.067%) persists despite perfect detector-offset recovery (≥99.999%); diagnostics show uniform delta across panels rather than localized divergence.
Next: Investigate Stage A best-snapshot rollback logic, Stage C iteration=0 param alignment, or use callchain analysis to trace where the 0.067% drift originates in `_compute_panel_loss`.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/ (panel_diag/{small,full}/{stage_a_panel_diag.json, stage_c_panel_diag.json, panel_diag_compare_{small,full}.{json,md}}, telemetry JSONs, stage_c_warm_cache_report.json)
