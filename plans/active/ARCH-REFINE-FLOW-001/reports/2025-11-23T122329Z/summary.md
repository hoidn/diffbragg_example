### Turn Summary
Identified HKL grid device routing bug as root cause of CPU fallback zero-Bragg failure: closure transfers CUDA hkl_grid to CPU instead of using CPU-native stage_b_eval_stage_a_ctx.hkl_grid.
Ralph's minimal reproducer (loop i=220) proved nanobrag_torch works correctly on CPU with 99% Bragg coverage; parameter parity (loop i=219) ruled out config mismatch.
Next: apply targeted 5-line fix at line 2464, validate both full+small detector tests pass, then proceed to Phase C validation (C3-C5).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/ (input.md with fix strategy, reproducer evidence cross-refs)
