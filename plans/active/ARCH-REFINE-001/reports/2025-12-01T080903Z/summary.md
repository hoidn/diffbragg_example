### Turn Summary
Relocated Stage A helpers from nanobrag_refinement.py to dedicated stage_a_impl.py module with 1944 insertions, -1858 deletions across 5 files.
Resolved circular import by consolidating shared utilities and fixed type annotation for forward reference; all imports updated consistently.
Next: Continue with Phase A.2 to create RefinementContext/JobContext dataclasses replacing ad-hoc dict plumbing.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/ (pytest_stage_a_engine.log, pytest_stage_b_small.log, pytest_stage_a_helpers_collect.log)
