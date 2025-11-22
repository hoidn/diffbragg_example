### Turn Summary
Reviewed Phase B1 gradient probe results and confirmed the explicit cell+misset parameterization at zero deltas yields χ² ≈ 2.98e6 (≈2.6× higher than mapping MOSFLM path), proving Adam legitimately walks away due to large non-zero gradients (orientation_vec magnitude ≈2.88e8).
The problem is NOT optimizer tuning—it's a **geometry parameterization gap** where the Phase A strain (1.4e-3 symmetric) translates directly into a significant chi-squared penalty.
Next: Phase A3 (mapping forward model comparison) to isolate whether this gap arises from cell/misset encoding conventions or simulator numerical differences, then proceed to Branch G (geometry fix) if forward models are identical.
Artifacts: plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/ (awaiting forward_model_comparison.json, forward_model_comparison.log, pytest_stage_a_regression.log, commands.txt)
