# PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per‑Iteration Re‑Instantiation

> Deferral Note (2025-11-23): Per TORCH-API-ALIGN-001, all warm/cold cache work is deferred until after the simulator wiring refactor and ExperimentModel adapter land. Do not modify warm-cache logic during that initiative. New parity/adapter tests will force warm-cache OFF and set `NANOBRAGG_DISABLE_COMPILE=1` via fixtures for determinism.

## Motivation
Current refinement loops repeatedly re‑instantiate `Detector`, `Crystal`, and `Simulator` for every closure/iteration and for each sampled panel (e.g., Stage A/B/C paths in `dbex/nanobrag_refinement.py`). This guarantees fresh state but imposes a large, avoidable performance tax, especially with CPU‑only, compile‑disabled test settings and LBFGS’s multi‑closure behavior. Migrating to a warm, reusable simulator with parameter‑only updates should yield substantial speedups without changing physics.

Environment Freeze: No runtime/toolchain changes. Deterministic CPU tests remain intact. This initiative is a refactor and scheduling policy change, not a physics change.

## Goals
- Reuse per‑panel `Detector` models and a stage‑scoped `Crystal`/`Simulator`; avoid rebuilding inside the optimizer closure.
- Hoist mask→tensor conversion and HKL tensors to the target device once per stage.
- Update only parameter tensors during optimization (scale, cell logs/angles, misset, Stage B shell modifiers, Stage C distances).
- Preserve numeric equivalence within documented tolerances; keep existing telemetry structure intact and add light perf telemetry.

## Non‑Goals
- Changing physics or loss definition.
- Enabling GPU or `torch.compile` in tests (remain CPU + compile‑disabled for determinism).
- Altering acceptance thresholds in tests (unless needed to switch validation cadence; document if so).

## Scope & Affected Code
- Stage A: `run_nanobrag_refinement` — panel loop and LBFGS closure reuse path (Detector/Crystal/Simulator) in `dbex/nanobrag_refinement.py`.
- Stage B: Shell‑modifier loop reuse and HKL grid modification strategy.
- Stage C: Per‑panel distance offsets with prebuilt models + distance override tensors.
- Bridge helpers remain as‑is; ensure mask tensors and HKL grid are attached once.

### Existing Implementation Note
- Stage A already implements an ROI‑aware warm cache and perf‑telemetry contract (e.g., `roi_count_total`, `roi_count_sampled`, `cache_mode`, `roi_mode`, `forward_time_ms`) as documented in `docs/fix_plan.md` under `[PERF-WARM-SIM-001]`.
- Future work that extends warm‑cache/ROI behavior or perf telemetry should **evolve this contract inside PERF-WARM-SIM-001 (or a successor perf initiative)** and keep tests/docs in sync, rather than introducing parallel cache or telemetry schemas in other plans.

## Design Sketch
- Introduce a stage context (e.g., `RefinementStageContext`) constructed once per stage:
  - Holds: list of per‑panel `Detector` models, one `Crystal` model, one `Simulator` (or one per panel if required by API), device/dtype, pre‑tensorized masks, HKL tensors/metadata.
  - Exposes lightweight setters for parameter tensors the optimizer updates.
- Closure uses context to run forward passes without constructing new Python objects or re‑tensorizing masks/HKL.
- Validation cadence knob: keep `full_validation_interval` but allow optional subset validation between full checks.
- Telemetry: add perf counters (forward time per iteration, closure evals per LBFGS step, number of full validations) under `/torch_diagnostics` while preserving existing fields.

## Risks & Mitigations
- Hidden state in `nanobrag_torch` tied to construction: validate by comparing one‑step outputs old vs new for identical params (tolerance gate) and fall back to minimal reconstruction if required (e.g., when shapes change).
- Memory footprint growth from cached models: monitor and batch panels if needed; adopt ROI‑cropped models in follow‑ups if memory becomes limiting.

## Exit Criteria
1) 2–5× speedup on CPU for Stage A smoke selector at current defaults (same dataset/seed). Document baseline vs improved timings. **Deferred** — post-2025-11-21 scope change: benchmarking will resume after the engine refactor; until then, no sprinting on perf targets.
2) Numeric parity within existing tolerances for a fixed seed on Stage A; Stage B/C parity where applicable.
3) Perf telemetry present in `/torch_diagnostics` (counts/timings) without breaking existing readers/tests.
4) No environment/toolchain changes; tests remain deterministic.

## Tasks (deferred benchmarking)
- A1: Add stage context type and refactor Stage A to prebuild models and hoist tensors; update closure to parameter-only updates.
- A2: Add perf telemetry counters; wire to HDF5.
- B1: Apply reuse pattern to Stage B (shell modifiers), ensuring modified HKL grid remains on device.
- C1: Apply reuse pattern to Stage C with distance override tensors.
- V1: **Deferred** — micro-bench harness + pass/fail guard to be implemented when the initiative resumes (requires hardware/dataset spec).
- D1: Update `docs/findings.md` with before/after timings and lessons; add a brief note in `docs/spec-db-runtime.md` on warm model reuse guidance.

## Artifacts
```
plans/active/PERF-WARM-SIM-001/
  implementation.md
  reports/
    <YYYY-MM-DDTHHMMSSZ>/
      baseline_timings.json
      improved_timings.json
      parity_check.json
      summary.md
```

## Timeline
Estimated 1–2 engineering days across A (Stage A), then C, then B. Prioritize Stage A first to realize immediate gains.

## Phase D — Stage C Detector Reuse (PERF-WARM-013)

- **D1 — Context metadata**: Extend `StageAContext` (and `_build_stage_a_context`) with baseline per-panel distance vectors plus ROI→panel maps so downstream stages can mutate cached detectors without cloning configs. Spec refs: `docs/spec-db-runtime.md §2.1` (cache reuse) and `docs/spec-db-workflow.md §Stage C`.
- **D2 — Retarget helpers**: Add a helper (e.g., `_retarget_stage_a_detectors`) that applies bounded distance deltas to every cached simulator/ROI entry, mirroring `_retarget_stage_a_simulators` but operating on detector geometry. Guard CPU fallbacks and dtype/device parity.
- **D3 — Stage C warm path**: Refactor `compute_loss_stage_c` plus the final Stage C reconstruction block (`dbex/nanobrag_refinement.py:2238-2545`) to call the new helper whenever `stage_c_use_warm_cache` is true so we stop instantiating fresh `Detector`/`Simulator` objects per ROI/panel. Cold mode stays untouched.
- **D4 — Telemetry + docs**: Rerun Stage C smokes (small + full detectors) with `DBEX_SMOKE_TELEMETRY_PATH` rooted at the new report directory, capture `telemetry_stage_c_{small,full}.json`, regenerate `stage_c_roi_summary.json`, and update `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md` only if the workflow changes (per Test Registry Sync rules).

## Phase D Status Update (2025-11-23T180000Z)

**D1-D3: ✓ COMPLETE**
- D1: Extended StageAContext with roi_panel_map field (dbex/nanobrag_refinement.py:381, 647)
- D2: Implemented _retarget_stage_a_detectors helper (lines 693-770) with lazy imports, bounds checks, fallback path
- D3: Refactored Stage C warm branches (compute_loss_stage_c lines 3121-3165, final reconstruction lines 3471-3515)

**D4: ✗ BLOCKED**
Test harness bug (ARCH-REFINE-FLOW-001 StageA wrapper inputs dict mismatch). Phase D code compiles cleanly. See phase_d_decision.md for details.

**Overall:** Implementation complete, runtime validation deferred to harness fix.

## Phase F — ROI-mode Simulator Trace (PERF-WARM-016)

Purpose: Stage C warm-cache retargeting now fixes panel-mode runs, but ROI-mode (full-detector) executions still ignore new detector distances. We need hard evidence showing how cached ROI simulators mutate (or fail to mutate) when `_retarget_stage_a_detectors` runs so we can repair the ROI path without another blind implementation attempt.

### Checklist
- [ ] F1: Add an opt-in debug hook to `_retarget_stage_a_detectors` that captures per-call panel/ROI distance summaries (baseline vs updated, ROI indices/bboxes, simulator ids) and writes JSON snapshots to a user-provided directory (`DBEX_STAGE_C_CACHE_DEBUG_PATH`). Keep the instrumentation completely disabled by default so smoke/perf runs stay unchanged.
- [ ] F2: Re-run Stage C small and full smoketests with `DBEX_STAGE_C_CACHE_DEBUG_PATH` pointing into `plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/` so we archive both panel-mode (passing) and ROI-mode (failing) traces. Capture pytest logs, telemetry JSON, and the new cache-debug JSON payloads for analysis.

### Notes
- The debug hook is evidence-only; do not mutate acceptance gates or fix the ROI bug in this phase.
- Stage C full smoketest still fails due to the known +0.067% chi² drift; run it under `|| true` so artifacts/logs are captured despite the failing assertion.
