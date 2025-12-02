### Turn Summary
Relocated StageAROIEntry and StageAContext dataclasses to context.py and deleted stage_a_impl.py; all 5 existing mapped tests passed.
Fixed _compute_variance_weighted_loss import to use canonical physics.loss source instead of stage_a_impl re-export; updated 5 import sites across stage_a_utils/stage_c/stage_a/nanobrag_refinement/tools.
ARCH-REFACTOR-001 Exit Criterion #1 fully satisfied: all *_impl.py modules (stage_a_impl, stage_b_impl, stage_c_impl) eliminated; net -1460 lines repo-wide.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/ (pytest_stage_a_expansion.log, pytest_stage_a_telemetry.log, pytest_stage_b_guard.log, pytest_stage_b_shell.log, pytest_stage_c_smoke.log, remaining_imports.txt, missing_test_note.txt)
