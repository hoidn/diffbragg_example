Summary: Route canonical Stage B smokes through the existing stage_b_full_eval_on_cpu fallback so the full detector runs on CPU without OOM and still records telemetry for ROI/perf analysis.
Mode: none
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — honor `stage_b_full_eval_on_cpu` by routing Stage B panel-mode closures/validations (canonical runs with ROI disabled) to CPU, resetting `stage_b_use_warm_cache`/perf counters accordingly while keeping ROI-mode small smokes on the warmed CUDA path.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — keep ROI/perf assertions for the small smoke but accept `cache_mode="cold"` + panel ROI counts when the CPU fallback is active on the canonical detector.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/pytest_stage_b_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/pytest_stage_b_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/stage_b_roi_summary.json

How-To Map:
1. Update Stage B CPU fallback in `dbex/nanobrag_refinement.py`: detect when `config.stage_b_full_eval_on_cpu` is True, device is CUDA, and ROI mode is disabled, then evaluate Stage B on CPU (use the existing cold path) while forcing `stage_b_use_warm_cache=False` so perf counters report `cache_mode="cold"`; keep ROI-mode small runs untouched so they still use warmed CUDA simulators.
2. Adjust `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` so cache-mode/ROI assertions expect `cache_mode="warm"` for the small detector and `cache_mode="cold"`, `roi_mode="panel"` for the canonical CPU fallback, while leaving the strict chi-squared/modifier gates intact.
3. Rerun the small-detector Stage B smoke with the env vars above; verify it passes, emits telemetry_stage_b_small.json, and keeps `cache_mode="warm"`, `roi_mode="roi"`.
4. Rerun the full-detector Stage B smoke (expected to pass with the CPU fallback) and confirm telemetry_stage_b_full.json now reports `status in {ok,early_stop}` instead of `error`; capture the pytest log even if asserts fail and leave the command non-fatal only if a different bug appears.
5. Run `summarize_stage_b_roi.py` with both telemetry files so stage_b_roi_summary.json includes small + canonical entries; cite these artifacts in docs/fix_plan.md + docs/findings.md once the OOM path is eliminated.

Pitfalls To Avoid:
- Do not relax the ±1% REFINE-008 gates or Stage B loss tolerances; only reroute execution devices.
- Keep small-smoke ROI telemetry identical (cache_mode warm, roi counts intact); only canonical panel runs should flip to CPU.
- Ensure `stage_b_use_warm_cache` and perf counters reflect the actual execution path, otherwise tests will still gate on stale values.
- Leave Stage C and Stage A code untouched; this loop targets Stage B only.
- Capture telemetry/logs even if the full-detector run still fails; missing JSON means the loop is blocked again.
- Respect Environment Freeze—no package installs or CUDA toggles outside the documented env vars.

If Blocked:
- If the canonical smoke still raises CUDA OOM, save the pytest log plus telemetry snippets (or lack thereof) under the artifacts directory, update docs/fix_plan.md with the failure signature, and note the block in galph_memory.md so we can escalate before another code attempt.

Findings Applied (Mandatory):
- PERF-WARM-003/004 — Warm cache changes must preserve determinism; keep ROI sampling tied to the warm CUDA path for small smokes.
- PERF-WARM-005 — ROI telemetry must continue to label roi_mode/roi_counts correctly for both warm and cold paths.
- PERF-WARM-006/007 — Stage B perf counters (`cache_mode`, closure_evals, forward_time_ms) are contractual; update them when CPU fallback activates.
- PERF-WARM-008 — Canonical runs still require panel validations and ±1% shell modifier bounds.
- PERF-WARM-009/010 — Canonical detector stays in panel mode until the strict gate is recalibrated; the fallback must not re-enable ROI sampling there.
- PERF-WARM-011 — GPU OOM on canonical Stage B is now the primary blocker; CPU fallback is the mitigation, not a spec change.

Pointers:
- docs/fix_plan.md:37 — PERF-WARM-SIM-001 ledger entry and latest Do Now description.
- docs/findings.md:16-24 — PERF-WARM guardrails, including the new PERF-WARM-011 OOM finding.
- docs/TESTING_GUIDE.md:38 — Stage B strict gate expectations for canonical smokes.
- dbex/nanobrag_refinement.py:1500 — Stage B refinement block where CPU fallback logic lives.
- tests/dbex/test_torch_refine_smoke.py:876 — Stage B smoke test that asserts telemetry/perf counters.

Next Up (optional): Investigate shell binning once canonical telemetry lands without OOM and the REFINE-008 gate re-fires.

Doc Sync Plan (Conditional): none — selectors unchanged beyond telemetry alignment.

Mapped Tests Guardrail: Both Stage B selectors already exist in the suite and collect under the commands above; rerun them with telemetry logging per How-To map.

Hard Gate: Do not mark this loop done until telemetry_stage_b_full.json (status not "error") and stage_b_roi_summary.json exist under the new artifacts directory.

Normative Math/Physics: Stage B must continue minimizing the variance-weighted chi-squared per docs/spec-db-core.md:57-80; CPU fallback cannot alter the loss expression or sigma provenance.
