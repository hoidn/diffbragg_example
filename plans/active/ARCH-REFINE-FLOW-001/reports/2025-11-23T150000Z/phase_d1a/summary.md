### Turn Summary
Extracted `_build_stage_c_params` helper function (156 lines) from inline Stage C code and inserted at line 2737 of `dbex/nanobrag_refinement.py`.
Compilation passed cleanly and regression guard test (Stage C smoke, small detector) passed in 15.99s with no behavior change.
Next: proceed to Phase D1b to extract `_build_stage_c_lbfgs_closure` helper (~400 lines containing the nested loss closures).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/ (compilation_check.log, pytest_stage_c_regression.log, helper_diff.patch, metrics.json, decision.md)
