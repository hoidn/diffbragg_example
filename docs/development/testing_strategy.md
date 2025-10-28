# nanoBragg PyTorch Testing Strategy

**Version:** 1.1  
**Date:** 2024-07-25  
**Owner:** [Your Name/Team]

## 1. Introduction & Philosophy

This document outlines the comprehensive testing strategy for the PyTorch implementation of nanoBragg. The primary goal is to ensure that the new application is a correct, verifiable, and trustworthy scientific tool.
Our testing philosophy is a three-tiered hybrid approach, designed to build confidence layer by layer:

1. **Tier 1: Translation Correctness:** We first prove that the PyTorch code is a faithful, numerically precise reimplementation of the original C code's physical model. The C code is treated as the "ground truth" specification.
2. **Tier 2: Gradient Correctness:** We then prove that the new differentiable capabilities are mathematically sound.
3. **Tier 3: Scientific Validation:** Finally, we validate the model against objective physical principles.

All tests will be implemented using the PyTest framework.

### 1.4 PyTorch Device & Dtype Discipline

- **Device-neutral code:** Every PyTorch path MUST operate correctly on both CPU and CUDA tensors and across supported dtypes. Do not hard-code `.cpu()`/`.cuda()` calls, create CPU-only constants, or assume float64 execution when the caller may supply float32/half tensors.
- **Authoritative smoke runs:** When a change touches tensor math, run the authoritative reproduction command once on CPU and once on CUDA (when available). Capture both logs/metrics and attach them to the fix plan. Treat any `torch.compile` or Dynamo warning about mixed devices as blocking.
- **Targeted tests:** Prefer parametrised tests that iterate over `device in {"cpu", "cuda"}` (guarded by `torch.cuda.is_available()`). At minimum, ensure a `gpu_smoke` marker or equivalent pytest node exercises the new logic on CUDA before declaring success.
- **Helper utilities:** Encapsulate device/dtype harmonisation in small helpers (e.g., `tensor.to(other_tensor)` or `type_as`). Centralise these helpers in reusable modules to keep the rule enforceable across future PyTorch projects.
- **Cache dtype consistency:** When implementing cached computations, ensure cache retrieval coerces to current `dtype` to support dynamic dtype switching. Use `.to(device=self.device, dtype=self.dtype)` instead of `.to(self.device)` alone. See `Detector.get_pixel_coords()` (lines 762-777) for reference implementation.
- **CI gate:** If CI offers GPU runners, add a fast smoke job that runs the `gpu_smoke` marker (or agreed command) so regressions like CPU↔GPU tensor mixing fail quickly.
- **Vectorization check:** Confirm `_compute_physics_for_position` and related helpers remain batched across sources/phi/mosaic/oversample; extend broadcast dimensions instead of adding Python loops.
- **Runtime checklist:** Consult `docs/development/pytorch_runtime_checklist.md` during development and cite it in fix-plan notes for PyTorch changes.
- **Gradient test guard:** All gradient tests require `NANOBRAGG_DISABLE_COMPILE=1` environment variable to prevent torch.compile interference with gradcheck. See §4.1 for execution requirements and canonical commands.

### 1.5 Loop Execution Notes (Do Now + Validation Scripts)

- Do Now must include an exact pytest command: In the supervisor→engineer handoff (`input.md`), include the precise `pytest` node(s) that reproduce the active item. If no test exists, first author the minimal targeted test and then run it.
- Prefer reusable validation scripts: Place ad‑hoc validations under `scripts/validation/` and reference them from `input.md` rather than embedding Python snippets inline. Keep them portable and invoke via the project’s standard CLI/env.
- Test cadence per loop: Run targeted tests first; execute the full `pytest` suite at most once per engineer turn (end of loop) when code changed. For prompt/docs‑only loops, use `pytest --collect-only -q` to verify import/collection.

## 2. Configuration Parity

**CRITICAL REQUIREMENT:** Before implementing any test that compares against recorded golden outputs, you **MUST** ensure exact configuration parity. All golden test cases must be generated with commands that are verifiably equivalent to the PyTorch test configurations.

**Authoritative Reference:** See the **[C-CLI to PyTorch Configuration Map](./c_to_pytorch_config_map.md)** for:
- Complete parameter mappings
- Implicit conventions (pivot modes, beam adjustments, rotation axes)
- Common configuration bugs and prevention strategies

Configuration mismatches are the most common source of test failures. Always verify:
- Pivot mode (BEAM vs SAMPLE) based on parameter implications
- Convention-specific adjustments (e.g., MOSFLM's 0.5 pixel offset)
- Default rotation axes for each convention
- Proper unit conversions at boundaries
 - Explicit convention selection: tests and harnesses MUST pass `-convention` (or equivalent API flag) to avoid implicit CUSTOM switching when vector parameters are present


## 2.1 Golden Reference Data

The testing strategy relies on a PyTorch-generated Golden Suite. For each case we maintain:
1. **Golden Output Image:** The simulator’s final tensor serialized to `.bin`.
2. **PyTorch Trace Log:** A step-by-step log for a representative pixel captured via `debug_config`.
3. **Configuration Metadata:** JSON describing detector, beam, crystal, and sampling settings.

All artifacts are versioned under `nanoBragg2/tests/golden_data/` alongside the test harness.

### 2.2 Trace Capture

Use the simulator `debug_config.trace_pixel` option (or the trace fixtures in `nanoBragg2/tests/conftest.py`) to capture per-pixel traces. The trace payload is emitted by the same PyTorch code path used in production, ensuring debugging sessions analyse real execution state.

### 2.3 Golden Test Cases

The following PyTorch-generated scenarios make up the Golden Suite. Each lives under `nanoBragg2/tests/golden_data/` with output, trace, and metadata files.

| Test Case Name | Description | Purpose |
| :--- | :--- | :--- |
| `simple_cubic` | A 100Å cubic cell, single wavelength, no mosaicity, no oscillation. | Baseline geometry and spot calculation. |
| `triclinic_P1` | A low-symmetry triclinic cell with misset orientation. | Stress-test reciprocal space and geometry calculations. |
| `simple_cubic_mosaic` | The `simple_cubic` case with mosaic spread. | Validate mosaic domain implementation. |
| `cubic_tilted_detector` | Cubic cell with rotated and tilted detector. | Validate general detector geometry. |

### 2.4 Refreshing Golden Data

Follow `nanoBragg2/docs/spec_generation_guide.md` to regenerate golden images, traces, and metadata whenever simulator behavior changes. Capture new artifacts with the PyTorch harness, commit them alongside code changes, and document the refresh in `docs/fix_plan.md`.

## 2.5 Validation Matrix (AT ↔ tests ↔ commands)

This matrix maps each acceptance test profile to its PyTorch-only pytest selector. The commands assume execution from the repository root with any required environment flags described in `docs/TESTING_GUIDE.md`.

- AT‑PARALLEL‑001 — Beam Center Scaling  
  Command: `pytest -v nanoBragg2/tests/test_at_parallel_001.py`

- AT‑PARALLEL‑002 — Pixel Size Independence  
  Command: `pytest -v nanoBragg2/tests/test_at_parallel_002.py`

- AT‑PARALLEL‑004 — MOSFLM 0.5 Pixel Offset  
  Command: `pytest -v nanoBragg2/tests/test_at_parallel_004.py`

- AT‑PARALLEL‑006 — Single Reflection Position  
  Command: `pytest -v nanoBragg2/tests/test_at_parallel_006.py`

- AT‑PARALLEL‑007 — Peak Position with Rotations  
  Command: `pytest -v nanoBragg2/tests/test_at_parallel_007.py`


For equivalence debugging (AT‑PARALLEL failures, correlation below thresholds, structured diffs), generate aligned traces:

- Pixel selection: choose a strong on‑peak pixel close to the beam center or a specified coordinate in the test; record the exact `(s,f)` indices used.
- PyTorch trace: emit a structured log containing, at minimum, `pix0_vector`, basis vectors, `R` (distance), solid angle (both point‑pixel and obliquity‑corrected), close_distance and obliquity factor, `k_in`, `k_out`, `S`, Miller indices (float and rounded), `F`, lattice factors (`F_latt_a/b/c`, product), `F^2`, `F_latt^2`, `omega/solid_angle`, pixel area, fluence and final intensity.
- Golden trace: reuse the stored golden trace for the same pixel (or regenerate via the trace harness) and ensure units match the PyTorch log (meters, steradians, Å where noted).
- Dtype/device: debug in float64 on CPU for determinism unless the AT explicitly requires GPU.
- Artifacts: save as `reports/debug/<DATE>/AT-<ID>/{golden_trace.log, py_trace.log, metrics.json, diff_heatmap.png}` and cite paths in the plan.

### 2.5.2 Matrix Gate (hard preflight)

Before any parity run in a debugging loop:

- Resolve the AT in this matrix to the exact pytest node(s) and required environment.
- Ensure the corresponding golden artifacts (images, traces, metadata) are present; regenerate them before running tests if they are stale.
- Run the canonical pytest command first. Supplemental diagnostics (e.g., targeted unit tests) may follow but cannot substitute for the mapped selector.
- If an AT mapping is missing or incomplete, add a minimal entry here (test file, env, canonical command) and append a TODO in `docs/fix_plan.md` referencing the addition.
 - Friction rule: If the same preparation steps (env export, pytest node, trace generation) are repeated across two loops, factor them into a minimal helper (e.g., a one‑liner shell alias or small script) and reference it in this matrix. Record the addition briefly in `docs/fix_plan.md` Attempts History. Do not bypass pytest; helpers should only wrap the mapped canonical commands.

### 2.5.3 Normative Parity Coverage (SHALL)

- Every acceptance test in `docs/spec-db-conformance.md` with a numerical tolerance MUST have:
  - A human-readable entry in this matrix (test path, environment, canonical command), and
  - A corresponding machine-readable case in `tests/parity_cases.yaml` powering `tests/test_parity_matrix.py`.
- Missing coverage in either location is blocking. The fix plan cannot mark the AT done until the mapping exists or an explicit harness entry (with pass/fail logic) is added.
- Documentation updates MUST keep the matrix and YAML file in sync with the canonical command line (arguments, sweeps, thresholds).

#### 2.5.3a Parity Case Classification Criteria (SHALL)

**Purpose:** Clarify which AT-PARALLEL tests belong in `parity_cases.yaml` (parameterized harness) vs standalone test files (custom logic).

**Classification Rules:**
- **parity_cases.yaml ONLY:** Simple parameter sweeps with standard correlation/sum metrics, no custom post-processing
  - Examples: AT-001 (beam center scaling), AT-002 (pixel size sweeps), AT-006 (distance/wavelength sweeps)
- **parity_cases.yaml + Standalone (BOTH):** Basic image generation via YAML; standalone adds custom validation logic
  - Examples: AT-010 (adds 1/R² scaling physics checks), AT-016 (adds NaN/Inf robustness checks)
  - Pattern: YAML generates images for correlation checks; standalone test loads those images and applies domain-specific validation
- **Standalone ONLY:** Custom algorithms, special infrastructure, or complex validation that cannot be expressed in YAML
  - Examples:
    - AT-008 (Hungarian peak matching algorithm)
    - AT-013 (deterministic mode setup, platform fingerprinting)
    - AT-027 (HKL file loading, F² scaling validation)
    - AT-029 (FFT spectral analysis, aliasing measurement)

**Linter Expectations:**
- The linter (`scripts/lint_parity_coverage.py`) flags all ATs with C↔Py correlation thresholds as potentially missing from `parity_cases.yaml`
- Standalone-only ATs (008, 013, 027, 029) produce warnings that should be ignored
- BOTH-type ATs (010, 016) should appear in parity_cases.yaml to suppress warnings; their standalone tests add extra validation

**Decision Flowchart:**
1. Does the AT have a golden-data correlation threshold? → If NO, skip (not a parity test)
2. Does validation require custom Python logic (algorithms, FFT, file I/O, special checks)? → If YES:
   - Can basic image generation use parameter sweeps? → If YES, use BOTH (YAML + standalone); if NO, standalone only
3. Is it a pure parameter sweep with standard metrics? → YES, use parity_cases.yaml only

### 2.5.4 Artifact-Backed Closure (SHALL)

- Success claims for parity-threshold ATs MUST cite artifacts from a mapped parity path meeting thresholds:
  - Metrics: correlation, MSE, RMSE, max |Δ|, C_sum, Py_sum, sum_ratio (optional SSIM when helpful).
  - Storage: under `reports/<date>-AT-<ID>/metrics.json` (or equivalent) plus supporting visuals (diff heatmaps/overlays) when failures occur.
  - fix_plan Attempts History MUST reference these paths (look for `Metrics:` / `Artifacts:` entries).
- No artifacts → no closure; reopen the fix plan item instead.

### 2.5.5 Environment Canonicalization Preflight (SHALL)

- Confirm that required environment variables from `docs/TESTING_GUIDE.md` are exported (e.g., `KMP_DUPLICATE_LIB_OK=TRUE`, determinism guards).
- Ensure the golden dataset path (`nanoBragg2/tests/golden_data/`) is accessible and up to date before executing parity tests.
- Invoke PyTorch parity via `sys.executable` to ensure the active virtual environment executes the run.
- Treat missing artifacts or misconfigured environments as blocking errors (fail fast rather than skipping parity).

### 2.5.6 CI Meta-Check (Docs-as-Data)

- CI MUST lint for:
  - Spec → matrix → YAML coverage for all parity-threshold ATs.
  - Existence of mapped commands/binaries referenced in the YAML.
  - Presence of artifact paths when fix_plan marks parity items complete.
- CI SHOULD fail when any invariant above is violated; parity documentation is normative.

## 2.6 CI Gates (Parity & Traces)

To prevent drift, CI should enforce the following fast gates on CPU:

- Detector geometry visual parity: run `scripts/verify_detector_geometry.py` and fail if any reported correlation against the golden dataset drops below the documented thresholds (e.g., ≥0.999 for baseline/tilted unless otherwise specified). Save PNG and metrics JSON as artifacts.
- Trace parity check: generate one golden trace and one PyTorch trace for the canonical pixel (`tests/golden_data/simple_cubic_pixel_trace.log` spec) and assert no first‑difference at the named checkpoints (e.g., pix0_vector, basis vectors, q, h,k,l, omega_pixel). Attach golden_trace.log/py_trace.log on failure.

Optional visual parity harness (sanity check):

- Script: `scripts/comparison/run_parallel_visual.py`
- Run: `python scripts/comparison/run_parallel_visual.py`
- Output: PNGs and `metrics.json` under `parallel_test_visuals/AT-PARALLEL-XXX/`

When the visual harness and the AT tests disagree, treat the AT tests as the primary gate (authoritative) and use parallel trace‑driven debugging (Section 2.1) to identify the first divergence. Scripts are supportive tools; conformance is determined by the pytest suite.

## 2.7 Determinism Validation Workflow

**Purpose:** Ensure reproducible simulations across platforms, devices, and runs.

### 2.7.1 Authoritative Tests

| Test File | Purpose | Key Validations |
|-----------|---------|----------------|
| `tests/test_at_parallel_013.py` | Cross-platform determinism | Same-seed bitwise equality, different-seed independence, float64 precision, platform fingerprint |
| `tests/test_at_parallel_024.py` | Mosaic/misset RNG determinism | LCG bitstream parity, seed isolation, `mosaic_rotation_umat` determinism, umat↔misset round-trip |

### 2.7.2 Environment Setup

Determinism tests require specific environment guards to prevent non-deterministic behavior:

```bash
# Required before pytest execution:
export CUDA_VISIBLE_DEVICES=''           # Force CPU-only (avoid CUDA non-determinism)
export TORCHDYNAMO_DISABLE=1             # Disable TorchDynamo graph capture
export NANOBRAGG_DISABLE_COMPILE=1       # Disable torch.compile in simulator
export KMP_DUPLICATE_LIB_OK=TRUE         # Avoid MKL conflicts

# Execute determinism tests:
pytest -v tests/test_at_parallel_013.py tests/test_at_parallel_024.py
```

**Rationale:**
- `CUDA_VISIBLE_DEVICES=''`: GPU operations may introduce non-deterministic atomics/reductions. CPU execution guarantees bitwise reproducibility.
- `TORCHDYNAMO_DISABLE=1`: Prevents TorchDynamo/Triton CUDA device query crashes when `CUDA_VISIBLE_DEVICES=''` is set (TorchDynamo attempts to index device 0 on zero-length device list).
- `NANOBRAGG_DISABLE_COMPILE=1`: Ensures simulator respects Dynamo disable flag.
- Test files MUST set environment variables at module level before `torch` import (see implementation note below).

### 2.7.3 Validation Metrics

**Same-Seed Runs (Bitwise Reproducibility):**

| Metric | Threshold | Spec Reference |
|--------|-----------|----------------|
| `np.array_equal(img1, img2)` | ✅ True (exact match) | AT-PARALLEL-013 §Same-Seed |
| Correlation | ≥0.9999999 | AT-PARALLEL-013 §Same-Seed |
| `np.allclose(img1, img2, rtol=1e-7, atol=1e-12)` | ✅ True | AT-PARALLEL-013 §Same-Seed |
| Max absolute difference | ≤1e-10 (float64) | AT-PARALLEL-013 §Precision |

**Different-Seed Runs (Statistical Independence):**

| Metric | Threshold | Spec Reference |
|--------|-----------|----------------|
| `np.array_equal(img1, img2)` | ❌ False (must differ) | AT-PARALLEL-013 §Diff-Seed |
| Correlation | ≤0.7 (low correlation) | AT-PARALLEL-013 §Diff-Seed |
| Non-zero pixels differ | ≥50% | AT-PARALLEL-013 §Diff-Seed |

### 2.7.4 Reproduction Commands

```bash
# Full determinism suite:
CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
KMP_DUPLICATE_LIB_OK=TRUE pytest -v \
  tests/test_at_parallel_013.py \
  tests/test_at_parallel_024.py

# Individual tests:
# Same-seed bitwise equality (critical):
CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
KMP_DUPLICATE_LIB_OK=TRUE pytest -v \
  tests/test_at_parallel_013.py::TestATParallel013CrossPlatformConsistency::test_pytorch_determinism_same_seed

# LCG bitstream parity (seed contract validation):
CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
KMP_DUPLICATE_LIB_OK=TRUE pytest -v \
  tests/test_at_parallel_024.py::TestATParallel024RandomMisset::test_lcg_compatibility
```

**Expected Results:**
- AT-PARALLEL-013: 5 passed, 1 skipped (runtime ~5-6s)
- AT-PARALLEL-024: 5 passed, 1 skipped (runtime ~4-5s)
- Total: 10 passed, 2 skipped

**Skipped Tests:** `test_c_pytorch_equivalence` (both files) require `NB_RUN_PARALLEL=1` and C binary

### 2.7.5 Implementation Note

**Test files MUST set environment variables at module level before `torch` import:**

```python
# CORRECT (tests/test_at_parallel_013.py lines 1-10):
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCHDYNAMO_DISABLE'] = '1'
os.environ['NANOBRAGG_DISABLE_COMPILE'] = '1'

import torch  # ← Import AFTER env setup
import numpy as np
import pytest
```

**Why:** PyTorch initializes CUDA runtime on import if `torch.cuda.is_available()` returns `True`. Setting `CUDA_VISIBLE_DEVICES` after import has no effect.

### 2.7.6 Artifact Expectations

- Test logs: `reports/2026-01-test-suite-triage/phase_d/<STAMP>/determinism/`
- Metrics: Correlation values, `np.array_equal` results, float64 precision checks
- Environment snapshot: `env.json` capturing Python/PyTorch/CUDA versions
- Commands log: `commands.txt` with exact reproduction steps

### 2.7.7 Known Limitations

- **CUDA Determinism:** Currently deferred. Tests force CPU-only execution to avoid TorchDynamo device query bug. Future work: Re-enable CUDA execution after upstream fix, validate GPU determinism with `torch.cuda.manual_seed_all()` and CuDNN deterministic mode.
- **Noise Seed:** Current tests focus on mosaic/misset seeds. Poisson noise determinism (`seed` parameter) validated implicitly but not traced in detail. Add explicit noise seed tests if regressions occur.

### 2.7.8 References

- Spec: `docs/spec-db-runtime.md` §5.3 (RNG determinism), `docs/spec-db-conformance.md` AT-parity profiles
- Architecture: `docs/architecture.md` ADR-05 (Deterministic Sampling & Seeds)
- Implementation: `src/nanobrag_torch/utils/c_random.py` (LCG), `src/nanobrag_torch/models/crystal.py` (seed propagation)
- Phase C Analysis: `reports/determinism-callchain/phase_c/20251011T052920Z/testing_strategy_notes.md` (detailed workflow notes)

## 3. Tier 1: Translation Correctness Testing

**Goal:** To prove the PyTorch code is a faithful port of the C code.

### 3.1 The Foundational Test: Parallel Trace Validation

All debugging of physics discrepancies **must** begin with a parallel trace comparison. Comparing only the final output images is insufficient and can be misleading. The line-by-line comparison of intermediate variables between the C-code trace and the PyTorch trace is the only deterministic method for locating the source of an error and is the mandatory first step before attempting to debug with any other method.

### 3.2 Unit Tests (`tests/test_utils.py`)

**Target:** Functions in `utils/geometry.py` and `utils/physics.py`.  
**Methodology:** For each function, create a PyTest test using hard-coded inputs. The expected output will be taken directly from the Golden C-Code Trace Log.

### 3.3 Component Tests (`tests/test_models.py`)

**Target:** The `Detector` and `Crystal` classes.  
**Methodology:** The primary component test is the **Parallel Trace Comparison**.

- `test_trace_equivalence`: A test that runs `scripts/debug_pixel_trace.py` to generate a new PyTorch trace and compares it numerically, line-by-line, against the corresponding Golden C-Code Trace Log. This single test validates the entire chain of component calculations.

### 3.4 Integration Tests (`tests/test_simulator.py`)

**Target:** The end-to-end `Simulator.run()` method.  
**Methodology:** For each test case, create a test that compares the final PyTorch image tensor against the golden `.bin` file using `torch.allclose`. This test should only be expected to pass after the Parallel Trace Comparison test passes.

**Primary Validation Tool:** The main script for running end-to-end parallel validation against the C-code reference is `scripts/verify_detector_geometry.py`. This script automates the execution of both the PyTorch and C implementations, generates comparison plots, and computes quantitative correlation metrics. It relies on `scripts/c_reference_runner.py` to manage the C-code execution.

## 4. Tier 2: Gradient Correctness Testing

**Goal:** To prove that the automatic differentiation capabilities are mathematically correct.

### 4.1 Gradient Checks (`tests/test_gradients.py`)

*   **Target:** All parameters intended for refinement.
*   **Methodology:** We will use PyTorch's built-in numerical gradient checker, `torch.autograd.gradcheck`. For each parameter, a test will be created that:
    1.  Sets up a minimal, fast-to-run simulation scenario.
    2.  Defines a function that takes the parameter tensor as input and returns a scalar loss.
    3.  Calls `gradcheck` on this function and its input.
*   **Requirement:** The following parameters (at a minimum) must pass `gradcheck`:
    *   **Crystal:** `cell_a`, `cell_gamma`, `misset_rot_x`
    *   **Detector:** `distance_mm`, `Fbeam_mm`
    *   **Beam:** `lambda_A`
    *   **Model:** `mosaic_spread_rad`, `fluence`

**Execution Requirements (MANDATORY):**
*   **All gradient tests MUST set `NANOBRAGG_DISABLE_COMPILE=1`** environment variable before importing torch to prevent torch.compile interference
*   **Rationale:** torch.compile creates donated buffers that break gradient computation during numerical gradient checks
*   **Implementation:** Test files set `os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"` at module level (before torch import)
*   **Canonical command:**
    ```bash
    env CUDA_VISIBLE_DEVICES=-1 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
      pytest -v tests/test_gradients.py -k "gradcheck" --tb=short
    ```
*   **Validation:** Phase M2 (2025-10-11T172830Z) confirmed 10/10 gradcheck tests pass with guard enabled
*   **Reference:** `reports/2026-01-test-suite-triage/phase_m2/20251011T172830Z/summary.md` for validation artifacts

**Performance Expectations (Slow Gradient Suite):**
*   **Maximum runtime tolerance:** Gradient stability tests (particularly `test_property_gradient_stability`) may run up to 905 seconds on CPU with float64 precision and compile guard enabled
*   **Rationale:** High-precision numerical gradient checks (`torch.autograd.gradcheck`) require extensive finite-difference computations across large parameter spaces, inherently slow on CPU
*   **Marker:** Tests expected to exceed standard timeouts are marked with `@pytest.mark.timeout(905)` and `@pytest.mark.slow_gradient`
*   **Validation:** Phase P timing packet (2025-10-15T060354Z) established initial 900s ceiling with 6 percent margin above 845.68s Phase O baseline; Phase Q validation (2025-10-15T071423Z) confirmed 839.14s runtime; Phase R uplift (2025-10-15T091543Z) raised ceiling to 905s after observing 900.02s breach in chunk 03 rerun, maintaining 0.5 percent safety margin
*   **CI integration:** pytest-timeout dependency required; install via `pip install pytest-timeout` or `pip install -e ".[test]"` (includes optional test dependencies)
*   **Evidence artifacts:** `reports/2026-01-test-suite-triage/phase_p/20251015T060354Z/c18_timing.md` (tolerance derivation), `reports/2026-01-test-suite-triage/phase_q/20251015T071423Z/summary.md` (validation results)

### 4.2 Multi-Tier Gradient Testing

**Comprehensive gradient testing requires multiple levels of verification:**

#### 4.2.1 Unit-Level Gradient Tests
- **Target:** Individual components like `get_rotated_real_vectors`
- **Purpose:** Verify gradients flow correctly through isolated functions
- **Example:**
  ```python
  def test_rotation_gradients():
      phi_start = torch.tensor(10.0, requires_grad=True, dtype=torch.float64)
      config = CrystalConfig(phi_start_deg=phi_start)
      rotated_vectors = crystal.get_rotated_real_vectors(config)
      assert rotated_vectors[0].requires_grad
      assert torch.autograd.gradcheck(lambda x: crystal.get_rotated_real_vectors(
          CrystalConfig(phi_start_deg=x))[0].sum(), phi_start)
  ```

#### 4.2.2 Integration-Level Gradient Tests
- **Target:** End-to-end `Simulator.run()` method
- **Purpose:** Verify gradients flow through complete simulation chain
- **Critical:** All configuration parameters must be tensors to preserve gradient flow

#### 4.2.3 Gradient Stability Tests
- **Target:** Parameter ranges and edge cases
- **Purpose:** Verify gradients remain stable across realistic parameter variations
- **Example:**
  ```python
  def test_gradient_stability():
      for phi_val in [0.0, 45.0, 90.0, 180.0]:
          phi_start = torch.tensor(phi_val, requires_grad=True, dtype=torch.float64)
          config = CrystalConfig(phi_start_deg=phi_start)
          result = simulator.run_with_config(config)
          assert result.requires_grad
  ```

#### 4.2.4 Gradient Flow Debugging
- **Purpose:** Systematic approach to diagnose gradient breaks
- **Methodology:**
  1. **Isolation:** Create minimal test case with `requires_grad=True`
  2. **Tracing:** Check `requires_grad` at each computation step
  3. **Break Point Identification:** Find where gradients are lost
  4. **Common Causes:**
     - `.item()` calls on differentiable tensors (detaches from computation graph)
     - `torch.linspace` with tensor endpoints (known PyTorch limitation)
     - Manual tensor overwriting instead of functional computation
     - Using `.detach()` or `.numpy()` on tensors that need gradients

## 5. Tier 3: Scientific Validation Testing

**Goal:** To validate the model against objective physical principles, independent of the original C code.

### 5.1 First Principles Tests (`tests/test_validation.py`)

*   **Target:** The fundamental geometry and physics of the simulation.
*   **Methodology:**
    *   **`test_bragg_spot_position`:**
        1.  Configure a simple case: cubic cell, beam along Z, detector on XY plane, no rotations.
        2.  Analytically calculate the exact (x,y) position of a low-index reflection (e.g., (1,0,0)) using the Bragg equation and simple trigonometry.
        3.  Run the simulation.
        4.  Find the coordinates of the brightest pixel in the output image using `torch.argmax`.
        5.  Assert that the simulated spot position is within one pixel of the analytically calculated position.
    *   **`test_polarization_limits`:**
        1.  Configure a reflection to be at exactly 90 degrees 2-theta.
        2.  Run the simulation with polarization set to horizontal. Assert the spot intensity is near maximum.
        3.  Run again with polarization set to vertical. Assert the spot intensity is near zero.

## 6. Tooling & Benchmark Hygiene

- **Directory layout:** Place benchmarks, profilers, and ad-hoc tooling under `scripts/` (e.g., `scripts/benchmarks/benchmark_detailed.py`). Do not add standalone executables to the repo root.
- **Environment parity:** All tooling must honour the same environment contract as the tests (`KMP_DUPLICATE_LIB_OK=TRUE`, `NB_C_BIN` precedence, editable install). Scripts SHOULD exit with a non-zero status if prerequisites are missing.
- **Plan integration:** When a benchmark exposes a regression, log the command, metrics, and artifact path under `docs/fix_plan.md` › `## Suite Failures` or the relevant tracking section.
- **Generalisation:** These expectations apply to any PyTorch project you touch—structure tooling predictably, rely on documented env vars, and keep benchmark commands discoverable through project docs.
