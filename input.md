# Input

- Summary: Convert Stage A warm caching to simulate only the sampled ROI bounding boxes so each LBFGS closure touches the pixels referenced by `panel_slices`, then re-run the Stage A smoke + warm/cold benchmark to document the new speedup.
- Mode: Perf
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/telemetry_stage_a_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/

## Do Now
- Focus Item: PERF-WARM-SIM-001
- Implement: `dbex/nanobrag_refinement.py::run_nanobrag_refinement` + `dbex/nanobrag_bridge.py::create_detector_config` — add ROI-aware Stage A context that builds cropped Detector/Simulator pairs per `panel_slices`, samples ROIs instead of full panels inside the closure (with a cold-mode rebuild path), and updates telemetry/`roi_sample_fraction` semantics while keeping Stage B/C behavior unchanged.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/

## How-To Map
1. Refactor Stage A warm cache: extend `_build_stage_a_context` with ROI entries (one per `inputs.panel_slices`) that precompute cropped DetectorConfigs (updating `spixels/fpixels`, beam-center offsets, and mask slices) and cache ROI-sized `Simulator` objects; teach `compute_loss` to sample ROI entries rather than panel IDs and to fall back to the existing panel path when `config.enable_stage_a_roi_mode` is False.
2. Update telemetry + config plumbing: expose a flag on `RefinementConfig` (default True) for ROI sampling, count ROIs when reporting `roi_count_{sampled,total}`/`n_rois`, and keep the cold-mode branch by rebuilding ROI detectors/simulators on the fly when `enable_stage_a_warm_cache=False` so the benchmark still has a control path.
3. Stage A smoke (small detector) with telemetry capture:
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/pytest_stage_a_small.log`
4. Stage A smoke (full detector parity) to prove ROI batching respects canonical assets:
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/telemetry_stage_a_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/pytest_stage_a_full.log`
5. Warm vs cold benchmark (same dataset/seed) to document the new gain:
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py --modes warm cold --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/ | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/benchmark.log`
   Record the updated `benchmark_summary.json`, `{warm,cold}_perf_counters.json`, and call out the measured speedup (target ≥1.3×; note findings if it still plateaus).
6. Summarize ROI counts, telemetry deltas (forward time mean/total, closure_evals), and benchmark speedup in `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/summary.md`, then refresh `docs/fix_plan.md`/`docs/findings.md` only if the gain still misses the ≥2× goal.

## Pitfalls To Avoid
- Keep Stage B/C code paths untouched; only Stage A should switch to ROI batching.
- Respect bbox semantics (`x1/y1` are exclusive) when cropping detector/mask slices to avoid off-by-one geometry shifts.
- Adjust beam centers in millimetres before casting to tensors so the cropped DetectorConfig still points to the physical beam location.
- Preserve the cold-mode benchmark by rebuilding ROI detectors when `enable_stage_a_warm_cache=False`; do not short-circuit the control arm.
- Ensure ROI sampling still honors deterministic ordering/seed so Stage A smoke and benchmarks remain reproducible.
- Maintain `sigma_readout`/mask dtype/device placement; no `.to()` calls inside the ROI loop beyond the initial cache per spec-db-runtime.

## If Blocked
- If ROI detector cropping cannot be expressed correctly (e.g., geometry validation fails or simulator refuses smaller frames), capture the traceback plus ROI diagnostics under the artifact directory, mark PERF-WARM-SIM-001 `blocked` in docs/fix_plan.md, and include the failure signature in the summary so we can reassess whether tooling fixes are needed upstream.

## Findings Applied (Mandatory)
- PERF-WARM-003 — Warm vs cold benchmarks sit at 1.01× because we render full panels; ROI-level execution is needed to change the math.
- PERF-WARM-004 — Simulator caching alone trims ~2% of forward time, so the next optimization must reduce the number of simulated pixels.
- MASKING-001 — Loss-mask coverage is <1%, so cropping compute to ROI bounding boxes is spec-compliant and should slash runtime.
- RUNTIME-001 — Keep `NANOBRAGG_DISABLE_COMPILE=1`/`KMP_DUPLICATE_LIB_OK=TRUE` for reproducible perf measurements and grad stability.

## Pointers
- dbex/nanobrag_refinement.py:720 — Stage A currently samples `n_panels` (1) so every closure renders the entire detector despite sparse ROIs.
- dbex/nanobrag_bridge.py:279 — `create_detector_config` needs ROI-aware overrides (beam-center shifts, mask cropping) to describe sub-panels.
- docs/spec-db-workflow.md §Stage Smoke Dataset Policy — ROI-only compute via cropped detectors is explicitly permitted for Stage smokes/perf work.
- docs/findings.md (PERF-WARM-0xx) — Baseline benchmarks and guardrails we must beat; cite when logging the new metrics.
- plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py — Canonical harness/inputs for the warm vs cold comparison; reuse it verbatim.

## Next Up (optional)
- If the ROI path lands quickly, begin drafting Stage B/C cache tasks (shared simulator pools, ROI-aware shell modifiers) so perf gains extend beyond Stage A.
