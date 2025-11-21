### Turn Summary
Hoisted the Stage A warm cache so `compute_loss` reuses StageAContext detector/HKL/mask tensors and instantiates `Crystal` once per closure while the cold benchmark still rebuilds per panel for comparisons.
Stage A smoke (`tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`) now runs in warm mode with CLI sigma overrides, logging telemetry to `telemetry_stage_a_small.json` alongside `pytest_stage_a_small.log`.
Warm vs cold benchmarking captured updated perf counters but only moved the wall-clock delta to ≈1.01× (250.77 s vs 252.94 s), so the 2–5× exit criterion remains open.
Next: profile panel-level simulator work and cache ROI/loss-mask prep so warm mode can deliver a measurable >2× gain before touching Stage B/C paths.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/ (pytest_stage_a_small.log, benchmark_summary.json)

### Turn Summary
Warm vs cold Stage A benchmarks are still 1.00× (133.18 s vs 133.15 s) because `compute_loss` keeps rebuilding `create_crystal_config`/`Crystal` per panel despite StageAContext, so the perf exit criterion can’t advance.
Prepared a ready-for-implementation Do Now to thread StageAContext through the Stage A closure, hoist the crystal/Simulator instantiation outside the panel loop, and preserve the cold rebuild mode for benchmarking evidence.
Next: Ralph lands the refactor, reruns `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, and executes the warm/cold benchmark script to capture the improved perf counters.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/ (Do Now + benchmark instructions)
