Summary: Capture Stage C perf-counter telemetry (logs + summary script) so PERF-WARM-SIM-001 can close the Stage B/C exit criterion.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests:
  * tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
  * tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — add a Stage C perf-counter print block (cache_mode, roi_mode, ROI totals, closure/validation counts, forward_time_ms stats) mirroring the Stage B logging so warm-cache proofs appear directly in pytest output without weakening the existing asserts.
- Implement: plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py::main — clone the Stage B summarizer to target `stage_c_detector_microslip` entries, capturing ROI/perf counters plus detector-offset reductions into `stage_c_roi_summary.json` (one consolidated file for both telemetry JSONs).
- Implement: docs/TESTING_GUIDE.md::§2 Stage smoke telemetry workflow — extend the Stage B/C section so operators know to set `DBEX_SMOKE_TELEMETRY_PATH` for Stage C, run the new summarizer, and archive telemetry/log files alongside pytest logs.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/pytest_stage_c_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/pytest_stage_c_full.log

How-To Map:
1. Extend `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (lines 583-854) with a `print(f"[Stage C] ...")` block that surfaces `cache_mode`, `roi_mode`, `roi_count_total`, `roi_count_sampled`, `closure_evals`, `validation_runs`, and `forward_time_ms.{total,mean}` directly after the existing perf-counter assertions; keep all asserts unchanged.
2. Create `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py` (same header pattern as `summarize_stage_b_roi.py`) that accepts repeated `--telemetry` args, filters for `stage_c_detector_microslip`, and writes `stage_c_roi_summary.json` with ROI/perf counters plus `detector_offset_reduction_min` and `detector_offset_final_abs_max` fields for each dataset.
3. Update `docs/TESTING_GUIDE.md` Stage smoke section (lines 38-150) to note the Stage C telemetry env var, the new summarizer command, and the artifact expectations (telemetry JSONs + `stage_c_roi_summary.json`).
4. Run the Stage C small-detector pytest command above with telemetry env vars set, capture stdout in `pytest_stage_c_small.log`, and ensure `telemetry_stage_c_small.json` is created under the artifacts directory.
5. Repeat for the full-detector selector, capturing `pytest_stage_c_full.log` + `telemetry_stage_c_full.json`; note that canonical runs may take longer because Stage C still executes LBFGS on CUDA.
6. Generate `stage_c_roi_summary.json` via `python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/telemetry_stage_c_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/telemetry_stage_c_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/stage_c_roi_summary.json | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/summarize_stage_c_roi.log` and reference the summary in `docs/fix_plan.md` and findings if it uncovers new lessons.
7. Attach the new telemetry JSONs, pytest logs, and summary artifacts to the loop directory and note them in `docs/fix_plan.md` Attempts History.

Pitfalls To Avoid:
- Do not relax or delete the existing Stage C asserts; the new prints are purely diagnostic.
- Keep `DBEX_SMOKE_TELEMETRY_PATH` unique per run to avoid clobbering the JSON array.
- Reuse the Stage B summarizer patterns; no ad-hoc scripts outside `plans/active/PERF-WARM-SIM-001/bin/`.
- Preserve ROI/perf counter field names exactly (`cache_mode`, `roi_mode`, etc.) so downstream tooling keeps working.
- Canonical runs still expect warm cache + panel mode; do not re-enable ROI mode without revisiting PERF-WARM-010.
- Stay within the frozen environment (no package installs); treat missing imports as blockers.
- Keep device/dtype handling identical to current config (CUDA float32) so perf counters remain comparable.
- When editing docs, link back to the new artifact paths to maintain traceability.
- Capture pytest stdout via `tee` to the artifacts directory for both detector sizes.
- If Stage C OOMs on CUDA, do not flip to CPU without updating PERF-WARM-SIM-001 dependencies first.

If Blocked:
- If either Stage C selector fails (e.g., CUDA OOM or perf-counter mismatch), capture the failing log under the artifacts directory, note the error signature plus telemetry path in `docs/fix_plan.md`, and set PERF-WARM-SIM-001 to `blocked` with the root cause in galph_memory/input so we can decide whether to pursue a CPU fallback or revisit ROI settings.

Findings Applied (Mandatory):
- PERF-WARM-006 — Stage C must report warm-cache perf counters tied to Stage A ROI mode; new logging/summarizer prove these invariants.
- PERF-WARM-007 — Canonical Stage B/C smokes require perf-counter artifacts alongside pytest logs; we extend Stage C telemetry to match this precedent.
- PERF-WARM-010 — Keep canonical runs in panel mode (ROI disabled) so shell-modifier tolerances remain valid while capturing Stage C telemetry.
- PERF-WARM-011 — Document that canonical Stage B/C may rely on CPU fallback; ensure the Stage C instructions preserve current device handling.
- PERF-WARM-012 — Warm cache must persist even during CPU fallbacks; the Stage C perf-counter logging validates cache_mode stays `warm`.
- RUNTIME-001 — Run Stage smokes with `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile interference.
- CONFORMANCE-001 — Use the canonical pytest selectors + `KMP_DUPLICATE_LIB_OK=TRUE` per Spec DB workflow gates.

Pointers:
- docs/fix_plan.md:37 — PERF-WARM-SIM-001 ledger row and exit criteria.
- plans/active/PERF-WARM-SIM-001/implementation.md:1 — Warm simulator plan + scope.
- tests/dbex/test_torch_refine_smoke.py:583 — Stage C detector microslip test needing new perf-counter logging.
- docs/TESTING_GUIDE.md:38 — Stage smoke selector workflow / telemetry requirements.
- docs/development/TEST_SUITE_INDEX.md:11 — Registry entry for Stage A/B/C smoke selectors.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py:1 — Reference implementation for the new Stage C summarizer.

Next Up (optional):
- Once Stage C telemetry artifacts exist, re-run Stage B canonical smokes to confirm the CPU cache clone still reports `cache_mode="warm"` and fold the evidence into docs/fix_plan.md exit-criterion #2.
