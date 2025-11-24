# spec-db-runtime.md — Runtime and Execution (Normative)

Overview (Normative)
- Purpose: Define execution guardrails for PyTorch‑backed simulation and refinement, ensuring determinism, performance, and differentiability.

Status
- Applies to the planned `nanobrag_torch` backend. The legacy DiffBragg path does not use these PyTorch runtime guardrails.
- Use `python -m dbex.refine_one` for the current CLI (see `dbex/refine_one.py:5-26`).

Runtime Guardrails (Normative)
- Vectorization: Callers SHALL avoid Python loops over pixels/ROIs when vectorized simulator capabilities exist (per‑panel run or cropped detectors).
- Device/dtype neutrality: Callers SHALL co‑locate tensors on the target device/dtype before `run()`; SHALL NOT call `.to()` inside tight loops.
- Differentiability: Callers SHALL NOT use `.item()/.detach()` on differentiable parameters in forward passes; SHALL avoid `torch.linspace` endpoints that break graphs; use arange‑based arithmetic.
- torch.compile: Simulator MAY compile graphs; callers SHALL keep tensor shapes stable during reuse to preserve caches. Changing image shape or oversample SHALL trigger re‑instantiation.
- Eager fallback: `NANOBRAGG_DISABLE_COMPILE=1` SHALL disable compilation for debugging.
- Seeds: Conformance SHALL specify deterministic seeds; random sources (if any) SHALL be controlled by explicit seeding.

### Parameterization Correctness & Round-Trip (Normative)

- UB / A* round-trip:
  - Any new Stage‑A parameterization (including quaternion‑based ones) SHALL pass a round‑trip correctness check against dxtbx and the Busing–Levy conventions defined in `docs/spec-db-core.md` at the zero point:
    - Starting from the baseline `A*_0 = crystal.get_A()` and baseline cell `c₀` from dxtbx, implementations MUST construct `B₀ = B(c₀)` and `U₀ = A*_0 @ B₀⁻¹` (or an equivalent pair satisfying `U₀ @ B₀ = A*_0`), and with `params=0` MUST reproduce `U(0)=U₀`, `B(0)=B₀`, and `A*(0)=U₀ @ B₀` within a documented numerical tolerance.
  - Implementations SHALL provide a small, executable test (see `docs/spec-db-conformance.md`) that exercises this round trip and fails fast if the parameterization drifts from the dxtbx baseline.

- Prohibited patterns in production refinement:
  - Production refinement code SHALL NOT use inverse decompositions `A* → (U,B)` to derive the baseline state or to update simulator geometry.
  - Such decompositions MAY be used in diagnostic tooling only, and MUST be clearly separated from the runtime path used for DB‑AT‑024 mapping‑aligned runs.

Environment (Normative)
- `KMP_DUPLICATE_LIB_OK=TRUE` SHALL be set in all entry points importing torch.
- `CUDA_VISIBLE_DEVICES` MAY be used to pin GPUs; device index SHALL be configurable.

Shape‑Change Policy (Normative)
- Reuse a warmed Simulator when `spixels/fpixels` and oversample are constant.
- Rebuild Detector/Simulator when panel dimensions or oversample change.

Compile Modes (Informative)
- GPU commonly uses `mode="max-autotune"`; CPU may use `reduce-overhead`.

References (Informative)
- docs/nanobrag_api.md (runtime details, including `ExperimentModel` Stage‑A parameterization).
