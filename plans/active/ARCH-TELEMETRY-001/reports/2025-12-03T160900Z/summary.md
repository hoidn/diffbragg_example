### Turn Summary
Scoped the Stage B/C collector migration so telemetry flows through `StageResult` objects and no longer mutates `telemetry_state` directly.
Logged the new attempt + artifact path in docs/fix_plan.md, refreshed the Phase C checklist, and rebuilt input.md with the concrete Parity-mode Do Now plus the Stage B guard and Stage B/C smoke selectors.
No blockers surfaced; next loop must land the collector implementation and rerun the mapped tests per dwell rules.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T160900Z/ (planning notes)
