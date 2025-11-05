# PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per‑Iteration Re‑Instantiation

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
1) 2–5× speedup on CPU for Stage A smoke selector at current defaults (same dataset/seed). Document baseline vs improved timings.
2) Numeric parity within existing tolerances for a fixed seed on Stage A; Stage B/C parity where applicable.
3) Perf telemetry present in `/torch_diagnostics` (counts/timings) without breaking existing readers/tests.
4) No environment/toolchain changes; tests remain deterministic.

## Tasks (No environment changes)
- A1: Add stage context type and refactor Stage A to prebuild models and hoist tensors; update closure to parameter‑only updates.
- A2: Add perf telemetry counters; wire to HDF5.
- B1: Apply reuse pattern to Stage B (shell modifiers), ensuring modified HKL grid remains on device.
- C1: Apply reuse pattern to Stage C with distance override tensors.
- V1: Add micro‑bench harness (timings printed/logged) and document results in artifacts.
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

