### Turn Summary
Captured the 2025-12-01T173200Z Stage C telemetry with the warm-cache summarizer, confirming both detector sizes now run panel-mode closures yet still regress chi² by 0.063–0.067% even while offsets shrink 99.99999%.
Tied the regression to REFINE-012’s “force panel closures” logic and sketched the fix: keep ROI closures when Stage A telemetry says ROI, but keep validations panel-scoped and expose a new validation_scope perf counter.
Updated docs/fix_plan.md and input.md so Ralph patches dbex/refinement/stage_c_impl.py plus the Stage C smoketest, then reruns both detector-size selectors with telemetry under the new artifacts path.
Next: implement the ROI-closure restoration and re-run the small/full Stage C smokes plus the summarizer to verify REFINE-007 passes again.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T173344Z/ (stage_c_warm_cache_report.json, summarize_stage_c_warm_cache.log)
