# ARCH-SIM-CONSTRUCTION-001 Supervisor Notes — 2025-12-15T235500Z

## Why we’re here
- Stage A cache fast path shipped (2025-12-15T150000Z) but DB-AT-028/029 still fail because the cached zero-iteration tensor and telemetry `model_mean_masked` remain at the pre-scale ~11.57 ADU level; the masked target is 87.12 ADU.
- Evidence: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T150000Z/stage_a_baseline_probe.json` shows `model_mean_masked=11.57`, `target_mean_masked=87.12`, yet cache parity ratio = 1.0, proving reconstruction now faithfully replays the *wrong* tensor.

## Decision / Plan
1. **Phase C.10 scope** — After the masked-intensity ratio updates `log_scale_baseline`, compute `scale_factor_zero_iter = exp(log_scale_baseline + clamp(initial_log_scale))` and multiply `stage_a_ctx.bragg_zero_iter` by this factor so the cache holds the calibrated pre-LBFGS prediction.
2. Update `model_mean_masked` so telemetry reflects the scaled mean (≈87 ADU) instead of the pre-scale ~11 ADU value.
3. Extend `tests/dbex/test_artifact_parity.py` to assert the cached masked mean matches telemetry when warm cache is enabled, catching regressions.
4. Collect fresh evidence under this directory: rerun `compare_stage_a_baseline.py` plus `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with env vars pointing here.

## Artifacts
- `summary.md` (this file)
- Awaiting: `stage_a_baseline_probe.json`, `pytest_db_at_028_029.log`, `db_at_028/029` metric folders after Ralph executes the Do Now.
