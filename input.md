# Input

- Summary: Tag Stage A telemetry with cache-mode metadata and repair the warm/cold benchmark harness so we can capture reproducible speedup evidence.
- Mode: Perf
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Branch: integration
- Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/

## Do Now
- Focus Item: PERF-WARM-SIM-001
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement (emit `perf_counters["cache_mode"]` for Stage A), tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion (assert warm cache telemetry), and plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py::main (prepend repo root to `sys.path` and consume live perf counter keys) so warm/cold benchmarks can attribute telemetry.
- Test: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/

## How-To Map
1. Edit `dbex/nanobrag_refinement.py::run_nanobrag_refinement` to compute `cache_mode = "warm" if config.enable_stage_a_warm_cache else "cold"` and include it in `telemetry_a.perf_counters`; keep the dict schema stable for other counters.
2. Extend `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` so Acceptance 7 verifies `perf_counters["cache_mode"] == "warm"` (string check plus non-empty guard) without weakening existing assertions.
3. Update `plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py`: prepend the repo root to `sys.path` before any `dbex` imports, and rewrite the perf counter extraction so it uses `perf_counters.get("validation_runs", 0)` and the nested `forward_time_ms` dict (`mean`, `total`, etc.) instead of the stale `validations`/`forward_time_ms_total` keys.
4. Re-run the mapped selector with `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/pytest_stage_a.log` to prove telemetry didn’t regress.
5. Execute `python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/` (env: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`) so the JSON/report/per-mode counters land beside the pytest log.
6. Append the measured warm vs cold timings + cache-mode telemetry summary to `docs/findings.md` entry PERF-WARM-001 and note the artifact timestamp.

## Pitfalls To Avoid
- Do not touch `nanobrag_torch` or external packages; Environment Freeze requires source-only fixes.
- Keep Stage A cache toggle default `True` and guard against side effects on Stage B/C flows (device/dtype neutrality per docs/pytorch_runtime_checklist.md:1).
- Preserve deterministic ROI sampling (seed=42) so benchmark telemetry matches existing artifacts.
- Stage A smoke must run with `NANOBRAG_DISABLE_COMPILE=1` and CPU tensors; no CUDA shortcuts per docs/spec-db-runtime.md.
- Ensure the benchmark script only imports the workspace `dbex` (sys.path prepend) to avoid mixing installed wheels.
- When parsing perf counters, tolerate missing keys but never silently swallow schema mismatches—fail loudly if dict shape changes.
- Artifacts must include pytest log plus `benchmark_summary.json`, `benchmark_report.txt`, and `{warm,cold}_perf_counters.json` under the timestamped directory.

## If Blocked
- If the Stage A selector fails before hitting the new assertion, capture the pytest log under the artifacts path, note the stack trace in `plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/summary.md`, and mark the fix-plan Attempts History with the error signature.
- If the benchmark script still resolves the wrong module (e.g., ModuleNotFoundError), log the exact import error, keep the repro command, and stop—treat as environment drift per CLAUDE.md.

## Findings Applied
- PERF-WARM-001 — Warm Stage A cache & perf telemetry: keep cache toggles plumbed through telemetry/scripts and document measured speedups before closing the initiative.

## Pointers
- docs/fix_plan.md:64 — Initiative metadata, exit criteria, and Attempts history for PERF-WARM-SIM-001.
- plans/active/PERF-WARM-SIM-001/implementation.md:1 — Stage A warm-cache design sketch and checklist references (A1/B1/etc.).
- docs/pytorch_runtime_checklist.md:1 — Device/dtype and perf counter guardrails for nanobrag_torch edits.
- docs/TESTING_GUIDE.md:82 — Active implementation selectors + Stage A staging notes for the mapped pytest node.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py:1 — Benchmark harness consuming telemetry and writing perf artifacts.

## Next Up (optional)
1. Instrument Stage B telemetry/perf counters once warm vs cold evidence lands.
2. Add CLI flag plumbing so end users can flip the warm-cache benchmark mode directly from `dbex.refine_one`.

## Mapped Tests Guardrail
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` collects exactly 1 test; if collection breaks, fix/author the selector before delivering code changes.
