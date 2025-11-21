Summary: Keep the canonical Stage B fallback warm by cloning StageAContext onto CPU so panel-mode runs reuse cached detectors/masks instead of rebuilding for ~80 s.
Mode: none
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — when `stage_b_full_eval_on_cpu` triggers, build/retain a CPU `StageAContext`, point Stage B closures/validations at that cache, and plumb perf counters so canonical telemetry reports `cache_mode="warm"` even though eval_device is CPU (small smokes stay on the original CUDA cache).
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — keep the ROI/warm asserts for the small detector but update the canonical path to expect `cache_mode="warm"`, `roi_mode="panel"`, and log the forward_time delta so we prove the CPU cache actually saved time.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/pytest_stage_b_small.log
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/pytest_stage_b_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/stage_b_roi_summary.json

How-To Map:
1. In `dbex/nanobrag_refinement.py`, introduce a helper that reuses `_build_stage_a_context` to spawn a CPU copy (device=`torch.device("cpu")`) when `stage_b_full_eval_on_cpu` and canonical panel mode are active; store it alongside the CUDA context after Stage A builds.
2. Thread a `stage_b_eval_stage_a_ctx` variable through the Stage B block so ROI/perf logic always talks to the cache that matches `eval_device`; keep ROI sampling disabled for canonical panel runs but ensure cached detectors/simulators are reused on CPU.
3. Update perf-counter plumbing so canonical telemetry once again emits `cache_mode="warm"`, closure/validation counts from the warm path, and the reduced `forward_time_ms` (expect a drop from ~80 s to seconds once caching works).
4. Refresh `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` to assert the new canonical telemetry (`cache_mode="warm"`, `roi_mode="panel"`, `roi_count_total=92`, `roi_count_sampled=92`) and to log the new runtime in the pytest output for perf tracking; keep small-smoke assertions unchanged.
5. Run the mapped stage_b selectors with the env vars above to generate telemetry/logs in the new artifact directory, then rerun `summarize_stage_b_roi.py` so we can cite the before/after runtimes in findings/fix_plan updates.

Pitfalls To Avoid:
- Do not flip canonical ROI mode back to ROI; Stage B strict gates still rely on panel coverage per PERF-WARM-009/010.
- Keep small-smoke ROI perf counters identical (warm CUDA cache, `roi_mode="roi"`); only canonical panel runs should move to CPU.
- Ensure the CPU cache does not mutate the original CUDA StageAContext—copy or rebuild rather than reusing mutable lists.
- Preserve deterministic random sampling; seeding/ROI order must match existing Stage B behavior.
- Leave Stage C untouched; its warm cache already lives on CUDA and still needs the original context.
- Capture telemetry/logs even if the canonical run regresses; missing JSON re-blocks the plan.
- Environment freeze still applies (no package installs, no CUDA driver changes).

If Blocked:
- If canonical Stage B still prints `cache_mode="cold"` or takes ~80 s, save both pytest logs plus telemetry JSONs, update `docs/fix_plan.md` + `galph_memory.md` with the failure signature, and halt so we can reassess before another code attempt.

Findings Applied (Mandatory):
- PERF-WARM-003 — Warm-cache changes must keep determinism; cloning StageAContext to CPU cannot alter the ROI sampling order.
- PERF-WARM-005 — ROI telemetry needs accurate `roi_mode`/counts for both cache paths; verify JSON after both selectors.
- PERF-WARM-006 — Stage B/C reuse StageAContext when warm caches exist, so canonical CPU fallback must stop reporting `cache_mode="cold"`.
- PERF-WARM-008 — Canonical Stage B still enforces the ±1 % shell-modifier gate; CPU cache reuse must not relax loss tolerances.
- PERF-WARM-011 — GPU OOM mitigation remains CPU fallback, but now we must make that fallback performant.
- PERF-WARM-012 — Address the newly-logged cold-cache regression by reusing StageAContext on CPU so runtime drops back to seconds.

Pointers:
- docs/fix_plan.md:37 — Initiative ledger and the new 2025-11-21T160700Z attempt.
- docs/findings.md:16-25 — PERF-WARM guardrails (incl. PERF-WARM-012) that define cache/telemetry expectations.
- docs/TESTING_GUIDE.md:38 — Canonical Stage B gate requirements that the tests enforce.
- dbex/nanobrag_refinement.py:1588 — Current CPU fallback logic that disables the warm cache.
- tests/dbex/test_torch_refine_smoke.py:876 — Stage B smoke harness where perf/telemetry asserts live.

Next Up (optional): Once canonical cache reuse is warm again, revisit ROI sampling (`roi_sample_fraction`) so small-smoke shell modifiers stop pegging at the clamp.

Doc Sync Plan (Conditional): none — selectors unchanged beyond telemetry expectations.

Mapped Tests Guardrail: Both mapped selectors already collect under `--smoke-detector-size={small,full}`; rerun them with telemetry logging as listed before editing docs/fix_plan/findings.

Hard Gate: Do not close this loop until telemetry_stage_b_full.json reports `cache_mode="warm"` with `status in {ok,early_stop}` and the new stage_b_roi_summary.json captures the runtime drop.

Normative Math/Physics: Stage B still minimizes the variance-weighted chi-squared `Σ((pred-obs)^2 / (pred.detach()+σ^2))` per docs/spec-db-core.md:57-80; CPU cache reuse must not change the loss definition or sigma provenance.
