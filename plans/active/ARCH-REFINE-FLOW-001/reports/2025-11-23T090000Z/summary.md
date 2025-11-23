### Turn Summary (Ralph loop i=212)
Implemented partial CPU fallback fix for Stage B engine delegation path; final Bragg reconstruction now uses CPU device when needed.
Test still fails with CUDA OOM in different location (physics.py:79 vs crystal.py:356), indicating Stage B closure also needs CPU device propagation investigation.
Next: Debug _build_stage_b_lbfgs_closure device usage and verify stage_b_eval_stage_a_ctx device propagation.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/ (pytest_stage_b_full_after_fix2.log)
