# Input

- Summary: Recalibrate the strict `--smoke-detector-size=full` Stage B/C gates so canonical detector smokes pass while preserving telemetry evidence for PHYSICS-LOSS-001.
- Mode: Parity
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for smoke tests
- Branch: integration
- Mapped tests:
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/

## Do Now
- Focus Item: PERF-SMOKE-DETSIZE
- Implement: `tests/dbex/test_torch_refine_smoke.py::{test_stage_c_detector_microslip,test_stage_b_shell_modifiers}` — capture canonical-detector telemetry via `DBEX_SMOKE_TELEMETRY_PATH`, convert the strict gates to (a) detector-offset reduction + non-regression chi-squared checks for Stage C and (b) bounded loss deltas + shell-modifier sanity for Stage B, then sync `docs/TESTING_GUIDE.md` Stage-smoke guidance with the new tolerances.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/telemetry_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/pytest_stage_c_full.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/telemetry_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/pytest_stage_b_full.log`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/

## How-To Map
1. Before editing, replay the failing selectors from `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log` to confirm the current chi-squared/percentage deltas, and set `DBEX_SMOKE_TELEMETRY_PATH` so future runs emit JSON payloads for later analysis.
2. Update `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` to compute absolute detector-offset reductions from `telemetry_c.param_deltas` (e.g., require ≥80% reduction toward zero or final |offset| ≤0.05 mm) while also asserting Stage C does not regress (`stage_c_final_chi2 <= stage_a_final_chi2 * 1.0005`). Document these tolerances inline and keep `strict_gates` limited to `smoke_detector_size=="full"`.
3. Revise `test_stage_b_shell_modifiers` so the strict gate enforces `improvement_b >= -1e-6` (no measurable regression) plus “identity shell modifier” checks (each modifier stays within ±1% of 1.0) instead of the stale ≥1e-8 improvement. Capture the actual improvement from telemetry and record it in the initiative artifacts for traceability.
4. Refresh `docs/TESTING_GUIDE.md` Stage-smoke section to explain the canonical-detector calibration procedure (telemetry capture, new offset/modifier tolerances, and required env vars), and mention where artifacts live.
5. Execute the mapped Stage C/B selectors with `DBEX_SMOKE_DETECTOR_SIZE=full` and the telemetry path set; archive the pytest logs plus the emitted telemetry JSON under `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/`, and note the measured metrics in `docs/fix_plan.md` Attempts History if the gates pass.

## Pitfalls To Avoid
- Do not relax the guard to let `--smoke-detector-size=small` satisfy DB-AT workflows; we only touch strict-gate logic while still requiring full-detector runs for parity.
- Keep the detector-offset tolerance grounded in actual telemetry (±0.25 mm injection); avoid hand-wavy numbers without citing logs.
- Preserve Stage C/LBFGS configuration (history size, ROI sampling) so we are calibrating gates, not altering optimizer behavior.
- Ensure Stage B shell-modifier assertions verify telemetry (param_deltas, chi-squared traces) rather than deleting checks, and tolerate only minute negative deltas.
- Capture telemetry only inside the artifacts directory; do not litter repo root or git history with JSON logs.
- Maintain `KMP_DUPLICATE_LIB_OK=TRUE` + `NANOBRAGG_DISABLE_COMPILE=1` per `docs/TESTING_GUIDE.md`; deviating invalidates parity assumptions.
- Be explicit when editing docs: cite Stage C offsets and Stage B improvement numbers so future adjustments have provenance.
- If telemetry shows Stage C offsets fail to shrink, stop and log it — that indicates a simulator bug, not a test-only tweak.

## If Blocked
- If strict-gate telemetry proves Stage C never reduces detector offsets, capture the telemetry JSON + pytest failure, annotate `docs/fix_plan.md` as blocked (Stage C physics issue), and hand it back rather than masking the failure.
- If Stage B modifiers wander outside ±1% even after multiple seeds, archive the failing telemetry and log the deviation in the fix-plan Attempts History; do not further loosen gates without evidence.

## Findings Applied (Mandatory)
- REFINE-007 — Stage C detector microslip gate must reflect measured refGeom ceilings; new offset-based tolerances replace the obsolete 0.002% chi-squared gate while still proving detector motion occurs.
- REFINE-008 — Stage B shell modifiers show ~0 improvement on refGeom; calibrate the regression tolerance (≤1e-6 loss delta) and keep telemetry intact to honor this finding.

## Pointers
- docs/spec-db-workflow.md:33 — Stage Smoke Dataset Policy and canonical-detector requirements for DB-AT selectors.
- docs/TESTING_GUIDE.md:31 — Stage smoke selector doc that needs the new full-detector gating thresholds.
- tests/dbex/test_torch_refine_smoke.py:500 — Stage C microslip smoke harness targeted for recalibration.
- tests/dbex/test_torch_refine_smoke.py:691 — Stage B shell-modifier smoke harness targeted for recalibration.
- plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log:142-369 — Evidence of the failing strict gates on the canonical detector.

## Next Up (optional)
1. Once the canonical Stage B/C smokes pass, unblock PHYSICS-LOSS-001 to resume the shared variance-weighted helper work on the small-detector fixture.

## Mapped Tests Guardrail
- Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full` to confirm the Stage C selector still collects before the full execution.
- Repeat for Stage B: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full`; if either collects zero tests, fix the option plumbing before proceeding.
