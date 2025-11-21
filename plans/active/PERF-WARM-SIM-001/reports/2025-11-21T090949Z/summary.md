### Turn Summary
Warm vs cold Stage A benchmarks are still 1.00× (133.18 s vs 133.15 s) because `compute_loss` keeps rebuilding `create_crystal_config`/`Crystal` per panel despite StageAContext, so the perf exit criterion can’t advance.
Prepared a ready-for-implementation Do Now to thread StageAContext through the Stage A closure, hoist the crystal/Simulator instantiation outside the panel loop, and preserve the cold rebuild mode for benchmarking evidence.
Next: Ralph lands the refactor, reruns `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, and executes the warm/cold benchmark script to capture the improved perf counters.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/ (Do Now + benchmark instructions)
