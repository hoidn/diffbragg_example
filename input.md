# Input

- Summary: Validate the chi-squared telemetry rollout by upgrading the Stage B/C smokes to assert the new metrics and replay Stage A + DB-AT-024 selectors under the weighted loss.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/db_at_024 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` — extend the Stage B and Stage C smoke tests to assert the new `chi_squared_trace_*`, `chi_squared_best`, and `masked_mse_*` telemetry so regressions in the weighted-loss plumbing are caught immediately (update the Stage C section in the same file while you are here).
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, and `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/db_at_024 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (tee each log into the artifacts directory).
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/

## How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` before editing so every command recorded in artifacts inherits the authoritative reference.
2. In `tests/dbex/test_torch_refine_smoke.py`, update `test_stage_b_shell_modifiers` to read `telemetry_b.chi_squared_trace_sample/full`, `chi_squared_best`, and the masked-MSE companions, asserting that the chi-squared traces are monotonically non-increasing and that Stage B reports both metrics (Document PHYSICS-LOSS-001 + REFINE-008 in comments where you add assertions).
3. In the same file, extend `test_stage_c_detector_microslip` to compare Stage A vs Stage C `chi_squared_trace_full` entries (ensuring the gate still honors the ~0.003% improvement ceiling per REFINE-007) and assert the new telemetry datasets/attrs exist.
4. Run the Stage B smoke: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/pytest_stage_b.log`.
5. Run the Stage C smoke with the same env vars, teeing to `.../pytest_stage_c.log` to capture telemetry + improvement metrics.
6. Replay Stage A regression (`test_stage_a_expansion`) to ensure the chi-squared scaling still satisfies the ≥0.2% gate; tee output to `pytest_stage_a.log`.
7. Set `DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/db_at_024` (mkdir first), then execute `pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/pytest_db_at_024.log`, ensuring the metrics JSON/CSV land under the db_at_024 directory.
8. Summarize pass/fail status plus key telemetry deltas in `plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/summary.md` (include Stage A/B/C improvements and the DB-AT-024 correlation/localization numbers).

## Pitfalls To Avoid
- Do not touch simulator/dtorch packages outside the repo (Environment Freeze); any missing imports must be recorded as blockers.
- Stage B/C fixtures depend on `refGeom` assets; skip with rationale instead of deleting assertions if the data are unavailable.
- DB-AT-024 requires `DBAT024_ARTIFACT_DIR` and canonical fixtures; record the skip reason if assets are missing rather than forcing failure.
- Keep `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile caching during long smokes.
- Ensure telemetry assertions read tensors on CPU (convert to Python floats) before comparing; otherwise pytest will report device mismatch errors.
- Do not downgrade the chi-squared gate thresholds—any adjustments must cite REFINE-007/008 and live in the config, not inline in the tests.
- Avoid deleting the legacy `loss_trace_*` asserts; they remain for backward compatibility until TORCH-REFINE-005 completes.
- Always tee logs into the artifacts directory; collectors rely on these filenames for attempts history.
- Keep `DBAT024_ARTIFACT_DIR` unique per run to avoid overwriting prior parity evidence.

## If Blocked
- If Stage B/C smokes cannot collect due to missing refGeom assets, run each selector with `--collect-only`, save the log in the artifacts directory, and record the missing asset list plus skip reason in `docs/fix_plan.md` under PHYSICS-LOSS-001 (status -> blocked) before stopping.
- If DB-AT-024 fixtures (refined.expt, mask, scaled.mtz) are absent, capture the `pytest.skip` output, stash metrics if partially generated, and mark the initiative blocked with the asset list and log path.
- If tests fail because chi-squared telemetry is absent, stop after capturing the failure logs and escalate in `docs/fix_plan.md` + `plans/active/PHYSICS-LOSS-001/reports/.../summary.md` instead of pushing partial fixes.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — Stage B/C must carry the same variance-weighted denominator and emit chi-squared + masked-MSE telemetry (docs/findings.md line 19).
- DIAGNOSTICS-001 — `/torch_diagnostics` schema stability requires additive attrs/datasets; never remove legacy `masked_mse` entries when extending telemetry.
- REFINE-005 — Stage B hinges on halo/interpolation guards; ensure asserts continue to enforce `hkl_metadata["has_halo"]` after telemetry edits.
- REFINE-007 — Stage C detector microslip gates sit around 0.002% improvement; telemetry comparisons must preserve that calibration.
- REFINE-008 — Stage B improvement ceiling is ~1e-8, so tests must keep the relaxed gate and treat chi-squared telemetry as the authoritative metric.

## Pointers
- docs/spec-db-core.md:32-94 — Variance-weighted loss and detached denominator requirements.
- plans/active/PHYSICS-LOSS-001/implementation.md:31-70 — Phase B completion notes + Phase C validation checklist.
- tests/dbex/test_torch_refine_smoke.py:360-750 — Stage A/B/C smoke implementations and acceptance criteria.
- tests/dbex/test_mapping_consistency.py:1-200 — DB-AT-024 selector structure, env requirements, and metrics expectations.
- docs/TESTING_GUIDE.md:1-140 — Canonical pytest invocation flags + artifact policy for Stage smokes and DB-AT selectors.

## Next Up (optional)
1. If the above lands quickly, capture a telemetry excerpt from a real CLI run and update docs/findings.md with Stage B/C chi-squared baselines.
2. Run DB-AT-010 again under GPU to ensure variance-plumbing remains device-neutral before closing the initiative.

## Mapped Tests Guardrail
- Stage B/C smokes and Stage A expansion must collect exactly one test each; run `--collect-only` if fixtures are missing and log the skip.
- DB-AT-024 mapping smoke collects one test when the canonical fixtures exist; if collection drops to 0, capture the skip reason and treat the loop as blocked rather than forging ahead.
