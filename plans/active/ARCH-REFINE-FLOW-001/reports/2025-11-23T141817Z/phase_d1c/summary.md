### Turn Summary
Extracted _run_stage_c_lbfgs helper (296 lines) and wired all 3 Stage C helpers into run_nanobrag_refinement, reducing inline code by 420 lines (net -124 lines).
Fixed multiple dict key mismatches (target_t, loss_mask_t, sigma_readout_t) and added missing lazy imports to helper2's compute_loss_stage_c closure.
Both regression tests (small + full detector) PASSED; Phase D1c complete, ready for Phase D2.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/ (pytest_stage_c_small.log, pytest_stage_c_full.log, metrics.json, decision.md)
