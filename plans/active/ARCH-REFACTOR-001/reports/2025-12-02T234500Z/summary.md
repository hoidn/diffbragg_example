### Turn Summary
Implemented Crystal construction fix in `build_final_bragg_from_stage_a_telemetry` warm path to pass `beam_config=stage_a_ctx.beam_config` at construction time instead of buggy `beam_config=None` + post-hoc assignment (reconstruction.py:152-165).
Tests still FAIL with identical symptoms (`bragg_after_mean = 7.63e-14`, chi²/pixel = 2.098e+05), despite fix matching input.md spec exactly. Discovered Crystal doesn't expose `beam_config` as attribute post-construction, confirming original post-hoc assignment was silently ineffective.
Suspected upstream nanobrag_torch issue or additional bug location not covered by root cause analysis; marking initiative blocked pending deeper investigation or spec clarification.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/ (pytest_parity_batch2_fixed.log, db_at_028_metrics.json)
