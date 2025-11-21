<<<<<<< HEAD
# Input

- Summary: Begin standardizing the visual diagnostics stack (`dbex.vis`) so smoke/parity runs share a common triptych/Z-score implementation.
- Mode: TDD
- Focus: TOOLING-VIS-001 — Standardize visual diagnostics library
- Branch: integration
- Mapped tests:
  * tests/dbex/test_vis_triptych_smoke.py::test_plot_triptych_smoke
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-21T180000Z/

## Do Now
- Focus Item: TOOLING-VIS-001
- Implement: `dbex/vis/__init__.py, dbex/vis/triptych.py::plot_triptych` — scaffold the `dbex.vis` package and a minimal `plot_triptych(data_roi, model_roi, residual_roi, out_path)` helper that renders a 3-panel triptych (Data | Model | Residual) using `(slow, fast)` indexing and saves a PNG; align layout with `docs/spec-db-vis.md` triptych clauses.
- Implement: `tests/dbex/test_vis_triptych_smoke.py::test_plot_triptych_smoke` — add a small smoke test that builds synthetic `[panel, slow, fast]` arrays, calls `plot_triptych` on a single ROI, and asserts the output PNG exists and has non-zero size.
- Test: `pytest -vv tests/dbex/test_vis_triptych_smoke.py::test_plot_triptych_smoke`

## How-To Map
1. Create the `dbex/vis/` package and an initial `triptych.py` module with a `plot_triptych(data_roi, model_roi, residual_roi, filename)` function that follows the triptych ordering and colormap guidance from `docs/spec-db-vis.md` (Data/Model in grayscale, Residual in diverging colormap).
2. In `tests/dbex/test_vis_triptych_smoke.py`, write a smoke test that constructs small synthetic `data`, `model`, and `residual` arrays (e.g., 1×16×16), calls `plot_triptych` to write to a temporary path, and asserts the file exists and is larger than a minimal byte threshold.
3. Run the mapped pytest node, capture logs under the Artifacts directory, and update `docs/fix_plan.md` Attempts History for TOOLING-VIS-001 with the artifact path and a brief summary of the new helper + test.

Pitfalls To Avoid:
- Do not introduce new plotting dependencies; reuse the existing matplotlib stack only.
- Keep the API surface minimal (one helper function) until later phases; avoid prematurely wiring `dbex.look` or the CLI.
- Ensure all plotting uses `(slow, fast)` ordering and does not transpose arrays implicitly.

If Blocked:
- If imports fail (e.g., missing matplotlib) or tests cannot run, record the minimal error signature in `docs/fix_plan.md` and treat TOOLING-VIS-001 as blocked rather than adding new dependencies.

Findings Applied (Mandatory):
- TOOLING-VIS-001 — Visual diagnostics should share a single triptych implementation and respect Spec DB visualization standards.

Pointers:
- docs/fix_plan.md — TOOLING-VIS-001 ledger row.
- plans/active/TOOLING-VIS-001/implementation.md — full visualization plan.
- docs/spec-db-vis.md — normative triptych/Z-score spec.

Next Up (optional):
- Once the basic triptych helper and smoke test land, extend `dbex/look.py` to call `dbex.vis.plot_triptych` for a single ROI page and add a CLI flag to write a static PNG report.

=======
Summary: Capture Stage C warm-cache telemetry evidence (logs + summary script) so PERF-WARM-SIM-001 can satisfy the Stage B/C perf-counter exit criterion.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — add a Stage C perf-counter print block (cache_mode, roi_mode, ROI totals, closure/validation counts, forward_time_ms.total) mirroring the Stage B logging so pytest output shows the same warm-cache proof while keeping the existing asserts/REFINE-007 gates intact.
- Implement: plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py::main — clone the Stage B summarizer, target `stage_c_detector_microslip` entries, and emit dataset-tagged ROI/perf/loss/offset metrics into `stage_c_roi_summary.json` for both telemetry files.
- Implement: docs/TESTING_GUIDE.md::§1.1 Stage smoke telemetry logging — extend the Stage B/C workflow description to include the Stage C telemetry env vars + summarizer CLI so future operators can rerun this proof verbatim.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/pytest_stage_c_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/pytest_stage_c_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/telemetry_stage_c_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/telemetry_stage_c_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/stage_c_roi_summary.json | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/summarize_stage_c_roi.log

How-To Map:
1. In tests/dbex/test_torch_refine_smoke.py, copy the Stage B perf-counter logging pattern (cache_mode/roi_mode/forward_time totals) into test_stage_c_detector_microslip right after the existing perf-counter asserts so the log lines show the exact counters that are already validated.
2. Use plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py as the template for summarize_stage_c_roi.py: parse telemetry lists, pick the `stage_c_detector_microslip` payload, and emit dataset+perf metrics (loss deltas, chi-squared deltas, detector_offset reductions) into summaries[].
3. Re-run the Stage C smoke twice (small detector ROI mode, then canonical full detector with panel validations) with DBEX_SMOKE_TELEMETRY_PATH pointing at the artifact root; pipe pytest output to logs inside the same directory.
4. Execute the new summarizer against both telemetry files so stage_c_roi_summary.json captures ROI counts, cache/ROI modes, closure counts, forward_time_ms stats, and detector_offset reductions for each dataset.
5. Update docs/TESTING_GUIDE.md §1.1–1.2 so it explains the Stage C telemetry workflow, env vars, warm-cache expectations, and where summarize_stage_c_roi.py lives; cross-link PERF-WARM-SIM-001 artifacts so future loops can reproduce the evidence.

Pitfalls To Avoid:
- Do not relax REFINE-007 gates; only add logging and summarization around the existing assertions.
- Keep telemetry paths unique per detector size so JSON payloads never overwrite each other.
- Reuse the warmed Stage A ROI metadata; Stage C ROI totals must match 29 (small) and 92 (full) or the run is invalid.
- Leave the Stage B ROI/panel toggles untouched—this loop is Stage C only.
- Summaries must treat telemetry JSON as a list and filter by `stage` field; fail fast when Stage C entries are missing.
- Preserve Environment Freeze: no pip/conda/system package changes even if deps look tempting.
- Capture pytest and summarizer logs under the artifact directory so fix_plan/docs updates can cite them directly.

If Blocked:
- If either Stage C pytest run fails (OOM, NaN, missing telemetry) or the summarizer cannot find Stage C entries, stop immediately, save the failing log/JSON under the artifact path, and update docs/fix_plan.md plus galph_memory.md with the failure signature and why PERF-WARM-SIM-001 exit criterion #2 remains open.

Findings Applied (Mandatory):
- PERF-WARM-005 (docs/findings.md:18) — ROI perf counters must reflect the actual dataset slices; log + summarize the Stage C ROI totals and sampled counts for both detector sizes.
- PERF-WARM-006 (docs/findings.md:19) — Stage C must reuse Stage A caches and report `cache_mode="warm"`; the new printout and summary should prove this before documenting success.
- REFINE-007 (docs/findings.md:55) — Canonical Stage C runs need ≥80% detector-offset reduction and ≤0.05% χ² regression; keep the asserts and highlight these metrics in the summary JSON/logs.

Pointers:
- docs/fix_plan.md:37 — PERF-WARM-SIM-001 ledger, exit criteria, and attempts history that must stay in sync with artifacts.
- tests/dbex/test_torch_refine_smoke.py:583 — Stage C smoke function to extend with the perf-counter log block.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py:1 — Script template for the Stage C summarizer (match CLI + JSON format).
- docs/TESTING_GUIDE.md:31 — Stage smoke environment/telemetry guidance that needs the Stage C doc refresh.
- docs/findings.md:18 — Warm-cache ROI expectations that the new evidence relies on.

Next Up (optional): If time remains after Stage C telemetry passes, revisit PERF-WARM-008/010 to scope how canonical Stage B can re-enter ROI mode without breaking REFINE-008.

Doc Sync Plan (Conditional): No new selectors or renames; once Stage C telemetry artifacts exist, just update docs/TESTING_GUIDE.md with the workflow references (no extra collect-only run needed).

Mapped Tests Guardrail: Both Stage C selectors already collect; if `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_c_detector_microslip` ever returns zero nodes, add/restore the fixture before touching production code.

Hard Gate: Do not call the loop done until stage_c_roi_summary.json shows both detector sizes with `cache_mode="warm"`, the expected ROI totals (29/92), non-zero closure/validation counts, and detector_offset reductions ≥0.8 (or ≤0.05 mm) alongside passing pytest logs.

Normative Math/Physics: Telemetry and docs must still cite the Stage C loss definition from docs/spec-db-core.md §§32-68; avoid paraphrasing the equations—refer to the spec text directly when describing chi-squared improvements.
>>>>>>> c23792e (SUPERVISOR AUTO: doc/meta hygiene — tests: not run)
