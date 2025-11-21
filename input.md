Summary: Keep canonical Stage B smokes panel-scope so shell modifiers return to the ±1% REFINE-008 tolerance while small-detector runs continue using ROI mode.
Mode: none
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — when `smoke_detector_size="full"`, set `config.enable_stage_a_roi_mode=False` (and document why) so Stage B canonical runs execute panel-mode closures/validations and the telemetry/perf-counter expectations revert to `roi_mode="panel"`; keep ROI mode enabled for the small-detector default and ensure the asserts still read `telemetry_b.param_deltas` before the ±1% gate fires.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/pytest_stage_b_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/pytest_stage_b_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/stage_b_roi_summary.json
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/

How-To Map:
1. Update `test_stage_b_shell_modifiers` so `config.enable_stage_a_roi_mode` (and any related assertions) depend on `smoke_detector_size`, i.e., panel mode for `full`, ROI for `small`; mention PERF-WARM-010 inline so future changes keep canonical runs panel-scoped.
2. Adjust the perf-counter assertions so canonical runs now expect `telemetry_b.perf_counters['roi_mode']=='panel'` while small runs keep the ROI expectation; ensure the telemetry writer continues to flush `param_deltas` before the gate.
3. No changes to `run_nanobrag_refinement` are required this loop—only the test harness toggles the ROI knob per dataset; keep Stage B logic untouched aside from the test config so downstream initiatives can revisit ROI coverage later.
4. After the code change, rerun the Stage B smoke twice (small + full) with the env vars above, capturing logs/telemetry in the artifacts directory.
5. Run `summarize_stage_b_roi.py` so both telemetry files collapse into `stage_b_roi_summary.json` for evidence; cite the JSON + pytest logs when updating docs/fix_plan.md and docs/findings.md if additional notes are needed.

Pitfalls To Avoid:
- Do not weaken the ±1% or ≤1e-6 chi-squared gates; the fix must restore the original tolerance.
- Keep ROI perf counters intact for small-detector runs—only the canonical path should report `roi_mode="panel"`.
- Avoid touching Stage C or other selectors in this loop; scope stays on Stage B smoke wiring.
- Preserve Environment Freeze: no package/toolchain installs or CUDA changes.
- Capture telemetry even on failure; `_record_stage_telemetry` should never be skipped.
- Ensure `DBEX_SMOKE_TELEMETRY_PATH` points at the artifacts directory before running pytest.
- When editing tests, keep metadata-sigma markers untouched so optional fixtures still work.
- Use warmed StageAContext simulators for panel runs; do not fall back to cold detector rebuilds.
- Keep ROI summary CLI usage (arg order, JSON schema) unchanged so downstream scripts keep working.
- Don't delete prior artifacts under `2025-11-21T133127Z/`—append new logs.

If Blocked:
- Save the failing pytest output + any telemetry JSON to `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/blockers.txt`, note whether the new ROI toggle misbehaved, update docs/fix_plan.md Attempts History, and ping Galph via galph_memory.md before trying alternative fixes.

Findings Applied (Mandatory):
- PERF-WARM-005 — ROI telemetry must still reflect the warm-cache contract; only canonical runs may switch to panel mode.
- PERF-WARM-006 — Stage B must continue reusing StageAContext detectors/simulators; the change should not rebuild detectors mid-closure.
- PERF-WARM-007 — Perf counters have to remain asserted in tests; rerun selectors as documented in docs/TESTING_GUIDE.md §2.
- PERF-WARM-008 — Canonical Stage B smokes enforce ±1% shell modifiers; new telemetry must prove the guard again.
- PERF-WARM-009 — Panel validations are mandatory for canonical evidence; cite the new artifacts when updating the ledger.
- PERF-WARM-010 — Canonical runs shall disable Stage A ROI mode until the strict gate is recalibrated; document any code guard accordingly.

Pointers:
- docs/spec-db-workflow.md:39 — Stage B/Stage Smoke policy for canonical vs small datasets.
- docs/TESTING_GUIDE.md:48 — Canonical Stage B smoke selector and gate definitions.
- docs/findings.md:16-22 — PERF-WARM-005…010 guardrails.
- dbex/nanobrag_refinement.py:1595-1910 — Stage B ROI/validation logic for reference.
- tests/dbex/test_torch_refine_smoke.py:876-1140 — Stage B smoke implementation + assertions to update.
- plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/stage_b_full_probe.json — Evidence showing ROI mode breaks REFINE-008.

Next Up: If time remains after the Stage B fix, rerun the canonical Stage C smoke to confirm detector-offset telemetry still matches the panel-only expectations.

Doc Sync Plan: none — no new selectors or renamed tests.

Mapped Tests Guardrail: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_b_shell_modifiers` collects 1 node; both detector-size variants reuse this selector with different fixture args.

Hard Gate: Do not mark the initiative done until both telemetry files and `stage_b_roi_summary.json` report shell modifiers within ±1% and the canonical pytest run passes without manual tolerances.

Normative Math/Physics: Stage B continues minimizing the variance-weighted chi-squared defined in docs/spec-db-core.md §§32-68; ensure telemetry `chi_squared_trace_full` matches the panel evaluations.
