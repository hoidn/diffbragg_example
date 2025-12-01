### Turn Summary
Implemented Stage A telemetry baseline capture so loss/chi-squared traces always include initial values before LBFGS optimization.
Resolved empty-trace regressions by adding pre-optimization evaluation and exception-path guards; Stage B smoke now passes.
Stage C smoke reveals pre-existing zero-improvement issue on small detector (initial=final=3.31e+08), unrelated to telemetry fix.
Next: Investigate Stage A zero-improvement blocker on small detector configuration before resuming Stage C validation.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/ (pytest_stage_b_final.log, pytest_stage_c_final.log, telemetry JSONs)
