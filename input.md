Summary: Ensure Stage B smokes always emit telemetry (even on failure) so we can inspect chi-squared traces from the canonical detector run.
Mode: none
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full (expected fail while capturing telemetry)
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — wrap the body in a try/finally (or move `_record_stage_telemetry`/summary prints ahead of the REFINE-008 asserts) so Stage B telemetry is written before the ±1% gate fires, ensuring canonical runs still append `telemetry_stage_b_full.json`; keep ROI/cache perf-counter asserts intact and document the PERF-WARM-009/010 rationale inline.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/pytest_stage_b_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/pytest_stage_b_full.log || true  # failure expected once shell_0 hits clamp; telemetry must still be emitted
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/stage_b_roi_summary.json
- Artifacts: Copy both pytest logs, telemetry JSON files, and `stage_b_roi_summary.json` into plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/ for this loop.

How-To Map:
1. Edit tests/dbex/test_torch_refine_smoke.py around the Stage B smoke so `_record_stage_telemetry` (and the diagnostic prints) live inside a finally block that always runs, even when strict asserts fail or Stage B throws; keep telemetry payload identical so downstream scripts continue to parse it.
2. Re-run the small-detector Stage B smoke with the env vars above; the test should pass and append telemetry/log files beneath the new artifacts directory.
3. Re-run the full-detector Stage B smoke with the same env except `DBEX_SMOKE_DETECTOR_SIZE=full` and `--smoke-detector-size=full`; expect the ±1% assert to fail, so pipe output to the artifact log and allow the command to continue via `|| true` after confirming telemetry_stage_b_full.json was written.
4. Execute summarize_stage_b_roi.py with both telemetry JSON paths so canonical + small datasets appear in `stage_b_roi_summary.json`; cite this file plus pytest logs in docs/fix_plan.md when updating the Attempts History.
5. If telemetry now captures canonical traces, review the JSON locally to note Stage A/B chi-squared deltas for the next loop’s diagnosis; no spec changes until we understand the divergence.

Pitfalls To Avoid:
- Do not move or delete the strict REFINE-008 checks—only ensure telemetry recording happens before they trigger.
- Keep telemetry filenames distinct per dataset so summarize_stage_b_roi.py can join them unambiguously.
- Capture telemetry even when pytest exits non-zero; the canonical run must leave a JSON behind or the loop is blocked.
- Leave ROI/perf-counter asserts untouched so we keep coverage for PERF-WARM-005/007.
- Do not weaken the ±1% tolerance or stage_b_min_loss_improvement just to make the full run pass.
- Keep `AUTHORITATIVE_CMDS_DOC` exported exactly as written.

If Blocked:
- If full-detector telemetry still fails to write, save the pytest log plus any partial JSON/tracebacks to plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/blockers.txt, note whether the finally block ran, and update docs/fix_plan.md + galph_memory.md with the failure signature so we can re-plan before attempting code changes again.

Findings Applied (Mandatory):
- PERF-WARM-005 — ROI telemetry must still reflect warm-cache mode; ensure new logging doesn’t regress ROI/panel labeling.
- PERF-WARM-007 — Stage B perf-counter asserts stay in place so warm-cache regressions fail fast.
- PERF-WARM-009 — Canonical validations must stay panel-scope; this change is only about telemetry ordering.
- PERF-WARM-010 — Canonical runs keep `enable_stage_a_roi_mode=False`; the new telemetry capture should prove the gate’s behavior.

Pointers:
- docs/fix_plan.md:149 — Latest PERF-WARM-SIM-001 attempt describing this telemetry gap.
- docs/TESTING_GUIDE.md:40-50 — Stage B strict gate expectations and telemetry workflow.
- docs/findings.md:18-23 — PERF-WARM series guardrails for ROI/panel behavior.
- tests/dbex/test_torch_refine_smoke.py:900 — Stage B smoke implementation to edit.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py:1 — Script that consolidates telemetry into stage_b_roi_summary.json.

Next Up (optional): Investigate Stage B shell binning vs Stage A loss traces once canonical telemetry exists, and scope a fix if shell_0 still clamps at 2×.

Doc Sync Plan: none — selectors unchanged (only telemetry ordering inside the existing test).

Mapped Tests Guardrail: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_b_shell_modifiers` collects one node; both detector-size variants reuse this selector, so collection already verified.

Hard Gate: Do not call the loop done until telemetry_stage_b_full.json exists under the new artifacts dir and stage_b_roi_summary.json includes both the small and canonical dataset summaries.

Normative Math/Physics: Stage B still optimizes the variance-weighted chi-squared defined in docs/spec-db-core.md:32-68; the telemetry change must not bypass that contract.
