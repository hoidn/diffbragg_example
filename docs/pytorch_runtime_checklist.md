# PyTorch Runtime Checklist

Use this quick checklist before and after every PyTorch simulator edit. It distills the authoritative guidance from
`docs/architecture/pytorch_design.md`, `CLAUDE.md`, and the testing strategy, and enforces the normative requirements
from `docs/spec-db-runtime.md:10-20` and `docs/spec-db-conformance.md:10-48`.

1. **Vectorization** (`docs/spec-db-runtime.md:11`)
   - Do not reintroduce Python loops that duplicate work already handled by batched tensor code.
   - When adding a new flow (sources, phi, mosaic, oversample), extend the existing broadcast shapes instead of looping.
   - Verify `_compute_physics_for_position` receives tensors with the expected batch dimensions.
   - **Tricubic & Absorption Evidence:** Phases C-F validated batched gather/polynomial interpolation and detector absorption with 0% performance regression on CPU (`nanoBragg2/reports/2025-10-vectorization/phase_e/`, `phase_f/`). Regression commands (run from the DBEX repo root): `pytest nanoBragg2/tests/test_tricubic_vectorized.py -v` (19 tests) and `pytest nanoBragg2/tests/test_at_abs_001.py -v -k cpu` (8 tests). CUDA reruns resume after the device-placement fix (PERF-PYTORCH-004).

2. **Device & Dtype Neutrality** (`docs/spec-db-runtime.md:12-13`)
   - **Default dtype is float32** for performance and memory efficiency. Precision-critical operations (gradient checks, metric duality) explicitly override to float64 where required.
   - Materialize configuration tensors (beam, detector, crystal) on the execution device before the main loop.
   - Avoid per-iteration `.to()`, `.cpu()`, `.cuda()`, or tensor factories (`torch.tensor(...)`) inside compiled regions; cache constants once.
   - Run CPU **and** CUDA smoke commands (`pytest -v -m gpu_smoke`, targeting `nanoBragg2/tests/`) when a GPU is available.
   - **Cache dtype neutrality:** When retrieving cached tensors for comparison, use `.to(device=..., dtype=...)` to match both device AND dtype of live tensors. Example from `Detector.get_pixel_coords()`:
     ```python
     # Retrieve cached basis vector with dtype coercion
     cached_f = self._cached_basis_vectors[0].to(device=self.device, dtype=self.dtype)
     # Now safe to compare with live geometry tensor
     torch.allclose(self.fdet_vec, cached_f, atol=1e-15)  # ✅ Both same dtype
     ```
     Omitting `dtype=` causes `RuntimeError` when dtype switches occur (e.g., `detector.to(dtype=torch.float64)`).

3. **torch.compile Hygiene** (`docs/spec-db-runtime.md:14-15`)
   - Watch the console for Dynamo "graph break" warnings; treat them as blockers.
   - Benchmarks should reuse compiled functions; avoid changing shapes every call unless batching logic handles it.
   - **Gradient tests MUST disable compile:** Set `NANOBRAGG_DISABLE_COMPILE=1` environment variable before running gradient tests to prevent torch.compile interference with `torch.autograd.gradcheck`. See `docs/development/testing_strategy.md` §4.1 for canonical command. Test files set `os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"` before importing torch.

4. **Source Handling & Equal Weighting (C-Parity)**
   - **Do not apply source weights as multiplicative factors.** The weight column in sourcefiles is parsed but ignored per `specs/spec-a-core.md:151-153`.
   - Steps normalization divides by source count, not weight sum: `steps = sources * mosaic_domains * phisteps * oversample^2`.
   - CLI `-lambda` is authoritative for all sources; sourcefile wavelength column is also ignored.
   - **Parity Memo:** `nanoBragg2/reports/2025-11-source-weights/phase_h/20251010T002324Z/parity_reassessment.md` confirms C reference (nanoBragg.c:2570-2720) implements equal weighting; correlation ≥0.999, |sum_ratio−1| ≤5e-3 are the validated thresholds.
   - **Tests:** `pytest nanoBragg2/tests/test_cli_scaling.py::TestSourceWeights* -v` (expect 7/7 passing)

5. **Environment Variables** (`docs/spec-db-runtime.md:18-20`)
   - **Required in all torch entry points:** `KMP_DUPLICATE_LIB_OK=TRUE`
   - **For gradient tests:** `NANOBRAGG_DISABLE_COMPILE=1` (see §3 above)
   - **Optional GPU control:** `CUDA_VISIBLE_DEVICES` for device pinning

6. **Acceptance Test Hooks** (`docs/spec-db-conformance.md:10-48`)
   - **Forward Equivalence Profile:** DB-AT-001 (DiffBragg vs torch forward smoke; ROI correlation ≥0.2 per integration plan), DB-AT-002 (determinism under fixed seeds)
   - **Gradient-Safe Profile:** DB-AT-010 (gradcheck on refined parameters), DB-AT-011 (no graph breaks under runtime mask/loss)
   - **Workflow Integration Profile:** DB-AT-020 (DIALS reflection ingestion), DB-AT-021 (mask polarity), DB-AT-022 (ROI background semantics), DB-AT-023 (ADU vs photons policy), DB-AT-024 (mapping consistency)
   - **Commands:** All acceptance tests run via `pytest -v tests -k DB_AT_XXX` with `KMP_DUPLICATE_LIB_OK=TRUE` environment variable set.

7. **Documentation & Tests**
   - Update relevant docs/tests when you change vectorization or device handling.
   - Capture timings/metrics (CPU vs CUDA) and link them in `docs/fix_plan.md`.
   - **Gradient test performance:** Slow gradient tests (marked with `@pytest.mark.slow_gradient`) may legitimately run up to 905 seconds on CPU with float64 precision. This is expected behavior for high-precision numerical gradient checks, not a performance regression. Phase R uplift (2025-10-15T091543Z) raised ceiling to 905s after observing 900.02s breach in chunk 03 rerun.

Keep this checklist open while working; cite it in fix-plan entries so the vectorization/device guardrails stay visible.
