### Turn Summary
Scoped Stage B/C telemetry collector work so the observer channel is the only writer for loss/chi² traces.
Recorded how Stage B/C closures and LBFGS helpers must drop telemetry_state mutations, rely on collector.finalize(), and captured the refreshed Do Now/tests in docs/fix_plan.md plus input.md for the 2025-12-03T150000Z artifacts.
Next: implement the collector refactor and rerun the Stage B guard plus Stage B/C smokes under the mapped commands.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T150000Z/
