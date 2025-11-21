Summary: Capture Stage C small/full warm-cache telemetry and document the workflow so PERF-WARM-SIM-001 exit criteria cover Stage C as well as Stage B.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — mirror the Stage B log block by printing/asserting Stage C `cache_mode`, `roi_mode`, ROI totals, closure/validation counts, and `forward_time_ms.total` so telemetry evidence is visible in pytest output.
- Implement: plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py::main — author a T2 script (Stage C twin to `summarize_stage_b_roi.py`) that ingests one or more Stage C telemetry JSON files and emits ROI/perf/loss summaries for archival.
- Implement: docs/TESTING_GUIDE.md::Stage smoke telemetry logging — extend §1.1/§1.2 guidance to describe Stage C telemetry capture + the new summarizer so the warm-cache workflow is reproducible.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/pytest_stage_c_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/pytest_stage_c_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/telemetry_stage_c_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/telemetry_stage_c_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/stage_c_roi_summary.json | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/summarize_stage_c_roi.log

How-To Map:
1. Update Stage C smoke test logging (tests/dbex/test_torch_refine_smoke.py) to print/assert the Stage C perf counters that prove warm cache reuse (`cache_mode`, `roi_mode`, ROI totals, closure/validation counts, forward_time stats); keep canonical gates (≥80% offset reduction, ≤0.05% chi-squared regression) unchanged.
2. Clone `summarize_stage_b_roi.py` into `summarize_stage_c_roi.py`, switch the parser to look for `stage_c_detector_microslip`, and emit Stage C-specific fields (detector_offset_reduction stats, ROI counts, perf counters, chi-squared deltas).
3. Run Stage C smokes for the small detector (ROI mode) then canonical full detector (panel validations) with the env vars above so `telemetry_stage_c_small/full.json` and pytest logs land in the new artifact directory.
4. Execute the summarizer once both telemetry files exist; the JSON (`stage_c_roi_summary.json`) plus the script log should live under the same artifact path for fix-plan/finding updates.
5. Refresh docs/TESTING_GUIDE.md §1.1–1.2 so it cites the Stage C telemetry workflow (env vars, script) and cross-links PERF-WARM-SIM-001; call out the ≥80% offset gate and the expectation that both dataset sizes report `cache_mode="warm"`.

Pitfalls To Avoid:
- Do not re-enable canonical Stage C ROI sampling if it jeopardizes the ≥80% detector-offset gate—keep the existing perturbation/gate values intact.
- Set a unique `DBEX_SMOKE_TELEMETRY_PATH` per run; reusing the Stage B filenames will scramble archived evidence.
- The summarizer must treat telemetry JSON as a list of stage payloads (the tests append), not a single dict; reject missing Stage C entries loudly.
- Keep environment freeze: no pip/conda actions; missing import is a blocker recorded in docs/fix_plan.md.
- Preserve Stage B ROI panel behavior and CPU fallback; Stage C edits must not regress the freshly-warm Stage B path.
- Avoid canonical ROI counts drifting (expect 29 ROIs for `refGeom_small`, 92 for full). Fail fast if telemetry reports different values.
- Canonical runs still consume GPU VRAM; monitor OOM risk and capture telemetry/logs immediately if failures appear.

If Blocked:
- If Stage C pytest fails (NaN/Inf, OOM, missing telemetry) or the summarizer cannot find Stage C entries, stop, save the pytest log + partial telemetry in the artifact directory, and update docs/fix_plan.md + galph_memory.md with the error signature and why the exit criterion remains open.

Findings Applied (Mandatory):
- PERF-WARM-005 — Warm ROI mode must advertise accurate `roi_mode`/counts; verify Stage C telemetry matches dataset slices before accepting the run.
- PERF-WARM-006 — Stage C must reuse Stage A caches and record `cache_mode="warm"`; the new logs/scripts explicitly prove this for both detector sizes.
- REFINE-007 — Canonical Stage C must still hit ≥80% detector-offset reduction and ≤0.05% chi-squared regression; treat any deviation as a regression and gate completion on meeting this evidence.

Pointers:
- docs/fix_plan.md:37 — PERF-WARM-SIM-001 ledger + latest attempt history.
- docs/TESTING_GUIDE.md:31-50 — Canonical Stage B/C gate + telemetry instructions the new doc edits must extend.
- docs/findings.md:16-25 — PERF-WARM findings (especially PERF-WARM-005/006/010) describing ROI/cache expectations.
- dbex/nanobrag_refinement.py:2131 — Stage C warm-cache plumbing (`stage_c_cache_mode`, ROI counters) that the new logs/tests must expose.

Next Up (optional): Once Stage C telemetry is archived, reassess Stage B ROI sampling (PERF-WARM-008/010) so canonical runs can re-enter ROI mode without violating REFINE-008.

Doc Sync Plan (Conditional): After Stage C telemetry passes, fold the workflow + script reference into docs/TESTING_GUIDE.md §1.1–1.2 (no new selectors, so no extra collect-only run needed) and note the artifact path inside docs/fix_plan.md.

Mapped Tests Guardrail: Both mapped Stage C selectors already collect (>0) under `--smoke-detector-size={small,full}`; if `pytest --collect-only` suddenly drops to zero due to fixture edits, add a minimal test or restore the fixtures before proceeding.

Hard Gate: Do not close this loop until `stage_c_roi_summary.json` shows both dataset sizes with `cache_mode="warm"`, the expected ROI totals (29 small / 92 full), and the telemetry JSON captures the canonical ≥80% detector-offset reduction; otherwise mark the attempt blocked.

Normative Math/Physics: Stage C still minimizes the variance-weighted chi-squared defined in docs/spec-db-core.md §§32-68, so any telemetry or doc edits must keep the loss expression and REFINE-007 gate untouched—reference the spec rather than paraphrasing.
