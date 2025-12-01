### Turn Summary
Migrated Stage B helpers (_build_stage_b_params, _build_stage_b_lbfgs_closure, _run_stage_b_lbfgs) and ASU/shell utilities to dbex/refinement/stage_b_impl.py per ARCH-REFINE-001.
Encountered import collision when removing old definitions - accidentally deleted RefinementConfig and RefinementTelemetry dataclasses; restored both classes from git history.
Next: run validation tests (test_stage_b_shell_modifiers, test_stage_b_per_reflection_modifiers) to confirm helper extraction preserves behavior.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/ (stage_b_impl.py: 1163 lines)
