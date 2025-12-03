### Turn Summary
Implemented mask normalization so reconstruction cold-path mirrors Stage A's device/dtype tensor handling; intensity probe now shows perfect 1.0 parity across all three simulator paths.
Resolved the 18% raw output discrepancy (0.847→1.0 ratio) by normalizing detector_config.mask_array before passing to create_unified_simulator; exit criterion #1 (raw output magnitude parity) is now satisfied.
Next: investigate why DB-AT-028/029 tests still fail with chi²/ROI issues despite simulator parity—likely involves loss computation layers, scale application, or test fixture N_cells mismatch (probe used [36,28,26], tests show [41,29,32]).
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T230000Z/ (simulator_intensity_metrics.json, pytest_db_at_028_029.log, mask_coverage.json)
