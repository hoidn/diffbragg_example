### Turn Summary
Implemented gradient probe mode in stage_a_mapping_adam_debug.py showing large non-zero gradients at the mapping zero point (orientation_vec ≈2.88e8, cell_logs ≈9.82e7), proving that the explicit cell+misset parameterization at zero deltas does NOT reproduce the mapping MOSFLM A* path (χ²_explicit ≈ 2.98e6 vs χ²_mapping ≈ 1.13e6).
The Phase A strain gap (1.4e-3 symmetric) translates into a ~2.6× chi-squared penalty, validating that Adam legitimately walks away from this starting point rather than exhibiting pathological optimizer behavior.
Next: Phase B2 (scale analytical optimum check) or Phase A3 (mapping forward vs Stage-A configs comparison) to isolate the cell/misset encoding vs simulator numerical differences, OR pivot to Branch G (geometry fix).
Artifacts: plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/ (gradient_probe.json, gradient_probe.log, commands.txt, pytest_stage_a_regression.log)
