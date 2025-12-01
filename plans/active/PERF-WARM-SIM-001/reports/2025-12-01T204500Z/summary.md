### Turn Summary
Logged REFINE-014 and rewrote the plan/input so Stage C consumes Stage A’s raw orientation tensor instead of the post-tanh misset angles that currently inflate chi² by 0.067%.
Traced the regression to dbex/refinement/stage_c.py:174-355 and captured telemetry evidence under 2025-12-01T200900Z showing offsets recover but chi² stays flat; no code landed yet because this was a planning loop.
Next: implement the orientation tensor wiring and rerun the Stage C smoketests plus the warm-cache summarizer to clear REFINE-007.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/ (summary.md)
