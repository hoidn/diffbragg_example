### Turn Summary
Scoped Phase C.2: Stage B/C observer migration is green, so we planned the work to surface the collectors’ StageResult payloads through `RefinementTelemetry`/RefinementEngine and into `dbex/io/writer.py`.
Implementation plan + docs/fix_plan.md now call for attaching the typed StageResult on each stage (Stage A finalize hook + Stage B/C reuse), piping a `stage_results` map to the writer, and keeping `/torch_diagnostics` schema intact with StageResult-first serialization.
Next: execute the Do Now (code edits + four mapped pytest selectors) under plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/ (input.md, planning notes)
