2025-12-01T08:09:03Z focus=ARCH-REFINE-001 state=planning dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/ next_action=ready_for_implementation
- Stage A helper stack (StageAContext, quaternion utils, `_build_stage_a_*`) still lives inside `dbex.nanobrag_refinement`, forcing StageA/StageB wrappers to import the monolith and blocking full engine delegation. Tonight’s plan splits those helpers into a refinement-owned module, reuses it from the inline path, and keeps telemetry/perf counters intact per PHYSICS-LOSS-001 + PERF-WARM-001.
- Do Now handed to Ralph: relocate the helpers/dataclasses + quaternion math into `dbex/refinement/` (no new circular imports), update all consumers (StageA, inline LBFGS, tools), then rerun the Stage A expansion + engine telemetry selectors plus the Stage B shell smoke to ensure parameter reconstruction and warm caches survive.
Action State: ready_for_implementation
2025-12-01T084505Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/ next_action=ready_for_implementation
- Planned Phase A.2 Stage B helper extraction (new stage_b_impl module, ASU/shell utilities move, StageB+inline imports) and refreshed Do Now/tests accordingly.
- Updated docs/fix_plan.md Attempts History plus input.md (Do Now + How-To Map) so Ralph can execute helper migration with Stage B shell/per-reflection smokes.
Action State: ready_for_implementation
