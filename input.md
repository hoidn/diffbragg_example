Summary: Re-enable Stage C ROI-mode closures while keeping panel validations so the warm-cache LBFGS path matches pre-regression behavior and Stage C can pass REFINE-007 again.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_params (and plumbing) — drop the `and not force_panel_validation` guard so ROI closures follow Stage A telemetry again, keep `validation_scope` forcing panel mode when Stage B/C run, and only set `roi_mode_reason` when ROI closures are actually disabled (warm cache off, Stage A panel mode, or no ROIs). Mirror the change in tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip expectations (the perf-counter block already asserts both `roi_mode` and `validation_scope`; just ensure any helper logic still assumes they can differ).
- Validate: rerun the Stage C detector microslip smoketest for both detector sizes with telemetry capture plus the warm-cache summarizer; REFINE-007 gates must pass (≤0.05% χ² regression, ≥80% offset reduction or ≤0.05 mm absolute).
How-To Map:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=small \
    > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/collect_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override \
  DBEX_SMOKE_DETECTOR_SIZE=small \
  DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/telemetry_stage_c_small.json \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=small \
    | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/pytest_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=full \
    > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/collect_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override \
  DBEX_SMOKE_DETECTOR_SIZE=full \
  DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/telemetry_stage_c_full.json \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=full \
    | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/pytest_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py \
    --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/telemetry_stage_c_small.json \
    --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/telemetry_stage_c_full.json \
    --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/stage_c_warm_cache_report.json
Pitfalls To Avoid:
- Do NOT relax the REFINE-007 χ² gate; we need χ² regression ≤0.05% with ≥80% detector-offset reduction or ≤±0.05 mm absolute.
- Preserve `validation_scope="panel"` when Stage B/C (or `stage_a_force_panel_validation`) is enabled even if ROI closures run; ROI telemetry and validation scope are independent.
- Keep `roi_mode_reason` meaningful: only report why ROI mode is disabled, not that validation scope equals panel.
- Leave warm-cache plumbing untouched (Stage C must still reuse Stage A detectors via `_retarget_stage_a_detectors`).
- Maintain Environment Freeze: no new deps or package installs.
- Capture collect-only logs before each pytest invocation to keep selector health recorded.
- Ensure both telemetry JSON files and summarizer output land under the new artifacts directory.
- If Stage C still regresses, do not tweak tolerance values—capture telemetry and return to supervisor.
If Blocked:
- If χ² regression persists >0.05% after ROI closures are re-enabled, keep the telemetry JSON + summarizer output, note the exact failure signature in docs/fix_plan.md Attempts History, and pause so the supervisor can decide whether to escalate (gate recalibration vs. deeper LBFGS tuning).
Findings Applied (Mandatory):
- REFINE-007 — Canonical Stage C smokes must keep χ² regression ≤0.05% with ≥80% detector-offset reduction; use PERF telemetry to prove the threshold.
- REFINE-010 — Stage C ROI-mode decisions must mirror Stage A’s telemetry, independent of validation scope when warm cache is active.
- REFINE-012 — Validation scope must be forced to panel when Stage B/C run, but closures can still use ROI minibatching; telemetry should surface both fields.
- REFINE-013 — Best snapshot persistence/rehydration already fixed; ensure ROI-mode changes do not regress that flow.
- PERF-WARM-006 — Stage C must reuse warmed Stage A detectors/simulators; do not break `_retarget_stage_a_detectors`.
Pointers:
- docs/spec-db-workflow.md:62 — Stage C optimization vs. validation populations and ROI minibatching guidance.
- docs/TESTING_GUIDE.md:49 — REFINE-007 telemetry gate details and selector expectations.
- docs/findings.md:72 — REFINE-011/012 context for validation scope vs. ROI closures.
- dbex/refinement/stage_c_impl.py:160-320 — ROI-mode logic, perf-counter wiring, and warm-cache plumbing you will modify.
- tests/dbex/test_torch_refine_smoke.py:1188-1230 — Perf-counter assertions for `roi_mode` and `validation_scope`.
Next Up (optional):
- If ROI closures + telemetry fixes still hit the gate, capture chi² traces and consider staging an LBFGS hyperparameter probe (lower tolerance_change) under a new plan entry.
