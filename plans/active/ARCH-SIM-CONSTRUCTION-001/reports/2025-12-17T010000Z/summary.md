### Turn Summary

Implemented geometry mode parameterization for Stage A baseline probe (`--geometry-mode {perturbed,baseline}` flag) to isolate geometry perturbation effects from DB-AT-027 parity validation. Validation with baseline mode shows perfect ROI correlation (CC=1.0) but persistent magnitude discrepancy (max|Δ|=18,775 ADU, 35% mean difference), ruling out geometry perturbation as the root cause. DB-AT-028/029 continue to fail with chi²=2.097e5 (4 orders above spec) and negative ROI correlation (-0.053), confirming fundamental scale/physics mismatch between Stage A and mapping forward models.

Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/` (baseline probe JSON/log, pytest logs, DB-AT metrics JSONs)
