Summary: Capture warm vs cold Stage A benchmark evidence by fixing the script's module path, tagging telemetry with cache mode, and rerunning the perf measurements.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T095520Z/

Do Now:
- PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
  - Implement: dbex/nanobrag_refinement.py::RefinementTelemetry — add a `cache_mode` string ("warm"|"cold") defaulting to "warm" and set it from `run_nanobrag_refinement` so Stage A telemetry artifacts record which cache path executed.
  - Implement: plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py::main — prepend the repo root to `sys.path`, pull the cache mode from telemetry into the report, and ensure warm/cold runs write JSON + text outputs under `$ARTIFACTS` without relying on packaged installs.
  - Implement: docs/findings.md::PERF-WARM-001 — log measured warm vs cold runtimes, speedup ratio, cache-mode telemetry note, and artifact paths for exit criterion #1.
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee $ARTIFACTS/collect_stage_a.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_a.log
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts $ARTIFACTS | tee $ARTIFACTS/benchmark_stage_a_cache.txt
  - Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T095520Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T095520Z
- mkdir -p "$ARTIFACTS"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee "$ARTIFACTS/collect_stage_a.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_a.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts "$ARTIFACTS" | tee "$ARTIFACTS/benchmark_stage_a_cache.txt"

Pitfalls To Avoid:
- Warm cache stays the default; only disable via the new flag inside controlled benchmarks.
- Preserve Stage B/C telemetry fields when adding cache-mode; avoid schema churn outside Stage A.
- Keep deterministic seeds (`NANOBRAGG_DISABLE_COMPILE=1`, no torch.compile) so warm/cold runs remain comparable.
- Ensure benchmark script prepends the workspace path before importing `dbex`; do not edit environment installs.
- Run benchmarks serially (warm then cold) to prevent cache interference and capture isolated logs.
- Store JSON/text outputs only under `$ARTIFACTS`; avoid emitting large HDF5 products.
- Update docs/findings.md in-place with concise evidence; no new sections or duplicated entries.
- Document any failure by capturing stderr/stdout before retrying; no silent reruns.

If Blocked:
- Tee failing command output to "$ARTIFACTS/blocker.log", mark PERF-WARM-SIM-001 blocked in docs/fix_plan.md with the error signature, append the block and unblock condition to galph_memory.md, and hold for supervisor guidance.

Findings Applied (Mandatory):
- PERF-WARM-001 — Warm cache remains default; benchmarking artifacts must reflect cache mode and script location.
- RUNTIME-001 — CPU refinements require `NANOBRAGG_DISABLE_COMPILE=1` for deterministic perf comparisons.
- TESTING-003 — Capture collect-only logs alongside pytest runs for selector hygiene.
- DIAGNOSTICS-001 — Preserve `/torch_diagnostics` schema when adding telemetry fields.

Pointers:
- dbex/nanobrag_refinement.py:321 — `RefinementTelemetry` dataclass to extend with `cache_mode` and populate inside Stage A.
- dbex/nanobrag_refinement.py:592 — Stage A warm/cold branch point to tag telemetry and reuse perf counters.
- tests/dbex/test_torch_refine_smoke.py:370 — Stage A smoke assertions to extend with cache-mode validation.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py:1 — Benchmark script header/main path to adjust sys.path and artifact writes.
- docs/findings.md:45 — Knowledge base entry to refresh with measured timings once benchmark succeeds.

Next Up (optional):
- Extend warm-cache telemetry and perf counters to Stage B shell modifiers once Stage A evidence lands.
