### Turn Summary
Extended the telemetry plan so Stage C can treat the seeded baseline as a synthetic closure whenever LBFGS exits without evaluating, keeping perf counters in sync with the observer channel.
Updated docs/fix_plan.md, the Phase C checklist, galph_memory, and input.md so Ralph has concrete instructions to add the increment flag, touch `_run_stage_c_lbfgs`, and rerun the Stage B/C smoketests with fresh logs.
Next: implement the helper + closure changes and capture the Stage B guard, Stage B shell, and Stage C detector logs in the reserved artifacts directory.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T235900Z/ (summary.md)
