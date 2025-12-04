Summary: Scale the cached Stage A zero-iteration Bragg stack (and telemetry masked means) after log-scale adjustments so `bragg_before` reflects the calibrated intensity before rerunning DB-AT-028/029.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/

Do Now:
- Implement: `dbex/refinement/stage_a.py` — after the masked-intensity ratio adjusts `log_scale_baseline`, compute the zero-iteration scale factor (`log_scale_zero_iter = log_scale_baseline + clamp(initial_log_scale, ±log_scale_max_delta)` when calibrated, else clamp the raw initial log scale) and multiply `stage_a_ctx.bragg_zero_iter` by `exp(log_scale_zero_iter)` so the cached tensor represents the exact pre-LBFGS prediction. Guard cold-mode runs so the cache remains optional.
- Implement: `dbex/refinement/stage_a.py` — once the scale factor is known, update `model_mean_masked` (and any telemetry fields that consume it) to record the scaled masked mean instead of the pre-scale ≈11 ADU value so downstream probes/tests see the calibrated intensity.
- Implement: `tests/dbex/test_artifact_parity.py::test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction` — extend the coverage case to assert that the cached fast path’s masked mean matches the telemetry `model_mean_masked` value when warm cache is enabled, ensuring future refactors cannot regress the scale application.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/stage_a_baseline_probe.json` (expect telemetry masked mean ≈ reconstructed masked mean ≈ 87 ADU).
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/pytest_db_at_028_029.log`.

How-To Map:
1. In the warm-cache baseline block, reuse the existing tensors to derive `scale_factor_zero_iter = exp(log_scale_baseline + clamp(initial_log_scale))` (falling back to the uncalibrated clamp when no baseline exists).
2. Multiply `stage_a_ctx.bragg_zero_iter` by this factor immediately after it is captured so any consumers (tests, reconstruction) see the calibrated intensity; keep the assignment inside a try/except so cold-mode runs still behave.
3. Replace the stored `model_mean_masked` with `model_mean_masked * scale_factor_zero_iter` (when defined) before the telemetry dict is built.
4. Update the artifact-parity test to assert that the cached fast path’s masked mean matches telemetry, proving the scale factor is applied.
5. Run the baseline probe and DB-AT selectors with the new artifacts directory to capture the improved masked-mean parity and chi²/corr metrics.

Pitfalls To Avoid:
- Do not mutate GPU tensors in place when scaling the cached array—always operate on the CPU float32 copy to avoid device lifetime issues.
- Clamp the initial log-scale delta using the same bounds Stage A uses in `compute_loss` so the cached stack mirrors runtime behavior even when heuristics provided a large seed.
- Leave the cold-path reconstruction logic untouched; the cache remains an optional fast path, so guard all new accesses.
- Keep the parity test deterministic (use the existing Stage A fixture) so it doesn’t introduce nondeterministic ROI sampling.
- Ensure the validation commands write artifacts under the new timestamped directory so fix_plan/future loops can trace the evidence.

If Blocked:
- If scaling the cached tensor triggers memory issues, capture the traceback plus the computed scale factor in the new artifact directory and fall back to the current behavior; note the block in docs/fix_plan.md and ping Galph for escalation.
- If the parity test cannot reliably access the Stage A cache, document the limitation in the report and gate the assertion behind a warm-cache check rather than disabling the entire test.

Findings Applied (Mandatory):
- SCALE-008 — Stage A warm-cache artifacts must remain authoritative (apply baseline adjustments before exposing telemetry/cached tensors).
- SCALE-009 — Reconstruction/bragg_before parity depends on replaying Stage A’s calibrated intensity, so the cache has to carry the scaled signal.

Pointers:
- dbex/refinement/stage_a.py (baseline telemetry block around lines 400–520)
- dbex/refinement/context.py (StageAContext cache field)
- dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry (fast path expectations)
- tests/dbex/test_artifact_parity.py
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
