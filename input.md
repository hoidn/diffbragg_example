Summary: Prove Stage B/C warm caching on the canonical detector by asserting perf telemetry and replaying the Stage smokes plus the warm-vs-cold benchmark.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers, tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — add asserts that `telemetry_b.perf_counters` exists, reports `cache_mode="warm"`, `roi_mode="panel"`, ROI counts that match `refinement_inputs.panel_slices`, and non-zero closure/validation counts so perf telemetry breaks if warm cache falls back to cold per panel.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — assert `telemetry_c.perf_counters` carries `cache_mode="warm"`, ROI counts that follow Stage A ROI mode, forward_time stats, and detector-offset metadata so canonical runs prove the warm ROI path is active. Emit these metrics via `_record_stage_telemetry`.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/telemetry_stage_bc_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip} | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/pytest_stage_bc_full.log
- Benchmark: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/

How-To Map:
1. Stage B perf assertions: in tests/dbex/test_torch_refine_smoke.py (~line 819) add a `perf = telemetry_b.perf_counters` guard plus asserts on `cache_mode`, `roi_mode`, `roi_count_total`, `roi_count_sampled`, `closure_evals`, and `forward_time_ms["total"] > 0`. Reuse the canonical ROI count (`len(refinement_inputs.panel_slices)`) for comparisons and include these fields in the `_record_stage_telemetry` payload.
2. Stage C perf assertions: in tests/dbex/test_torch_refine_smoke.py (~line 600) add the analogous `perf = telemetry_c.perf_counters` asserts plus checks that `telemetry_c.roi_mode == "roi"` when Stage A ROI mode is enabled and that detector-offset stats remain ≥80% reduction for full-detector strict gates. Emit the perf counter dict inside `_record_stage_telemetry` so the telemetry JSON mirrors new asserts.
3. Full-detector warm run: execute the provided pytest command with `DBEX_SMOKE_DETECTOR_SIZE=full` and telemetry path pointing to `telemetry_stage_bc_full.json`; verify the JSON shows `cache_mode="warm"`, ROI counts, and monotonic chi-squared traces for both stages before archiving the log/telemetry under the artifacts directory.
4. Warm vs cold benchmark: re-run `benchmark_stage_a_cache.py --modes warm cold` with the same artifact directory to regenerate `benchmark_summary.json`, `benchmark_report.txt`, and `{warm,cold}_perf_counters.json` so the findings ledger can cite the canonical ROI vs panel delta alongside the full-detector Stage smokes.
5. Documentation updates: append the measured perf deltas to `docs/findings.md` (new PERF-WARM entry) and log the evidence paths in `docs/fix_plan.md` once the tests/benchmark pass.

Pitfalls To Avoid:
- Keep `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE`; the Stage smokes use CUDA contexts and will fail or deadlock if those flags drop.
- Do not relax Stage B/C gates; strict tolerances from docs/TESTING_GUIDE.md:31 still apply when running the full detector.
- Ensure perf counter asserts degrade gracefully when `perf_counters` is `None` (e.g., cold mode) by guarding on warm cache flags instead of unconditional indexing.
- Remember Stage C ROI mode only activates when Stage A warm cache is enabled; avoid forcing ROI assertions in cold control paths.
- Leave Stage A ROI sampling code untouched—layered-scope guard prohibits mixing Stage A refactors into this loop.

If Blocked:
- Capture the failing selector output plus the telemetry JSON snippet to plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/blockers.txt, note the error in docs/fix_plan.md Attempts History, and update galph_memory.md with `state=blocked` plus the failing command before switching focus.

Findings Applied (Mandatory):
- PERF-WARM-003 — ROI sampling is required to escape the 1.01× plateau, so asserts must guarantee Stage B/C stay on the warm path.
- PERF-WARM-004 — Simulator instantiation overhead alone was insufficient; perf counters verify we are reusing the warmed context rather than reconstructing per closure.
- PERF-WARM-005 — Cold control paths must render full panels; benchmark rerun confirms the ≥10× ROI vs panel delta captured earlier still holds on the canonical dataset.
- PERF-WARM-006 — Stage C relies on Stage A detector configs and ROI metadata; telemetry asserts need to fail fast if the handoff regresses.

Pointers:
- tests/dbex/test_torch_refine_smoke.py:600 — Stage C smoke harness where the new perf assertions belong.
- tests/dbex/test_torch_refine_smoke.py:819 — Stage B smoke harness that needs the perf counter guard and `_record_stage_telemetry` update.
- docs/TESTING_GUIDE.md:31 — Detector-size policy and strict gates for canonical Stage smokes.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py:1 — Warm vs cold benchmark script used to publish ROI vs panel telemetry.

Next Up (optional): If this loop lands cleanly, explore a follow-on Do Now to add Stage B ROI-aware sampling so perf counters reflect sub-panel batching and we can expand the benchmark script beyond Stage A.
