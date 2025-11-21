Summary: Gate Stage A ROI caches so only the warm path uses them and refresh the benchmark/logging to prove the warm vs cold speedup clears the ≥2× target.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/

Do Now:
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — add an `allow_cold_stage_a_roi_mode` override (default False), require warm cache (or the override) before `_build_stage_a_context` constructs ROI entries / ROI sampling runs, and tag Stage A perf telemetry with the ROI mode + sampled counts so benchmark logs prove which path executed.
- Implement: plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py::run_stage_a_benchmark — explicitly disable ROI mode for the cold pass (and plumb a CLI arg/flag to re-enable if needed), then persist the updated `benchmark_summary.json`/perf counters under the new artifacts path so the recorded speedup compares warm(ROI) against cold(panel).
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/

How-To Map:
1. Warm-only ROI gate: edit `dbex/nanobrag_refinement.py` so `RefinementConfig` gains `allow_cold_stage_a_roi_mode` (default False) and `use_stage_a_roi_mode` becomes `enable_stage_a_roi_mode and canonical_roi_count>0 and (enable_stage_a_warm_cache or allow_cold_stage_a_roi_mode)`; ensure `_build_stage_a_context` receives the gated flag and that telemetry/perf_counters now report `roi_mode` ("roi" vs "panel") plus sampled/total counts.
2. Stage A smoke (captures telemetry + regression guard):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/telemetry_stage_a_small.json \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
   ```
   Verify telemetry shows `roi_mode="roi"`, `roi_count_total=92`, and ROI sampling only when warm cache is enabled.
3. Benchmark refresh (records ≥2× speedup evidence):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py \
     --modes warm cold \
     --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/
   ```
   Ensure the script forces `enable_stage_a_roi_mode=True` for warm and False for cold (unless `--allow-cold-roi` is passed) so `benchmark_summary.json` reports `speedup>=2.0`. Capture `{warm,cold}_perf_counters.json`, `benchmark_report.txt`, and note the exact wall-clock numbers in the artifact README.
4. Findings/docs: append the new benchmark metrics to `docs/findings.md` row PERF-WARM-005 (or add a new row if behavior changes) and note in `docs/fix_plan.md` Attempts History if telemetry/ratio reveals additional work.

Pitfalls To Avoid:
- Do not relax the Stage A loss/ROI gates; only route ROI mode based on the new config flag.
- Keep `enable_stage_a_roi_mode` default True so production warm runs remain ROI-backed.
- Leave Stage B/C logic untouched; if edits seem necessary, stop and draft a new plan per layered-scope guard.
- Do not change dataset knobs in the benchmark; always use the canonical refGeom assets with identical seeds as previous logs.
- Keep `AUTHORITATIVE_CMDS_DOC`/env vars identical to the testing guide to avoid conformance drift.
- Avoid touching CUDA/toolchain deps (Environment Freeze) even if perf seems limited.
- Ensure telemetry/perf counters stay deterministic (integers for ROI counts, no random sampling without seeds).
- Do not delete older benchmark artifacts; add the new directory alongside prior runs.

If Blocked:
- Capture the failure signature (e.g., ROI gate misdetects warm mode, benchmark still <2×) in `docs/fix_plan.md` Attempts History and dump the minimal error snippet into `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/blockers.txt`.
- Note the condition in `galph_memory.md` (state=blocked, dwell reset) and propose whether to pivot to Stage B ROI caching or unblock prerequisites.

Findings Applied (Mandatory):
- PERF-WARM-001 — Honor the warm-cache perf counters + benchmarking harness already in place; keep commands identical and log new numbers.
- PERF-WARM-002 — Ensure the cache actually hoists detector/crystal instantiation; the new ROI gate must not reintroduce per-closure rebuilds.
- PERF-WARM-005 — Record the ROI batching takeaway (warm≈14.5 s, cold≈14.6 s) and supersede it with the new warm-vs-panel results once verified.

Pointers:
- dbex/nanobrag_refinement.py:237 — RefinementConfig + Stage A context show where to add the ROI override.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py:1 — Benchmark CLI needs the cold ROI toggle and artifact logging updates.
- docs/spec-db-runtime.md:10 — Warm cache / vectorization guardrails justify keeping detector/ROI reuse tied to the warm path.
- plans/active/PERF-WARM-SIM-001/implementation.md:1 — Initiative goals plus exit criteria #1 (≥2× Stage A speedup) frame the acceptance bar for this Do Now.

Next Up (optional):
- Extend the same ROI-only warm cache gating to Stage B shell modifiers once Stage A speedup evidence sticks.
- Profile whether Stage A cold path still rebuilds HKL tensors unnecessarily; if so, consider a T2 probe before flipping more switches.
