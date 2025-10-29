# Parity Harness Specification (Normative)

**Version:** 1.0
**Date:** 2025-10-29
**Status:** Active

## 1. Purpose & Scope

This document defines the normative requirements for parity test harnesses validating the `nanobrag_torch` backend against golden reference data. It specifies datasets, environment configuration, metrics computation, trace capture workflows, and artifact expectations for DB-AT-001 (simple cubic parity) and DB-AT-002 (determinism validation).

**Authoritative References:**
- `docs/spec-db-conformance.md:10-48` — Acceptance test definitions and thresholds
- `docs/development/testing_strategy.md:1-451` — Comprehensive testing philosophy and parity workflow
- `docs/spec-db-tracing.md:10-26` — Tracing requirements and first-divergence workflow
- `docs/TESTING_GUIDE.md:1-91` — Environment flags and test taxonomy

## 2. DB-AT-001: Simple Cubic Parity

### 2.1 Test Objectives

Validate that the PyTorch simulator produces output images numerically equivalent to golden reference data for a simple cubic crystal geometry.

**Exit Criteria:**
- Image correlation ≥ 0.99 (Pearson correlation coefficient)
- Residual RMS within tolerance (RMSE documented in metrics.json)
- All intermediate trace checkpoints match golden trace within float64 precision

### 2.2 Golden Data Requirements

**Dataset Location:**
- Primary: `nanoBragg2/tests/golden_data/simple_cubic/` (if accessible)
- Fallback: DBEX-local mirror under `tests/fixtures/golden_data/simple_cubic/`

**Required Artifacts:**
- `golden_image_panel{p}.bin` — Golden reference image tensor (binary format, float64)
- `golden_trace_panel{p}_s{s}_f{f}.log` — Per-pixel trace for selected representative pixel
- `config.json` — Configuration metadata (detector, beam, crystal, sampling parameters)

**Verification Requirement:**
- Golden dataset MUST include SHA256 checksums in `manifest.json`
- Tests MUST validate checksums before comparison to detect data corruption

### 2.3 Configuration Parity

**Critical Parameters** (per `docs/development/c_to_pytorch_config_map.md`):
- Crystal: 100Å cubic cell, no mosaicity, no misset rotation
- Beam: Single wavelength (specified in config.json), no oscillation
- Detector: Flat panel, perpendicular to beam, square pixels
- Convention: CUSTOM (explicit, not inferred)

**Configuration Validation:**
- Tests MUST verify pixel pitch is square (raise if not per `docs/spec-db-core.md:43`)
- Tests MUST confirm `[panel, slow, fast]` tensor ordering (`docs/spec-db-core.md:24`)
- Tests MUST pass explicit `-convention` flag to avoid implicit switching

### 2.4 Environment Configuration

**Required Environment Variables:**

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

**Rationale:** Prevents MKL/BLAS library conflicts (`docs/TESTING_GUIDE.md:1.1`)

**Canonical Command:**

```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001
```

**Device/Dtype Requirements:**
- Primary validation: CPU, float64 (for deterministic baseline)
- Extended validation: Parametrize over `device in {cpu, cuda}` (if `torch.cuda.is_available()`)
- Dtypes: float64 (primary), float32 (secondary validation)

### 2.5 Metrics Computation

All DB-AT-001 test runs MUST compute and report the following metrics in `metrics.json`:

**Required Core Metrics:**
- `correlation` (float): Pearson correlation coefficient between golden and PyTorch output
- `mse` (float): Mean squared error
- `rmse` (float): Root mean squared error
- `max_abs_diff` (float): Maximum absolute pixel difference
- `sum_ratio` (float): `py_sum / golden_sum` (should be near 1.0)
- `golden_sum` (float): Sum of all golden pixel intensities
- `py_sum` (float): Sum of all PyTorch pixel intensities
- `n_pixels` (int): Total pixels compared

**Required Metadata:**
- `test_id` (string): "DB-AT-001"
- `timestamp` (string): ISO 8601 timestamp
- `golden_path` (string): Path to golden reference data
- `py_output_path` (string): Path to PyTorch output data
- `dtype` (string): torch.dtype used (e.g., "float64")
- `device` (string): torch.device used (e.g., "cpu", "cuda:0")
- `threshold_met` (bool): True if correlation ≥ 0.99
- `spec_threshold` (float): 0.99

**Optional Extended Metrics:**
- `ssim` (float): Structural similarity index (optional for visual validation)
- `mean_intensity_golden` (float): Mean pixel intensity in golden data
- `mean_intensity_py` (float): Mean pixel intensity in PyTorch output
- `runtime_s` (float): Test execution time
- `hardware` (string): Hardware description (CPU model or GPU model)
- `python_version` (string): Python version
- `torch_version` (string): PyTorch version
- `n_panels` (int): Number of detector panels
- `target_shape` (array): Shape of input/target tensors
- `notes` (string): Freeform notes

**Metrics Computation Helpers:**

Tests MUST use standardized computation functions to ensure consistency:

```python
import numpy as np
from scipy.stats import pearsonr

def compute_parity_metrics(golden, py_output):
    """
    Compute standardized parity metrics per parity_harness_spec.md §2.5

    Args:
        golden: numpy array or torch tensor (golden reference)
        py_output: numpy array or torch tensor (PyTorch output)

    Returns:
        dict with required core metrics
    """
    # Convert to numpy if needed
    if hasattr(golden, 'cpu'):
        golden = golden.cpu().numpy()
    if hasattr(py_output, 'cpu'):
        py_output = py_output.cpu().numpy()

    # Flatten for correlation computation
    g_flat = golden.flatten()
    p_flat = py_output.flatten()

    # Core metrics
    correlation = pearsonr(g_flat, p_flat)[0]
    diff = p_flat - g_flat
    mse = np.mean(diff ** 2)
    rmse = np.sqrt(mse)
    max_abs_diff = np.max(np.abs(diff))
    golden_sum = np.sum(g_flat)
    py_sum = np.sum(p_flat)
    sum_ratio = py_sum / golden_sum if golden_sum != 0 else float('nan')

    return {
        'correlation': float(correlation),
        'mse': float(mse),
        'rmse': float(rmse),
        'max_abs_diff': float(max_abs_diff),
        'sum_ratio': float(sum_ratio),
        'golden_sum': float(golden_sum),
        'py_sum': float(py_sum),
        'n_pixels': int(g_flat.size)
    }
```

### 2.6 Trace Capture Workflow

Per `docs/spec-db-tracing.md:10-26`, parity debugging MUST follow the trace-first workflow:

**Pixel Selection Strategy:**
- Choose a strong on-peak pixel near beam center
- Document exact `(panel, slow, fast)` indices in trace log filename
- Prefer pixels with high intensity in golden data (top 10th percentile)

**Trace Content Requirements** (per `docs/development/testing_strategy.md:117`):

Golden and PyTorch traces MUST include the following checkpoints:
- `pix0_vector` — Detector pixel origin in lab frame
- `basis_vectors` — Detector fast/slow vectors
- `R` — Sample-to-pixel distance
- `solid_angle` — Point-pixel solid angle
- `obliquity_factor` — Obliquity correction factor
- `k_in` — Incident beam wave vector
- `k_out` — Scattered wave vector
- `S` — Scattering vector
- `miller_indices_float` — (h, k, l) as floats
- `miller_indices_rounded` — (h, k, l) as integers
- `F` — Structure factor
- `F_latt_a`, `F_latt_b`, `F_latt_c` — Lattice factors per axis
- `F_latt_product` — F_latt_a × F_latt_b × F_latt_c
- `F_squared` — |F|²
- `F_latt_squared` — |F_latt|²
- `omega_solid_angle` — Solid angle (with obliquity)
- `pixel_area` — Pixel area
- `fluence` — Incident fluence
- `final_intensity` — Computed pixel intensity

**Trace Format:**
- Use consistent units: meters (geometry), steradians (solid angle), Ångströms (wavelength)
- Precision: float64 for determinism
- Format: Structured log (JSON or line-delimited key-value pairs)

**Trace Comparison:**
- Compare traces line-by-line to identify first divergence point
- Document first divergence in `parity/summary.md` with checkpoint name and delta value

**Naming Convention:**
- Golden trace: `golden_trace_panel{p}_s{s}_f{f}.log`
- PyTorch trace: `py_trace_panel{p}_s{s}_f{f}.log`
- Example: `golden_trace_panel0_s1200_f1000.log`

### 2.7 Artifact Layout

All DB-AT-001 test runs MUST produce artifacts under:

```
plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/parity/
```

**Required Artifacts:**
- `metrics.json` — Standardized metrics per §2.5
- `golden_trace_panel{p}_s{s}_f{f}.log` — Golden reference trace
- `py_trace_panel{p}_s{s}_f{f}.log` — PyTorch trace for same pixel
- `diff_heatmap_panel{p}.png` — Visual diff heatmap (golden - py) per panel
- `summary.md` — Human-readable summary with threshold status and first divergence notes

**Optional Artifacts:**
- `overlay_panel{p}.png` — Overlay visualization (golden + py)
- `histogram_diff.png` — Histogram of pixel differences
- `commands.txt` — Exact reproduction commands
- `env.json` — Environment snapshot (Python/PyTorch/CUDA versions)

**Artifact References:**
- Fix plan Attempts History MUST cite artifact path in `Artifacts:` line
- Metrics MUST be attached for all closure claims

### 2.8 Pass/Fail Criteria

**PASS conditions:**
- `correlation ≥ 0.99` (per `docs/spec-db-conformance.md:27`)
- No first divergence detected in trace comparison (all checkpoints match within float64 tolerance)
- Checksums validate for golden data

**FAIL conditions:**
- `correlation < 0.99`
- First divergence detected in trace comparison
- Configuration parity violation (wrong convention, non-square pixels, etc.)
- Missing required artifacts

**Blocked/Skip conditions:**
- Golden data inaccessible and no local mirror (document mitigation plan)
- Required `nanobrag_torch` API unavailable (e.g., debug_config.trace_pixel not implemented)

## 3. DB-AT-002: Determinism Validation

### 3.1 Test Objectives

Validate that the PyTorch simulator produces bitwise-reproducible outputs under fixed RNG seeds and statistically independent outputs under different seeds.

**Exit Criteria:**
- Same-seed runs: Bitwise equality (`np.array_equal(img1, img2) == True`)
- Same-seed runs: Correlation ≥ 0.9999999
- Different-seed runs: Correlation ≤ 0.7 (low correlation, proving independence)
- Different-seed runs: ≥50% of non-zero pixels differ

### 3.2 Environment Configuration

**Required Environment Variables:**

```bash
export CUDA_VISIBLE_DEVICES=''           # Force CPU-only (avoid CUDA non-determinism)
export TORCHDYNAMO_DISABLE=1             # Disable TorchDynamo (prevents device query crash)
export NANOBRAGG_DISABLE_COMPILE=1       # Disable torch.compile in simulator
export KMP_DUPLICATE_LIB_OK=TRUE         # Avoid MKL conflicts
```

**Rationale** (per `docs/development/testing_strategy.md:2.7.2`):
- `CUDA_VISIBLE_DEVICES=''`: GPU operations introduce non-deterministic atomics/reductions; CPU execution guarantees bitwise reproducibility
- `TORCHDYNAMO_DISABLE=1`: Prevents TorchDynamo/Triton device query crash when CUDA_VISIBLE_DEVICES is empty
- `NANOBRAGG_DISABLE_COMPILE=1`: Ensures simulator respects Dynamo disable flag
- Test modules MUST set environment variables at module level before `torch` import

**Canonical Command:**

```bash
CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
  KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_002
```

### 3.3 Test Scenarios

**Scenario 1: Same-Seed Bitwise Reproducibility**

- Run simulator twice with identical seed (e.g., `seed=42`)
- Validate: `np.array_equal(img1, img2) == True`
- Validate: `correlation ≥ 0.9999999`
- Validate: `np.allclose(img1, img2, rtol=1e-7, atol=1e-12)`
- Validate: `max_abs_diff ≤ 1e-10` (float64)

**Scenario 2: Different-Seed Statistical Independence**

- Run simulator twice with different seeds (e.g., `seed=42` vs `seed=123`)
- Validate: `np.array_equal(img1, img2) == False` (must differ)
- Validate: `correlation ≤ 0.7` (low correlation)
- Validate: ≥50% of non-zero pixels differ

**Scenario 3: Platform Fingerprint Consistency**

- Record platform metadata (Python version, PyTorch version, CPU model)
- Store fingerprint in `env.json` artifact
- Future runs on same platform MUST reproduce bitwise-identical outputs

### 3.4 Metrics Computation

All DB-AT-002 test runs MUST compute and report:

**Same-Seed Metrics:**
- `bitwise_equal` (bool): Result of `np.array_equal(img1, img2)`
- `correlation` (float): Should be ≥ 0.9999999
- `max_abs_diff` (float): Should be ≤ 1e-10 for float64
- `allclose_passed` (bool): Result of `np.allclose(img1, img2, rtol=1e-7, atol=1e-12)`

**Different-Seed Metrics:**
- `bitwise_equal` (bool): Should be False
- `correlation` (float): Should be ≤ 0.7
- `percent_pixels_differ` (float): Percentage of non-zero pixels that differ (should be ≥50%)

**Required Metadata:**
- `test_id` (string): "DB-AT-002"
- `scenario` (string): "same_seed" or "diff_seed"
- `timestamp` (string): ISO 8601 timestamp
- `seed1` (int): First RNG seed
- `seed2` (int): Second RNG seed (for diff-seed scenario)
- `dtype` (string): "float64" (required for determinism)
- `device` (string): "cpu" (required per environment constraints)
- `threshold_met` (bool): True if all validations pass for scenario
- `platform_fingerprint` (dict): Python/PyTorch/CPU metadata

### 3.5 RNG Seed Propagation

Per `docs/architecture.md` ADR-05 and `docs/spec-db-runtime.md` §5.3:

**Seed Contract:**
- Simulator MUST accept explicit `seed` parameter (int or None)
- Seed MUST propagate to all stochastic operations (mosaic rotation, Poisson noise)
- Implementation MUST use deterministic LCG (C-compatible, per `src/nanobrag_torch/utils/c_random.py`)

**Test Fixture Requirements:**
- Provide `locked_seed` fixture that sets deterministic seed and validates propagation
- Validate LCG bitstream parity against C reference implementation (if available)

### 3.6 Artifact Layout

All DB-AT-002 test runs MUST produce artifacts under:

```
plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/determinism/
```

**Required Artifacts:**
- `metrics_same_seed.json` — Metrics for same-seed scenario
- `metrics_diff_seed.json` — Metrics for different-seed scenario
- `env.json` — Platform fingerprint (Python/PyTorch/CPU versions)
- `summary.md` — Human-readable summary with scenario results
- `commands.txt` — Exact reproduction commands

**Optional Artifacts:**
- `diff_heatmap_diff_seed.png` — Visual diff for different-seed run (should show significant differences)
- `histogram_same_seed.png` — Histogram of pixel differences for same-seed (should be near-zero)

### 3.7 Pass/Fail Criteria

**PASS conditions (Same-Seed):**
- `bitwise_equal == True`
- `correlation ≥ 0.9999999`
- `allclose_passed == True`
- `max_abs_diff ≤ 1e-10` (float64)

**PASS conditions (Different-Seed):**
- `bitwise_equal == False`
- `correlation ≤ 0.7`
- `percent_pixels_differ ≥ 50%`

**FAIL conditions:**
- Any PASS condition violated
- Environment variables not set correctly (test module MUST validate)
- Non-CPU execution detected

**Blocked/Skip conditions:**
- CUDA device forced when CPU-only required (test should error, not skip)
- Required seed propagation API unavailable (document in fix plan)

## 4. Artifact Policy (Cross-Test)

### 4.1 Directory Structure

All parity harness runs MUST use the following directory structure:

```
plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/
├── parity/                           # DB-AT-001 artifacts
│   ├── metrics.json
│   ├── golden_trace_panel{p}_s{s}_f{f}.log
│   ├── py_trace_panel{p}_s{s}_f{f}.log
│   ├── diff_heatmap_panel{p}.png
│   └── summary.md
├── determinism/                      # DB-AT-002 artifacts
│   ├── metrics_same_seed.json
│   ├── metrics_diff_seed.json
│   ├── env.json
│   ├── summary.md
│   └── commands.txt
└── pytest.log                        # Pytest execution log (shared)
```

### 4.2 Artifact Capture Macro

Use the following shell macro to create artifact directories and capture environment metadata:

```bash
# Set artifact root
export ART=plans/active/<initiative-id>/reports/$(date -u +%FT%TZ)

# Create subdirectories
mkdir -p "$ART/parity" "$ART/determinism"

# Capture environment
echo "Python: $(python -V)" > "$ART/env.txt"
pip show torch | grep Version >> "$ART/env.txt"
lscpu | head -n1 >> "$ART/env.txt"
grep MemTotal /proc/meminfo >> "$ART/env.txt"
```

### 4.3 Metrics JSON Schema

All `metrics.json` files MUST conform to the following JSON schema:

```json
{
  "test_id": "string (DB-AT-001, DB-AT-002, etc.)",
  "timestamp": "string (ISO 8601)",
  "golden_path": "string (path to golden reference, or null for DB-AT-002)",
  "py_output_path": "string (path to PyTorch output)",
  "correlation": "float [0,1]",
  "mse": "float ≥0",
  "rmse": "float ≥0",
  "max_abs_diff": "float ≥0",
  "sum_ratio": "float (py_sum / golden_sum, near 1.0 for parity)",
  "golden_sum": "float (or null for DB-AT-002)",
  "py_sum": "float",
  "n_pixels": "int",
  "dtype": "string (e.g., 'float64')",
  "device": "string (e.g., 'cpu', 'cuda:0')",
  "threshold_met": "bool",
  "spec_threshold": "float (e.g., 0.99 for DB-AT-001)",

  "_optional": {
    "ssim": "float [0,1]",
    "mean_intensity_golden": "float",
    "mean_intensity_py": "float",
    "runtime_s": "float",
    "hardware": "string",
    "python_version": "string",
    "torch_version": "string",
    "n_panels": "int",
    "target_shape": "array of int",
    "notes": "string"
  }
}
```

### 4.4 Fix Plan Integration

Every parity harness run MUST update `docs/fix_plan.md` Attempts History with:

**Required Lines:**
- `Metrics:` — Summary of key metrics (correlation, MSE, RMSE, max|Δ|, threshold status)
- `Artifacts:` — Path to artifact directory
- `First Divergence:` — Checkpoint name and delta (if trace comparison failed, else "n/a")
- `Next Actions:` — Follow-up tasks or closure statement

**Example Entry:**

```
* 2025-10-29T001027Z — Implemented DB-AT-001 parity harness with golden data comparison.
  Metrics: correlation=0.9912, MSE=1.23e-4, RMSE=1.11e-2, max|Δ|=0.05, threshold_met=True.
  Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/.
  First Divergence: n/a.
  Next Actions: DB-AT-002 determinism harness; document correlation helper in conftest.py.
```

## 5. Cross-Document Synchronization

### 5.1 Required Documentation Updates

When authoring or updating parity harnesses, the following documents MUST remain synchronized:

**Primary Spec Documents:**
- `docs/spec-db-conformance.md` — Normative acceptance test definitions
- `docs/parity_harness_spec.md` — This document (normative harness requirements)

**Testing Guidance:**
- `docs/TESTING_GUIDE.md` §2 — Test taxonomy with selectors and commands
- `docs/development/TEST_SUITE_INDEX.md` — Selector registry with status and spec references
- `docs/development/testing_strategy.md` — Testing philosophy and detailed workflows

**Discovery & Navigation:**
- `docs/index.md` — Add reference to parity_harness_spec.md
- `docs/prompt_sources_map.json` — Include parity_harness_spec.md in sources

### 5.2 Synchronization Checklist

Before marking parity harness work complete, validate:

- [ ] `docs/spec-db-conformance.md` thresholds match `parity_harness_spec.md` §2.1, §3.1
- [ ] `docs/TESTING_GUIDE.md` §2 selectors match canonical commands in §2.4, §3.2
- [ ] `docs/development/TEST_SUITE_INDEX.md` entries reference this spec
- [ ] `docs/index.md` includes parity_harness_spec.md with keywords and usage guidance
- [ ] `docs/prompt_sources_map.json` lists parity_harness_spec.md
- [ ] All environment flags in this spec match `docs/TESTING_GUIDE.md` §1

## 6. Known Gaps & Future Work

### 6.1 Tooling Gaps (from Phase A audit)

The following helper utilities are required but not yet implemented:

1. **Correlation computation helper** — `compute_parity_metrics()` function (§2.5)
2. **Trace capture integration** — Fixture using `nanobrag_torch` debug_config
3. **Diff heatmap generator** — Matplotlib-based visualization helper
4. **Golden data loader** — Fixture with checksum validation
5. **Metrics JSON writer** — Standardized output helper

**Mitigation:** Document these as sub-tasks in Phase C of implementation plan. Author helpers incrementally as tests are implemented.

### 6.2 Golden Data Accessibility

**Current Status:** `nanoBragg2/tests/golden_data/` path referenced but accessibility in DBEX context unverified.

**Mitigation Options:**
1. Verify path accessibility during first DB-AT-001 test run
2. Create DBEX-local mirror under `tests/fixtures/golden_data/` if needed
3. Document golden data generation procedure in `docs/development/golden_data_generation.md` (future)

### 6.3 Platform-Specific Determinism

**Current Scope:** DB-AT-002 enforces CPU-only execution to avoid CUDA non-determinism.

**Future Work:**
- Re-enable CUDA execution after upstream TorchDynamo fix
- Validate GPU determinism with `torch.cuda.manual_seed_all()` and CuDNN deterministic mode
- Extend platform fingerprint to include GPU model and driver version

## 7. References (Normative)

- `docs/spec-db-conformance.md:10-48` — Acceptance test definitions
- `docs/spec-db-core.md:24,43,51` — Data contracts (tensor ordering, pixel pitch, mask polarity)
- `docs/spec-db-runtime.md:18-21` — Runtime guardrails
- `docs/spec-db-tracing.md:10-26` — Tracing workflow requirements
- `docs/development/testing_strategy.md:1-451` — Testing philosophy and parity workflows
- `docs/development/c_to_pytorch_config_map.md` — Configuration parity requirements
- `docs/TESTING_GUIDE.md:1-91` — Environment flags and test taxonomy
- `docs/pytorch_runtime_checklist.md:26,31` — Runtime checklist items
- `docs/architecture.md` ADR-05 — Deterministic sampling and seeds
- `docs/findings.md` — Knowledge base (CONFORMANCE-001, RUNTIME-001)

## 8. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-29 | Initial normative specification for DB-AT-001 and DB-AT-002 harnesses |
