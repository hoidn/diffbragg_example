### Turn Summary
Recorded the telemetry-aligned yet under-scaled Stage A failure in `docs/fix_plan.md` and explained why we now need to derive the baseline from the warmed Stage A context.
Refreshed `input.md` with a ready-for-implementation Do Now that has Ralph compute the zero-iteration Stage A mean, set `log_scale_baseline` from that ratio, and rerun DB-AT-028/029 while archiving artifacts under `plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/`.
Next: engineer implements the Stage A mean-based baseline and reruns the smoke selectors to verify `scale_ratio_before≈scale_ratio_mapping_masked`.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/ (collect + run logs once Ralph executes the Do Now)
