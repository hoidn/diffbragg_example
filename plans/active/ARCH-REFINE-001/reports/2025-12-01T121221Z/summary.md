### Turn Summary
Captured the Phase B.1 status plus the Phase B.2 JobContext scope so engine inputs can finally carry CLI/data provenance without recomputing globals.
Rewrote input.md with the concrete JobContext implementation plan and Stage A/B/C smoke + CLI selectors so Ralph can execute immediately.
Next: Implement the JobContext dataclass, thread it through run_nanobrag_backend/run_nanobrag_refinement, and rerun the mapped smokes + CLI test while logging telemetry under this report path.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/ (summary.md)
