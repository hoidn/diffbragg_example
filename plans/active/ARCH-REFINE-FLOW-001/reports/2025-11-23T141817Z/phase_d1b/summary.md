### Turn Summary
Extracted `_build_stage_c_lbfgs_closure` helper (298 lines) containing TWO nested functions (`compute_loss_stage_c` + `closure_stage_c`) with captured lexical scope from 25+ variables unpacked from input dicts per specification; compilation PASSED with clean import and correct function signature returning tuple of callables.
All PHYSICS-LOSS-001/002 variance-weighted loss patterns and PERF-WARM-011/012 warm-cache ROI sampling preserved; lazy imports stay inside nested functions per RUNTIME-001.
Next: Phase D1c to extract `_run_stage_c_lbfgs` execution helper, wire all three Stage C helpers, and run full regression guard (small + full detector smoke tests).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/ (compilation_check.log, helper_diff.patch, metrics.json, decision.md)
