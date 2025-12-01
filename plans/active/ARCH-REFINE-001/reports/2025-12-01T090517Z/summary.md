### Turn Summary
Successfully extracted all Stage C LBFGS helpers to dbex/refinement/stage_c_impl.py, completing ARCH-REFINE-001 Phase A.3.
Created _retarget_stage_a_detectors helper for warm-cache detector retargeting and migrated _build_stage_c_params, _build_stage_c_lbfgs_closure, and _run_stage_c_lbfgs to the new module; fixed syntax error in RefinementTelemetry.to_dict() and pre-existing bugs in stage_a.py and nanobrag_refinement.py (log_cell_max_delta, cached crystal access).
Stage C smoke test shows both Stage A+C telemetry generated correctly with detector offset parameters present; test failure due to unrelated pre-existing RefinementConfig missing attributes (blocked on config refactoring).
Next: Phase A.4 to extract remaining inline Stage C code path or address RefinementConfig attribute issues.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/ (pytest_stage_c_small.log, pytest_stage_c_final.log, summary.md)
