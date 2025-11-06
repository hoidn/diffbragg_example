Summary: Benchmark Stage A warm cache vs cold baseline by adding a config toggle, running a dedicated script, and updating the perf finding with measured speedup.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z/

Do Now:
- PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
  - Implement: dbex/nanobrag_refinement.py::RefinementConfig — add an `enable_stage_a_warm_cache` boolean (default True) documented for benchmarking so legacy cold-mode rebuilding can be invoked explicitly without changing existing callers.
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — honor the new flag by skipping `_build_stage_a_context` when False, reinstantiating detector configs/masks/HKL tensors inside `compute_loss` for a cold baseline while keeping perf counters, telemetry schema, and warm default behavior intact.
  - Implement: plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py::main — add a T2 script that runs Stage A twice (warm + cold) with identical inputs, records wall-clock/perf counter totals, and writes JSON + human-readable summaries under `$ARTIFACTS`.
  - Implement: docs/findings.md::PERF-WARM-001 — capture the measured warm vs cold timings, ratio, script path, and any caveats so exit criterion #1 has traceable evidence.
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee $ARTIFACTS/collect_stage_a.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_a.log
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts $ARTIFACTS | tee $ARTIFACTS/benchmark_stage_a_cache.txt
  - Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z
- mkdir -p "$ARTIFACTS"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee "$ARTIFACTS/collect_stage_a.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_a.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts "$ARTIFACTS" | tee "$ARTIFACTS/benchmark_stage_a_cache.txt"

Pitfalls To Avoid:
- Warm cache must remain the default path; only flip the flag inside benchmarking contexts.
- Keep Stage B/C telemetry untouched and ensure perf_counters structure stays consistent across modes.
- Reuse deterministic seeds and masks from existing helpers so warm vs cold remain directly comparable.
- Do not persist large HDF5 outputs outside `$ARTIFACTS`; store summaries/JSON only.
- Script should exit non-zero on failure and surface traceback so blockers are easy to capture.
- Maintain CPU-only determinism with `NANOBRAGG_DISABLE_COMPILE=1` and avoid torch.compile side effects.
- Ensure cold mode reinstantiates detectors/masks inside the closure; avoid accidentally reusing cached tensors.
- Update docs/findings.md in-place rather than creating new sections elsewhere.
- Keep new config field import-safe for existing callers (sane default, no positional arg churn).
- Guard benchmark script length (≤T2 complexity) and document usage within the script header per policy.

If Blocked:
- Capture failing command output to "$ARTIFACTS/blocker.log", set PERF-WARM-SIM-001 status to `blocked` in docs/fix_plan.md with the error signature, append the block + retry condition to galph_memory.md, and stop to await supervisor guidance.

Findings Applied (Mandatory):
- PERF-WARM-001 — Warm cache refactor stays default; benchmarking flag/script must not regress reuse semantics.
- RUNTIME-001 — CPU runs require `NANOBRAGG_DISABLE_COMPILE=1` for determinism.
- TESTING-003 — Record collect-only output before pytest execution and store logs with the node.
- DIAGNOSTICS-001 — Telemetry additions must preserve existing `/torch_diagnostics` consumers.

Pointers:
- dbex/nanobrag_refinement.py:235 — `RefinementConfig` definition to extend with the warm-cache toggle.
- dbex/nanobrag_refinement.py:569 — Stage A perf counters + closure setup; branch warm vs cold here.
- dbex/nanobrag_refinement.py:712 — Detector reuse loop that should rebuild when cold mode is requested.
- tests/dbex/test_torch_refine_smoke.py:230 — Stage A smoke selector and telemetry assertions validating new behavior.
- plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/pytest_stage_a.log — Baseline (cold) runtime reference used for planning.

Next Up (optional):
- Stage B cache/perf counters once Stage A speedup evidence is finalized.
