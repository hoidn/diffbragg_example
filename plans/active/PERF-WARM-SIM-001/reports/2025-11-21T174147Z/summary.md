### Micro Probes
`rg --files plans/active/PERF-WARM-SIM-001/reports | rg stage_c`
(no output — confirms no Stage C telemetry artifacts yet)

### Turn Summary
Rallied PERF-WARM-SIM-001 by drafting a ready-for-implementation Do Now so Stage C perf-counter telemetry lands with logging, summarizer, and docs/testing steps.
Validated the evidence gap via `rg --files plans/active/PERF-WARM-SIM-001/reports | rg stage_c` (no matches) and captured the requirement in docs/fix_plan.md plus the refreshed input.md handoff.
Next: Ralph implements the Stage C logging/summarizer, reruns both Stage C selectors with telemetry capture, and drops the telemetry/log/summary artifacts into the 2025-11-21T174147Z folder.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/ (summary.md)
