# spec-db-runtime.md — Runtime and Execution (Normative)

Overview (Normative)
- Purpose: Define execution guardrails for PyTorch‑backed simulation and refinement, ensuring determinism, performance, and differentiability.

Status
- These runtime guardrails apply to any backend that claims Spec‑DB conformance. At present, the only backend targeting Spec‑DB conformance is `nanobrag_torch`. The legacy DiffBragg backend (`--backend diffbragg`, current default) is diagnostic-only and does not currently satisfy these requirements.

Runtime Guardrails (Normative)
- Vectorization: Callers SHALL avoid Python loops over pixels/ROIs when vectorized simulator capabilities exist (per‑panel run or cropped detectors).
- Device/dtype neutrality: Callers SHALL co‑locate tensors on the target device/dtype before `run()`; SHALL NOT call `.to()` inside tight loops.
- Differentiability: Callers SHALL NOT use `.item()/.detach()` on differentiable parameters in forward passes; SHALL avoid `torch.linspace` endpoints that break graphs; use arange‑based arithmetic.
- torch.compile: Simulator MAY compile graphs; callers SHALL keep tensor shapes stable during reuse to preserve caches. Changing image shape or oversample SHALL trigger re‑instantiation.
- Eager fallback: `NANOBRAGG_DISABLE_COMPILE=1` SHALL disable compilation for debugging.
- Seeds: Conformance SHALL specify deterministic seeds; random sources (if any) SHALL be controlled by explicit seeding.

### Parameterization Correctness & Round-Trip (Normative)

- Canonical UB/A* zero-point definitions and the incremental parameterization are defined in `docs/spec-db-core.md` §Baseline Crystal State and Parameterization and the normative UB writeup (`writeups/torch_geometry_incremental_ub_parameterization.tex`). Backends SHALL implement that parameterization and pass DB‑AT‑026; this shard does not restate the decomposition.
- Prohibited patterns in production refinement:
  - A single, deterministic baseline decomposition `A*_0 → (U₀,B₀)` at initialization is permitted. Production refinement code SHALL NOT re‑decompose updated `A*(params)` back into `(U,B)` inside the optimization loop to drive geometry; updates MUST flow from the incremental parameterization (params → U(params), B(params) → A*(params)).
  - Diagnostic tooling MAY decompose `A*` for inspection, but such paths MUST be isolated from the runtime used for DB‑AT‑024/Stage‑A conformance.

Environment (Normative)
- `KMP_DUPLICATE_LIB_OK=TRUE` SHALL be set in all entry points importing torch.
- `CUDA_VISIBLE_DEVICES` MAY be used to pin GPUs; device index SHALL be configurable.
- Device profiles:
  - CPU Conformance Profile (v1): all DB‑AT selectors SHALL pass on CPU; telemetry SHALL record `device_profile="cpu_conformance"` (or equivalent) in `/torch_diagnostics`.
  - CUDA runs MAY be supported (e.g., `--device=cuda:0`) but are considered experimental until a CUDA Conformance Profile is published; telemetry SHOULD record `device_profile="cuda_experimental"` (or similar) for such runs.

Shape‑Change Policy (Normative)
- Reuse a warmed Simulator when `spixels/fpixels` and oversample are constant.
- Rebuild Detector/Simulator when panel dimensions or oversample change.

Compile Modes (Informative)
- GPU commonly uses `mode="max-autotune"`; CPU may use `reduce-overhead`.

References (Informative)
- docs/nanobrag_api.md (runtime details, including `ExperimentModel` Stage‑A parameterization).
- docs/config_crosswalk.md (notation ↔ config mapping for A*, U, B, cell, and loss tensors).
