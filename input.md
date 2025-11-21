# Input

- Summary: Finish the Stage A warm-cache plumbing so the LBFGS closure stops rebuilding Crystal/Simulator per iteration and capture a new warm vs cold benchmark.
- Mode: Perf
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/

## Do Now
- Focus Item: PERF-WARM-SIM-001
- Implement: `dbex/nanobrag_refinement.py::_build_stage_a_context` and `dbex/nanobrag_refinement.py::run_nanobrag_refinement::compute_loss` — plumb StageAContext through the Stage A closure so warm mode reuses cached detector/HKL/mask tensors, hoists `create_crystal_config` + `Crystal` instantiation out of the per-panel loop, and leaves the cold rebuild mode untouched for benchmarking; update perf counter serialization if structures change.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/

## How-To Map
1. Implement the Stage A warm-cache changes: refactor `compute_loss` to instantiate `crystal_config`/`Crystal` once per call, reuse `stage_a_ctx.hkl_grid`/`trusted_masks_t`, and keep the cold-mode branch rebuilding configs for comparison. Preserve `perf_counters["cache_mode"]` so downstream telemetry remains schema-compatible.
2. Stage A smoke (small detector, CLI sigma) to catch regressions while keeping runtime manageable:  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/pytest_stage_a_small.log`
3. Benchmark warm vs cold with the updated code to prove the perf delta:  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/ | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/benchmark.log`  
   Ensure the script emits `benchmark_summary.json` plus `{warm,cold}_perf_counters.json` inside the artifact directory.
4. Summarize the new warm/cold timings and perf counter deltas in `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/summary.md`, then update docs/fix_plan/findings if the speedup still falls short of the 2–5× target.

## Pitfalls To Avoid
- Leave the cold-mode rebuild path intact; the benchmark relies on it as a control.
- Keep tensor devices/dtypes consistent with `RefinementConfig` (no implicit `.to()` inside loops) per `docs/spec-db-runtime.md`.
- Do not relax Stage A gates or sample fractions; reuse the existing ROI sampler so perf comparisons stay apples-to-apples.
- Continue writing `perf_counters.cache_mode` and timing arrays to telemetry; downstream tooling expects the schema added on 2025-11-06T111515Z.
- Avoid touching Stage B/C code paths in this loop—the Do Now is scoped strictly to Stage A warm reuse and benchmarking.

## If Blocked
- If `nanobrag_torch` raises during the refactor (e.g., due to shared `Crystal` objects), capture the traceback in the artifact directory, revert only the offending hunk, and mark PERF-WARM-SIM-001 as `blocked` in docs/fix_plan.md with the log pointer; do not attempt environment changes.

## Findings Applied (Mandatory)
- PERF-WARM-001 — Stage A warm cache must reuse cached detectors/HKL tensors and log perf counters for cache attribution.
- PERF-WARM-002 — Hoist `create_crystal_config`/`Crystal` out of the per-panel loop so warm mode can diverge from cold mode and deliver a measurable speedup; benchmark artifacts must prove the delta.
- RUNTIME-001 — Keep `NANOBRAGG_DISABLE_COMPILE=1` (and `KMP_DUPLICATE_LIB_OK=TRUE`) set for deterministic autograd + torch LBFGS runs.

## Pointers
- docs/spec-db-runtime.md:20 — Warm simulator reuse requirement when detector shape/oversample stay constant.
- docs/TESTING_GUIDE.md:35-100 — Stage A smoke selector, telemetry logging, and canonical gate references.
- docs/development/TEST_SUITE_INDEX.md:12 — Registry entry + commands for Stage A/B/C smokes.
- dbex/nanobrag_refinement.py:722-910 — StageAContext construction and Stage A `compute_loss` implementation that still rebuilds Crystal/Simulator per panel.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py:1-140 — Warm vs cold benchmark harness and artifact contract.

## Next Up (optional)
- If the speedup lands but Stage A remains the only optimized stage, follow up by threading Stage A context or similar caching through the Stage B/C closures.
