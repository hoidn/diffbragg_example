### Turn Summary
Scoped Phase A.4 to remove the run_nanobrag_refinement inline Stage B/C branch and updated docs/fix_plan plus input.md so Ralph can ship the engine-only path next loop.
Traced StageA/StageB/StageC helper coverage, confirmed stage_c_impl already emits bragg buffers, and documented how StageC.run + RefinementEngine need to cache that output while CLI/tests drop the old --use-engine-delegation gate.
Next: Ralph implements the run_nanobrag_refinement/StageC/engine rewiring and reruns the merged Stage B+C smokes (`test_stage_b_shell_modifiers` + `test_stage_c_detector_microslip`) on the small detector bundle.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/ (summary.md)
