### Turn Summary
Reviewed the StageResult plumbing landed in 2025-12-04T020000Z and scoped Phase C.3 around StageResult-first writer serialization so `/torch_diagnostics` stops scraping legacy dicts.
Updated the implementation plan and docs/fix_plan.md, reserved the 2025-12-04T050000Z artifacts path, and rewrote input.md with the writer Do Now plus the CLI metadata, Stage B guard/smoke, and Stage C microslip selectors (Stage C log was missing last loop).
Next: implement the writer changes so typed StageResult telemetry/perf counters drive serialization (fallback for mocks/tests) and rerun the mapped selectors capturing all logs under this directory.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/ (summary.md, updated input.md)
