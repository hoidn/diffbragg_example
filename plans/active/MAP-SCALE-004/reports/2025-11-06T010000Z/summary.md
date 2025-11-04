# MAP-SCALE-004 Planning Snapshot — 2025-11-06T010000Z

## Reality Check
- Confirmed `dbex/nanobrag_bridge.py::simulate_forward_once` now returns an `hkl_telemetry` dict mirroring CLI semantics (source/path/count/mean amplitude) and that DB_AT_024 enforces refined MTZ usage via new assertions (`tests/dbex/test_mapping_consistency.py:339-358`).
- Verified canonical run artifacts at `plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/` capture telemetry (`mapping_metrics.json` shows `hkl_source="refined"`, `hkl_n_reflections=69614`, mean amplitude 47.41 ADU).
- Documentation still points to pre-telemetry metrics (DB_AT_024 rows in `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reference 2025-11-04 artifacts with no telemetry call-outs) and no finding captures the new guardrail.

## Gap Assessment
- Implementation Phase A/B checklist items are satisfied; Phase C (doc + knowledge-base sync) remains.
- Need to refresh fix plan Attempts History for MAP-SCALE-004 with 2025-11-05T220000Z implementation outcome.
- New durable lesson required: zero-iteration guard must persist structure-factor telemetry and fail on raw fallbacks when refined assets exist.

## Proposed Next Steps (for input.md)
1. Update `docs/TESTING_GUIDE.md` DB_AT_024 entry with telemetry expectations, latest metrics, and artifact path `plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/`.
2. Sync `docs/development/TEST_SUITE_INDEX.md` for DB_AT_024 with telemetry description + new collect/test logs.
3. Append finding `SCALE-007` documenting the telemetry guard, referencing bridge + test paths.
4. Re-run targeted `pytest --collect-only` + DB_AT_024 smoke to confirm selector coverage after doc edits (artifact the new logs under this report if re-run occurs).

Artifacts created this loop: plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/summary.md.
