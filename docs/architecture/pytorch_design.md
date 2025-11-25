# nanoBragg PyTorch Architecture Design (Addendum)
Scope: descriptive of the current/experimental torch implementation. Normative requirements live in `docs/spec-db*.md`; any SHALL/MUST language here reflects intended or current behavior and defers to the Spec‑DB shards for canonical rules.

## 1.1 Tricubic Interpolation & Detector Absorption Vectorization

The core simulator physics loops have been fully vectorized to eliminate Python-level iteration and enable efficient GPU acceleration. This section documents the batched tensor flows for two critical computational paths: structure factor interpolation and detector absorption.

### 1.1.1 Tricubic Interpolation Pipeline

**Objective:** Sample structure factors at arbitrary fractional Miller indices using 4×4×4 neighborhood interpolation without Python loops.

**Implementation:** `src/nanobrag_torch/models/crystal.py` (`_tricubic_interpolation`, commit 12742e5) and `src/nanobrag_torch/utils/physics.py` (`polint_vectorized`, `polin2_vectorized`, `polin3_vectorized`, commit f796861).

**Tensor Flow:**

1. **Batched Neighborhood Gather** (Phase C)
   - Input: Fractional Miller indices `(h, k, l)` with shape `(B,)` where `B = sources × phi_steps × mosaic_domains × oversample²`
   - Compute 64 neighbor indices: `(h0-1:h0+2, k0-1:k0+2, l0-1:l0+2)` via broadcasting
   - Output: `neighbor_F` tensor with shape `(B, 4, 4, 4)` containing structure factors for all 64 neighbors
   - Out-of-bounds handling: Single-pass bounds check; fallback to `default_F` for invalid queries

2. **Batched Polynomial Evaluation** (Phase D)
   - 1D interpolation (`polint_vectorized`): Processes `(B, 4)` → `(B,)` via vectorized Neville's algorithm
   - 2D interpolation (`polin2_vectorized`): Chains four 1D passes then aggregates
   - 3D interpolation (`polin3_vectorized`): Chains sixteen 1D passes, then four 2D passes, then final 1D
   - All operations preserve `requires_grad=True` for differentiability
   - Shape: `(B, 4, 4, 4)` → `(B,)` structure factors via pure tensor arithmetic

**Evidence:**
- **Correctness:** `tests/test_tricubic_vectorized.py` (19 tests, CPU + CUDA parametrization)
- **Performance:** Internal microbenchmarks show ≤1.2% delta vs baseline
- **Parity:** AT-STR-002 acceptance tests pass with correlation >0.999

**CUDA Status:** CPU validation complete. CUDA execution blocked by pre-existing device-placement defect (tracked in `docs/fix_plan.md` Attempt #14; see PERF-PYTORCH-004).

#### Halo Requirement and Stage Policy (descriptive; canonical rules in Spec‑DB)

- Tricubic requires a ±1 neighborhood in each of h/k/l. The dense |F| grid MUST include a ±1 halo; otherwise queries near bounds fall back to `default_F`, degrading gradients and parity.
- Stage A (geometry): current implementation runs nearest‑neighbor |F| (`interpolation=False`) to mirror DiffBragg geometry refinement and satisfy the Spec‑DB Stage‑A requirement (`spec-db-workflow.md`, DB‑AT‑025). A haloed tricubic mode exists as a tagged experiment when haloed |F| data exist; it is non‑canonical until Spec‑DB is updated.
- Stage B (Fhkl): current implementation enables interpolation with a halo and adds guards/telemetry to detect any default_F fallback when interpolation is on.

### 1.1.2 Detector Absorption Vectorization

**Objective:** Process detector thickness layers in parallel to compute depth-dependent capture fractions.

**Implementation:** `src/nanobrag_torch/simulator.py` lines 1764-1787 (validated Phase F; already vectorized).

**Tensor Flow:**

1. **Parallax Calculation**
   - Compute observation direction `obs_dir = pixel_pos / |pixel_pos|` for all pixels
   - Parallax factor: `ρ = detector_normal · obs_dir` (shape: `(S, F)`)
   - Broadcast to `(thicksteps, S, F)` for layer-wise computation

2. **Layer Capture Fractions**
   - Formula: `capture[t] = exp(−t·Δz·μ/ρ) − exp(−(t+1)·Δz·μ/ρ)` where `μ = 1/attenuation_depth`
   - Single vectorized operation processes all layers simultaneously
   - Shape: `(thicksteps, S, F)` capture fraction tensor

3. **Integration with Main Loop**
   - Batched over `(thicksteps, sources, phi_steps, mosaic_domains, oversample², S, F)`
   - Device/dtype neutral via `.device` property from input tensors
   - Preserves gradient flow (no `.item()` or detached operations)

**Evidence:**
- **Correctness:** `tests/test_at_abs_001.py` extended to 16 parametrized tests (8/8 CPU passing; CUDA blocked)
- **Performance:** CPU benchmarks show 0.0% regression vs baseline
- **Physics:** Capture fractions sum to `1 − exp(−thickness·μ/ρ)` within 1e-6 tolerance

**CUDA Status:** CPU validation complete with zero performance regression. CUDA benchmarks deferred pending device-placement fix (see `docs/fix_plan.md` Attempt #14 and Phase F summary for rerun commands).

### 1.1.3 Broadcast Shape Reference

All vectorized paths follow the canonical broadcast pattern from `docs/architecture.md` §8:

- **Pixel grid:** `(S, F)` for slow/fast detector dimensions
- **Subpixel sampling:** `(oversample², S, F)` when `oversample > 1`
- **Thickness layers:** `(thicksteps, S, F)` for detector absorption
- **Full batch:** `(sources, phi_steps, mosaic_domains, oversample², thicksteps, S, F)` in the general case

Extensions must preserve these shapes; adding a new sampling dimension requires expanding the broadcast pattern, not introducing Python loops.

### 1.1.4 Follow-Up Work

**CUDA Performance & Validation:** Once the device-placement defect is resolved (PERF-PYTORCH-004):
1. Rerun `tests/test_tricubic_vectorized.py` on CUDA (expect 19/19 passing)
2. Rerun `tests/test_at_abs_001.py -k cuda` (expect 8/8 passing)
3. Record updated CUDA benchmark metrics and update `docs/fix_plan.md` with the results

### 1.1.5 Source Weighting & Integration

**Objective:** Support equal weighting by default while honoring explicit per-source weights when provided.

**Implementation:** `src/nanobrag_torch/simulator.py` lines 399-423 (guard) and steps normalization at line 1892. Default path divides by the number of sources (equal weighting). When a `-lambda`/per-source weight vector is provided, the simulator multiplies each source contribution by the corresponding weight before accumulation.

**Normative Reference:** See `docs/spec-db-core.md` (Source Handling and Weighting) for the canonical rules: equal weighting by default; per-source weights allowed and interpreted as one coefficient per source; a global flux/exposure knob is separate from per-source weights.

**Validation:**
- Equal-weight handling verified with repeated runs of `tests/test_cli_scaling.py::TestSourceWeightsDivergence` (7 tests passing) with observed correlation ≥0.999 and |sum_ratio−1| ≤5e-3.
- Add/extend tests to cover explicit per-source weights once CLI/config plumbing is finalized (planned AT‑SRC to mirror DB‑AT coverage).

**Data Flow:**
1. Parse source weights (CLI/config). If none, synthesize an equal-weight vector of length `n_sources`.
2. Multiply each source’s contribution by its weight; accumulate across sources.
3. Normalize: `I_scaled = r_e^2 * fluence * I / steps` where `steps = source_count * ...`; flux/exposure remain global scalars.

**Acceptance:** Equal-weight path remains validated; per-source weighted path SHALL be validated by the forthcoming AT‑SRC/DB‑AT source-weighting selector once wired.

## 1.2 Differentiability vs Performance

Principle: Differentiability is required; over-hardening is not. Prefer the minimal change that passes gradcheck and preserves vectorization.

- Minimal Differentiability Contract
  - Return analytic limits at removable singularities only when the raw op produces NaN/Inf or unacceptable relative error in tests.
  - Keep the nominal fast path branch-free (or mask-based) and fully vectorized.
  - Avoid speculative guards and extra branches unless backed by (a) a reproduced gradient failure or (b) a measured numerical/perf improvement.

- Branching Budget (Hot Helpers)
  - Per-element branching inside hot helpers (e.g., `sincg`, `sinc3`, polarization) must be justified with numbers (gradcheck evidence or microbenchmark delta).

- Mask vs Guard
  - Masks gate analytic limits; a single epsilon guard may backstop tiny denominators. If the mask tolerance renders guards redundant, prefer the mask alone.

- Precision Guidance
  - Default dev dtype: float64; default prod dtype: float32. Tolerances must state dtype assumptions and be tested in both where relevant.

- Acceptance Criteria for Helper Changes
  - Show a before/after gradcheck result (float64 required, float32 if relevant).
  - Include a microbenchmark (≥1e6 evaluations) comparing old/new helper.
  - Confirm vectorization preserved (no data-dependent Python control flow).
