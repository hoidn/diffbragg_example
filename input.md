Summary: Restore the Stage C orientation tensor handoff so the warm-cache baseline matches Stage A final telemetry, then rerun both Stage C smoketests to revalidate REFINE-007.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/
Do Now:
- Implement: dbex/refinement/stage_c.py::StageC.run — build the frozen Stage C orientation tensor from `stage_a_telemetry['param_deltas']['orientation_vec']['final']` (torch tensor on the config device/dtype), keep it in the frozen `params` list, and pass it through `param_values['orientation_vec']` instead of the post-tanh `misset_xyz_deg`. Continue feeding `misset_deg_for_crystal` from the existing Euler delta so telemetry stays unchanged, but drop the `misset_xyz_deg` alias so `_build_stage_c_lbfgs_closure` reproduces Stage A’s quaternion exactly.
- Validate: rerun the Stage C detector microslip smoketests for both detector sizes with telemetry capture and `summarize_stage_c_warm_cache.py`; REFINE-007 requires ≤0.05% χ² regression with ≥80% detector-offset reduction (or ≤±0.05 mm absolute) in both telemetry files.
How-To Map:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=small \
    > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/collect_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override \
  DBEX_SMOKE_DETECTOR_SIZE=small \
  DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/telemetry_stage_c_small.json \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=small \
    | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/pytest_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=full \
    > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/collect_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override \
  DBEX_SMOKE_DETECTOR_SIZE=full \
  DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/telemetry_stage_c_full.json \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    --smoke-detector-size=full \
    | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/pytest_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py \
    --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/telemetry_stage_c_small.json \
    --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/telemetry_stage_c_full.json \
    --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/stage_c_warm_cache_report.json
Pitfalls To Avoid:
- Keep the orientation tensor on `config.device`/dtype and include it in the frozen `params` list so LBFGS cannot mutate Stage A state.
- Do not repurpose `misset_xyz_deg` for the LBFGS orientation input; it still needs to feed `misset_deg_for_crystal` telemetry.
- Preserve `validation_scope="panel"` when Stage B/C are enabled even if ROI closures are active—ROI telemetry and validation scope are independent.
- Leave warm-cache plumbing untouched (`_retarget_stage_a_detectors` must still operate on tensors to satisfy GRADIENT-004/REFINE-013).
- Capture collect-only logs before each pytest run and tee the test output; missing selector evidence blocks the ledger.
- No environment or tolerance tweaks—if chi² still regresses, capture telemetry and stop.
- Ensure every telemetry JSON and the summarizer output lands under the new artifacts directory.
If Blocked:
- If χ² regression remains >0.05% after the orientation fix, keep both telemetry JSONs plus the summarizer report, log the failure signature in docs/fix_plan.md Attempts History, and pause so the supervisor can decide whether to escalate toward LBFGS hyperparameter work.
Findings Applied (Mandatory):
- REFINE-007 — Stage C must prove ≤0.05% χ² regression alongside ≥80% detector-offset reduction; use the smoketest telemetry to document compliance.
- REFINE-010 — Stage A auto-panel enforcement remains the source of truth for ROI vs panel scope; mirror its telemetry rather than CLI flags.
- REFINE-011 — Full validations stay in panel mode whenever Stage A forced panel scope; keep the bypass guard intact while patching orientation.
- REFINE-012 — Warm-cache ROI closures may stay active, but telemetry must still emit accurate `roi_mode`/`validation_scope` provenance.
- REFINE-013 — Best-snapshot persistence/rehydration already landed; do not regress the telemetry writing order while touching Stage C inputs.
- REFINE-014 — Stage C orientation tensors must come from `param_deltas['orientation_vec']['final']` so panel-mode baselines match Stage A telemetry before enforcing REFINE-007.
Pointers:
- docs/spec-db-workflow.md:62 — Stage C spec for detector offsets and validation cadence the smoketests enforce.
- docs/TESTING_GUIDE.md:48 — Canonical Stage C smoketest commands, env knobs, and telemetry policy.
- docs/fix_plan.md:1204 — Blocked status for PERF-WARM-SIM-001 and the new orientation restoration plan.
- dbex/refinement/stage_c.py:170-355 — Stage A telemetry reconstruction feeding Stage C’s `orientation_vec` and `misset_deg_for_crystal`.
- plans/active/PERF-WARM-SIM-001/reports/2025-12-01T200900Z/telemetry_stage_c_full.json — Evidence of the repeat +0.067% χ² regression despite 99.99999% offset reduction.
Next Up (optional):
- If smoketests pass quickly, diff the new telemetry JSONs against the 2025-11-23 pass artifacts to confirm Stage C traces match Stage A again before closing Phase D.4.
