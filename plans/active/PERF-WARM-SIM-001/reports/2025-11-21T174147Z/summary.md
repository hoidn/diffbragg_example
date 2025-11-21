### Turn Summary
Instrumented Stage C smoke logging plus the telemetry summarizer so warm-cache perf counters and detector-offset stats show up in pytest output and consolidated artifacts.
Ran the small/full Stage C selectors with the canonical env vars, captured telemetry JSON + pytest logs, and generated `stage_c_roi_summary.json` proving both runs stayed in warm/ROI mode with the expected closure/validation counts.
Next: push PERF-WARM-SIM-001 criterion #1 by hoisting the warmed simulator contexts deeper into Stage B/C now that Stage C telemetry evidence is archived.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/ (pytest_stage_c_small.log, pytest_stage_c_full.log, stage_c_roi_summary.json)

### Micro Probes
`rg --files plans/active/PERF-WARM-SIM-001/reports | rg stage_c`
(no output — confirms no Stage C telemetry artifacts yet)

### Turn Summary
Rallied PERF-WARM-SIM-001 by drafting a ready-for-implementation Do Now so Stage C perf-counter telemetry lands with logging, summarizer, and docs/testing steps.
Validated the evidence gap via `rg --files plans/active/PERF-WARM-SIM-001/reports | rg stage_c` (no matches) and captured the requirement in docs/fix_plan.md plus the refreshed input.md handoff.
Next: Ralph implements the Stage C logging/summarizer, reruns both Stage C selectors with telemetry capture, and drops the telemetry/log/summary artifacts into the 2025-11-21T174147Z folder.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/ (summary.md)
