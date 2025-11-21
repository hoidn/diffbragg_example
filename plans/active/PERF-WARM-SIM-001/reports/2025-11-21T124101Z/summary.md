### Turn Summary
Authored the Stage B ROI summary script and ran small-detector smoke (passed), but full-detector smoke failed because Stage B telemetry is missing the `param_deltas` field entirely.
This is an implementation bug — the shell modifier values are not being extracted from the optimizer state and written to telemetry before _record_stage_telemetry().
Marked PERF-WARM-SIM-001 as blocked and documented the bug with evidence paths in blockers.txt and fix_plan Attempts History.
Next: debug Stage B telemetry emission, add the shell_modifiers → param_deltas mapping with d-spacing labels, then rerun both smokes.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/ (pytest_stage_b_small.log, telemetry_stage_b_small.json, pytest_stage_b_full.log, blockers.txt, summarize_stage_b_roi.py)

---

### Turn Summary (Prior Loop 2025-11-21T121804Z)
Logged the Stage B ROI implementation result (small pass, canonical gate still assuming panel) and updated docs/fix_plan plus findings with the ROI-mode drift and new artifact path.
Rewrote input.md with a Do Now that adds a Stage B telemetry summary script and mandates small/full Stage B smoke reruns plus ROI summary emission.
Next: Ralph builds the summarizer, reruns the Stage B selector for both detector sizes, and updates docs/fix_plan with the captured telemetry evidence.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/ (input.md, planning notes)
