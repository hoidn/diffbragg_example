### Turn Summary
Threaded `oversample` parameter through RefinementConfig → warm simulator context builders → all 4 `create_detector_config` call sites to fix 290/292 DetectorConfig instances having default oversample=-1.
Debug validation confirmed 292/292 instances now have oversample=3 with zero auto-selection events, resolving the root cause of Phase B deep-copy failure (config lifecycle issue, not mutation issue).
Next: Mark DIAG-NANOBRAGG-OVERSAMPLE-001 done and unblock ARCH-SIM-CONSTRUCTION-001 to address remaining magnitude discrepancy.
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/ (debug_validation.md, pytest_db_at_028_debug.log, nanobragg_rebuild_clean.log)
