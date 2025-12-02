### Turn Summary
Implemented ExperimentModel adapter (~110 lines) in helpers.py and wired Phase A3 parity test (~120 lines), but encountered parity blocker: max abs diff 5.03e-03 exceeds 1e-6 tolerance by 5000x.
Debug evidence shows localized outliers (MSE=2.41e-11) with nearly identical image statistics, suggesting a small number of pixels diverge significantly rather than systematic error.
One fix attempt (added beam_config to Crystal constructor matching ExperimentModel pattern) had no effect on parity metrics.
Documented blocker in phase_b3_decision.md Path B with root cause investigation steps; adapter code complete but Phase B3 blocked pending evidence gathering (HKL attachment audit, diff heatmap, tolerance evaluation).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/ (phase_b3_decision.md, pytest_experiment_parity.log, pytest_experiment_parity_fixed.log)
