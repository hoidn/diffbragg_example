### Turn Summary
Extracted `_build_stage_b_params` helper function (~184 lines) from Stage B inline code into a new function at line 2087.
Python compilation passed (exit code 0); helper includes all parameter initialization, optimizer setup, telemetry accumulators, CPU fallback logic, and ROI sampling per PERF-WARM-011/012.
Helper not yet wired to main function (no behavior change); next step is C1a-loop2 to extract `_build_stage_b_lbfgs_closure` helper.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/ (phase_c1a_loop1_extraction_diff.patch, compilation_check.log)
