# Input

- Summary: Cache per-panel `nanobrag_torch.Simulator` instances inside StageAContext so warm mode stops rebuilding ROI/pixel state every closure and re-benchmark warm vs cold to document the improved speedup.
- Mode: Perf
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/

## Do Now
- Focus Item: PERF-WARM-SIM-001
- Implement: `dbex/nanobrag_refinement.py::run_nanobrag_refinement::compute_loss` (and `_build_stage_a_context`) — extend StageAContext to build/cache per-panel `nanobrag_torch.Simulator` objects tied to the detector + beam configs, retarget them to the refreshed `Crystal` once per closure, and remove the warm-mode Simulator instantiation from the panel loop while leaving the `enable_stage_a_warm_cache=False` path untouched for benchmarking.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/

## How-To Map
1. Implement the simulator pool: update `StageAContext` and `_build_stage_a_context` to instantiate a `Simulator` per panel (seeded with the cached detector/beam configs) and store them so `compute_loss` can assign the freshly built warm `Crystal` and reuse their cached ROI masks/pixel coords; add a helper to keep `beam_config`, `hkls`, and `enable_hkl_interpolation` synchronized per spec.
2. Warm-mode verification (guardrail selector, keeps mapped test collecting):
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/pytest_stage_a_small.log`
3. Re-run the warm vs cold benchmark so we can compare to the 1.01× baseline and log `speedup` + perf counters:
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/ | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/benchmark.log`
   Expect to see `speedup >= 1.3×`; if not, capture the JSON/telemetry deltas plus a short profiler note in the summary.
4. Summarize the new timings (`warm/cold` wall clock, closure_evals, forward_time_ms) in `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/summary.md`, and update `docs/fix_plan.md`/`docs/findings.md` only if we still miss the ≥2× exit criterion after caching simulators.

## Pitfalls To Avoid
- Preserve the cold-mode rebuild path exactly as-is; benchmark script depends on it as the control arm.
- Ensure every cached simulator/device stays on the `RefinementConfig.device`/dtype; no `.to()` calls inside the panel loop per `docs/spec-db-runtime.md`.
- When retargeting cached simulators, also refresh `beam_config`/HKL tensors and the tricubic interpolation flag or risk diverging from canonical physics.
- Do not touch Stage B/C code or Stage A gates; this loop is scoped strictly to warm-mode simulator reuse and perf telemetry.
- Keep `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` for all pytest/benchmark runs (per RUNTIME-001); compiled graphs will skew perf counters.
- Maintain the `perf_counters` schema (closure_evals, forward_time_ms, cache_mode) so downstream tooling keeps parsing telemetry.

## If Blocked
- If cached simulators still yield ≤1.1× speedup or trigger traced bugs, archive `benchmark.log`, `benchmark_summary.json`, and the traceback under the artifact directory, then mark PERF-WARM-SIM-001 as `blocked` in docs/fix_plan.md with the failure signature.

## Findings Applied (Mandatory)
- PERF-WARM-001 — Warm cache must reuse detector/HKL tensors and keep perf telemetry stable while trimming closure work.
- PERF-WARM-002 — Spec explicitly calls for hoisting `create_crystal_config`/`Crystal` (and dependent simulator state) out of the panel loop so warm vs cold diverge meaningfully.
- PERF-WARM-003 — Baseline benchmark shows only 1.01×; reuse the same script/assets so the new warm/cold comparison is apples-to-apples.
- RUNTIME-001 — Deterministic LBFGS/perf measurements require `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` in every command listed here.

## Pointers
- dbex/nanobrag_refinement.py:807 — Warm mode still instantiates `Simulator` objects inside the panel loop, causing the 1.01× plateau.
- docs/spec-db-runtime.md:20 — Normative requirement to reuse warmed simulators when detector geometry/oversample stay fixed.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py:1 — Canonical warm vs cold benchmark harness and artifact contract.
- docs/TESTING_GUIDE.md:35 — Stage A smoke env vars, detector-size switch, and telemetry expectations.
- docs/findings.md:16 — PERF-WARM-003 ledger entry documenting the 1.01× warm/cold baseline that we must beat.

## Next Up (optional)
- Once Stage A shows a measurable gain, extend the cached simulator approach to Stage B/C closures so future loops can amortize shell-modifier and detector-microslip runs as well.
