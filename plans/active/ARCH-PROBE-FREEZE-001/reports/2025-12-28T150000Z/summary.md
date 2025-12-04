### Turn Summary (Galph — 2025-12-28T150000Z)

Stage A baseline telemetry plumbing now lives in production code (`dbex/refinement/stage_a.py:2134-2199`) and the probe has been collapsed into a thin wrapper (`plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py`). The new helper (`dbex/refinement/telemetry_baseline.py`) and pytest `test_stage_a_baseline_metrics_dump` confirm the schema, but DB-AT-028/029 still compute parity artifacts without enabling the metrics hook, and no code wires the `DBEX_STAGE_A_BASELINE_METRICS_PATH` env knob yet. Result: plan-local probes remain the only way to collect decision-carrying baseline JSON for the acceptance selectors.

**Gaps identified**
1. `stage_a_smoke_result` never toggles `enable_stage_a_baseline_metrics`, so Stage A does not emit the new payload during DB-AT runs.
2. The supposed env knob (`DBEX_STAGE_A_BASELINE_METRICS_PATH`) is only mentioned in comments; no factory reads it, and DB-AT tests never assert that a metrics JSON is written.
3. Without an automated artifact path, the refactored probe still needs to be run manually to populate parity ledgers, violating the probe-freeze mandate.

**Next loop focus (Phase B.3 completion)**
- Thread an opt-in metrics path through the Stage A smoke fixture (derive per-test filenames under `DBAT028_ARTIFACT_DIR` / `DBAT029_ARTIFACT_DIR` or honor `DBEX_STAGE_A_BASELINE_METRICS_PATH`). Set `enable_stage_a_baseline_metrics=True` whenever the path resolves.
- Surface the resolved JSON path + StageAArtifacts.baseline_metrics on the fixture result so DB-AT-028/029 can verify schema and persist the emitted file alongside their current metrics dumps.
- Update the tests to fail if the Stage A baseline metrics file is missing or malformed, ensuring parity evidence flows through the production hook.
- Document the new env usage in `docs/TESTING_GUIDE.md` and reserve the report directory for the resulting JSON/pytest logs.

Artifacts for the implementation loop should land under `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T150000Z/` (baseline metrics JSON, pytest logs for the refreshed DB-AT selectors, helper notes).
