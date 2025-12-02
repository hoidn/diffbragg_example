Summary: Re-disable Stage C ROI-mode closures when Stage A forces panel validations so detector refinement uses the same pixel population as the REFINE-007 gate.
Mode: Parity
InitiativeType: perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip (DBEX_SMOKE_DETECTOR_SIZE=small)
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip (DBEX_SMOKE_DETECTOR_SIZE=full)
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/

Do Now:
- FocusItem: PERF-WARM-SIM-001 Phase F — Enforce REFINE-012 gating before re-running Stage C smokes.
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_params — Gate `stage_c_roi_mode_active` on `not force_panel_validation`, set `roi_mode_reason="validation_scope_panel"` when the gate fires, and ensure telemetry/perf counters report the forced panel mode so closures and validations both call `_compute_panel_loss` when Stage A telemetry advertises `validation_scope="panel"`.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — Update the ROI-mode expectations so Stage C mirrors Stage A’s ROI mode only when panel validation was not forced; otherwise the expected ROI mode should be `"panel"` while the validation scope stays `"panel"` per REFINE-011.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/pytest_stage_c_small.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/pytest_stage_c_full.log`

How-To Map:
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/pytest_stage_c_small.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T183500Z/pytest_stage_c_full.log`

Pitfalls To Avoid:
- Do not relax the REFINE-007 chi² gate or skip the full-detector smoketest; the goal is to make it pass with panel-mode closures.
- Keep ROI-mode disabled only when Stage A telemetry reports `validation_scope="panel"`; do not hard-disable ROI mode for small-detector runs.
- Preserve trusted-mask gating inside `_compute_variance_weighted_loss`; the fix should not touch Stage A mask semantics.
- Leave the new `DBEX_STAGE_C_CACHE_DEBUG_PATH` instrumentation opt-in; this change should not emit extra files.
- Do not mutate Stage A telemetry or ROI sampling thresholds while wiring the gate; only Stage C logic/tests should change.
- Keep `roi_mode_reason` populated so telemetry consumers can see why ROI mode was disabled.
- Do not drop the warm-cache semantics in `_retarget_stage_a_detectors`; the retargeted simulators must still flow through Stage A/C parity logic.

If Blocked: Capture the updated telemetry JSON and failing pytest logs under the artifacts directory, note whether Stage A telemetry ever reports `validation_scope="panel"`, and update docs/fix_plan.md with the evidence before attempting more code changes.

Findings Applied (Mandatory):
- REFINE-011 — Stage C validations must mirror Stage A panel gating; keep `validation_scope="panel"` whenever Stage B/C are active.
- REFINE-012 — ROI-mode closures are prohibited when Stage A validation scope is panel; gate ROI activation accordingly.
- REFINE-016 — Trusted-mask parity is mandatory; ensure the panel-mode helper path stays untouched.
- PERF-WARM-013 — Warm-cache retargeting must remain in place; this fix only toggles closure selection.

Pointers:
- plans/active/PERF-WARM-SIM-001/implementation.md#phase-f — initiative checklist for Phase F.
- dbex/refinement/stage_c_impl.py:330-420 — Stage C parameter builder with ROI-mode gating and telemetry fields.
- tests/dbex/test_torch_refine_smoke.py:1280-1345 — Stage C perf counter assertions that must be updated for the new gating rule.
- docs/findings.md#REFINE-012 — canonical requirement for disabling ROI mode when panel validations are forced.

Next Up (optional): After ROI gating lands and the Stage C full smoketest passes, revisit the cache-debug JSON to confirm panel-mode runs no longer need ROI traces.
