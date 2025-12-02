### Turn Summary
Identified root cause for bragg_after near-zero bug: Crystal constructed with beam_config=None then assigned post-hoc in reconstruction.py, violating nanobrag_torch initialization contract.
Supervisor-side code inspection (per instrumentation saturation rule after two identical failures) revealed all other Crystal constructions pass beam_config at construction time; warm cache path in build_final_bragg_from_stage_a_telemetry is the only exception.
Next: Ralph will move Crystal construction inside warm cache block and pass beam_config=stage_a_ctx.beam_config to constructor (final attempt before spec_change escalation).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/ (root_cause_analysis.md, debug_bragg_reconstruction.py)
