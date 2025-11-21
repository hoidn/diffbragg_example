### Turn Summary
Hoisted Stage A warm caching by pre-building per-panel `nanobrag_torch.Simulator` objects inside `StageAContext`, adding helpers to hydrate/retarget warmed `Crystal` models, and rewiring `compute_loss` so warm mode never instantiates simulators inside the panel loop.
Verified `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` and reran `benchmark_stage_a_cache.py --modes warm cold`; warm=162.78 s vs cold=163.80 s (≈1.01×) with matching closure counts/telemetry captured under the initiative’s report directory.
Next: profile simulator panel loops/ROI mask prep to find the next amortization target so the warm cache can exceed the ≥2× goal before extending the pattern to Stage B/C.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/ (pytest_stage_a_small.log, telemetries, benchmark_summary.json, warm/cold_perf_counters.json)

### Turn Summary
Framed the Stage A warm-cache gap: the latest benchmark still shows only a 1.01× warm/cold delta because `compute_loss` re-instantiates `nanobrag_torch.Simulator` for every panel despite the warm context (dbex/nanobrag_refinement.py:807-855, plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/benchmark_summary.json).
Updated docs/fix_plan.md and input.md so Ralph adds cached per-panel simulators, retargets them each closure, and captures Stage A smoke + benchmark artifacts under 2025-11-21T093905Z/.
Next: implement the simulator pool, rerun the Stage A smoke plus the warm/cold benchmark, and stash telemetry/profiler notes if the speedup still falls below 1.3×.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/ (input.md, planning notes)
