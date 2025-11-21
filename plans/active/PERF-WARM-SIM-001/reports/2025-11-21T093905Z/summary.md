### Turn Summary
Framed the Stage A warm-cache gap: the latest benchmark still shows only a 1.01× warm/cold delta because `compute_loss` re-instantiates `nanobrag_torch.Simulator` for every panel despite the warm context (dbex/nanobrag_refinement.py:807-855, plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/benchmark_summary.json).
Updated docs/fix_plan.md and input.md so Ralph adds cached per-panel simulators, retargets them each closure, and captures Stage A smoke + benchmark artifacts under 2025-11-21T093905Z/.
Next: implement the simulator pool, rerun the Stage A smoke plus the warm/cold benchmark, and stash telemetry/profiler notes if the speedup still falls below 1.3×.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/ (input.md, planning notes)
