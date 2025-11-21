Summary: Capture Stage B ROI telemetry for both detector sizes and package it via a reusable summary script so we can update the findings/fix-plan evidence.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers (small + full datasets)
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py::main — add a T2 script that ingests one or more Stage B telemetry JSON files, extracts cache/ROI counters (mode, totals, sampled counts, closure/validation counts, forward_time stats, loss deltas), and emits a consolidated JSON report under this loop’s artifacts so future loops can diff ROI behavior without re-running pytest.
- Implement: docs/findings.md::PERF-WARM-008 — rewrite the entry with the new Stage B ROI telemetry (cite the summary script output + pytest logs) so canonical runs explicitly require `roi_mode="roi"` and ≥92 ROI totals; mention the fresh artifact path.
- Implement: docs/fix_plan.md::[PERF-WARM-SIM-001 Attempts] — append an Attempts History row documenting the dual Stage B smoke reruns, telemetry JSONs, and summary artifact so the ledger reflects the ROI evidence.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/pytest_stage_b_small.log
- Re-test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/pytest_stage_b_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/stage_b_roi_summary.json
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/

How-To Map:
1. Run the small-detector Stage B smoke with the env vars above to capture `pytest_stage_b_small.log` and `telemetry_stage_b_small.json` under the artifact directory.
2. Re-run the same selector with `--smoke-detector-size=full` (and the full telemetry env var) so canonical ROI-mode telemetry/ROI counts land in `telemetry_stage_b_full.json`.
3. Author `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py` (argparse-based CLI, docstring documenting purpose/inputs/outputs) and execute it with both telemetry files so it emits `stage_b_roi_summary.json` summarizing ROI modes, totals, sampled counts, closure/validation counts, forward_time stats, Stage A/B loss deltas, and dataset labels.
4. Use the script’s JSON plus the pytest logs to refresh `docs/findings.md::PERF-WARM-008` and add the new Attempts History bullet in `docs/fix_plan.md`.

Pitfalls To Avoid:
- Leave `RefinementConfig.enable_stage_a_roi_mode` untouched; the goal is to document behavior, not flip the knob.
- Keep Stage C smokes/tests out of scope per layered-scope guard; only Stage B evidence changes this loop.
- Ensure telemetry paths are unique per detector size; do not reuse the `121804Z` files.
- Capture the canonical run even if it now passes—ROI counts ≥92 must be visible in the artifacts.
- Don’t skip the summary script; we need reproducible metrics, not ad-hoc notes.
- Remember Environment Freeze: no package installs or pytorch upgrades.
- When editing docs, cite the artifact filenames exactly so ledger readers can replay the evidence.
- Stage B smoke uses GPU (`device="cuda:0"`); if CUDA unavailable, stop and log the block instead of downgrading the test.

If Blocked:
- Save the failing pytest output plus telemetry snippet to `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/blockers.txt`, update docs/fix_plan.md with the error signature, and log the block in galph_memory before pivoting per instructions.

Findings Applied (Mandatory):
- PERF-WARM-005 — Warm vs cold ROI gating requires ROI mode tags in perf counters; ensure both telemetry files show `roi_mode="roi"` and cite them in docs.
- PERF-WARM-006 — Stage B warm reuse must mirror Stage A detector/ROI caches; verifying telemetry for both detector sizes proves the reuse path is stable.
- PERF-WARM-007 — Canonical smokes must keep strict perf counters; capture the full-detector run to show closure_evals/validation counts are non-zero and warm-only.
- PERF-WARM-008 — Tests must key ROI-mode gates off the Stage A config; this loop provides the canonical ROI evidence and updates the finding accordingly.

Pointers:
- dbex/nanobrag_refinement.py:1595 — Stage B ROI-mode branch built atop `StageAContext.roi_entries`.
- tests/dbex/test_torch_refine_smoke.py:930 — Stage B smoke assertions/telemetry helpers that must be satisfied in both runs.
- docs/TESTING_GUIDE.md:31 — Detector-size switch + telemetry policy governing smoke selectors.
- docs/findings.md:20 — PERF-WARM entries describing warm-cache/ROI guardrails that need the refreshed evidence.
- plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/summary.md — Prior loop’s notes describing the ROI-mode failure on canonical runs.

Next Up (optional): If time remains after ROI telemetry lands, consider rerunning Stage C full-detector smoke to ensure its telemetry still matches the updated Stage B ROI evidence.

Doc Sync Plan (Conditional): Not needed—no new selectors or renamed pytest nodes once telemetry is recorded.

Mapped Tests Guardrail: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_b_shell_modifiers` already collects 1 test; reruns inherit that coverage.

Hard Gate: Do not close this focus until both Stage B smokes pass with telemetry JSONs showing `cache_mode="warm"`, `roi_mode="roi"`, and the summary script output archived alongside the pytest logs.

Normative Math/Physics: Stage B chi-squared computations must remain the variance-weighted loss from docs/spec-db-core.md §§57–68; ROI vs panel execution cannot change the formula—only the work-item sampling.
