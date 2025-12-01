### Turn Summary
Scoped the Stage A final Bragg reconstruction failure and wrote a Do Now that keeps RefinementContext wiring intact while fixing `_build_final_bragg_from_stage_a_telemetry`.
Captured evidence that `create_crystal_config` rejects the new kwargs and updated docs/fix_plan.md/input.md so the fix clamps the telemetry deltas, builds proper overrides, and reruns Stage A/B/C smokes with telemetry.
Next: Ralph patches `_build_final_bragg_from_stage_a_telemetry`, then replays the small-detector Stage A/B/C selectors per How-To Map.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/ (planning notes)
