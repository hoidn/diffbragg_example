### Turn Summary
Extended Stage A warm-cache refactor with benchmarking toggle; added enable_stage_a_warm_cache config flag (default True) to measure 2-5× speedup.
Warm mode preserves existing perf (test_stage_a_expansion: 0.2% improvement, 13 iterations); cold mode reinstantiates detector/masks/HKL per-closure for baseline.
Next: resolve PYTHONPATH conflict to execute benchmark script and capture empirical warm vs cold wall-clock comparison.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z/ (pytest_stage_a.log, benchmark_stage_a_cache.py)
