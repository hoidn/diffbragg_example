# Trace Capture Requirements Template

**Version:** 1.0
**Date:** 2025-10-29
**Spec Reference:** `docs/parity_harness_spec.md` §2.6

## Purpose

This template defines the normative requirements for per-pixel trace capture in DB-AT parity debugging workflows per `docs/spec-db-tracing.md:10-26`.

## Trace Naming Convention

**Golden trace:**
`golden_trace_panel{p}_s{s}_f{f}.log`

**PyTorch trace:**
`py_trace_panel{p}_s{s}_f{f}.log`

**Example:**
- `golden_trace_panel0_s1200_f1000.log`
- `py_trace_panel0_s1200_f1000.log`

## Required Trace Checkpoints

Per `docs/development/testing_strategy.md:117`, all trace logs MUST include the following 20+ checkpoints:

### Geometry Checkpoints
- `pix0_vector` — Detector pixel origin in lab frame (meters)
- `basis_vectors` — Detector fast/slow basis vectors (meters)
- `R` — Sample-to-pixel distance (meters)
- `solid_angle` — Point-pixel solid angle (steradians)
- `obliquity_factor` — Obliquity correction factor (dimensionless)
- `pixel_area` — Pixel area (meters²)

### Wave Vectors & Scattering
- `k_in` — Incident beam wave vector (Å⁻¹)
- `k_out` — Scattered wave vector (Å⁻¹)
- `S` — Scattering vector (Å⁻¹)

### Miller Indices & Structure Factors
- `miller_indices_float` — (h, k, l) as floats (dimensionless)
- `miller_indices_rounded` — (h, k, l) as integers (dimensionless)
- `F` — Structure factor (electrons)
- `F_squared` — |F|² (electrons²)

### Lattice Factors
- `F_latt_a` — Lattice factor along a-axis (dimensionless)
- `F_latt_b` — Lattice factor along b-axis (dimensionless)
- `F_latt_c` — Lattice factor along c-axis (dimensionless)
- `F_latt_product` — F_latt_a × F_latt_b × F_latt_c (dimensionless)
- `F_latt_squared` — |F_latt|² (dimensionless)

### Intensity Computation
- `omega_solid_angle` — Solid angle with obliquity correction (steradians)
- `fluence` — Incident photon fluence (photons/Ų)
- `final_intensity` — Computed pixel intensity (photons or ADU)

## Format Requirements

**Precision:** float64 for determinism
**Units:**
- Geometry: meters
- Solid angle: steradians
- Wavelength: Ångströms (Å)
- Wave vectors: Å⁻¹

**Structure:** JSON or line-delimited key-value pairs

**Example JSON Format:**
```json
{
  "panel": 0,
  "slow": 1200,
  "fast": 1000,
  "checkpoints": {
    "pix0_vector": [0.152, -0.045, 0.200],
    "basis_vectors": {
      "fast": [0.000172, 0.0, 0.0],
      "slow": [0.0, 0.000172, 0.0]
    },
    "R": 0.2145,
    "solid_angle": 6.567e-8,
    "obliquity_factor": 0.9342,
    "k_in": [0.0, 0.0, 6.283],
    "k_out": [0.512, -0.156, 6.245],
    "S": [0.512, -0.156, -0.038],
    "miller_indices_float": [4.02, -1.23, -0.30],
    "miller_indices_rounded": [4, -1, 0],
    "F": 23.45,
    "F_squared": 549.9,
    "F_latt_a": 0.856,
    "F_latt_b": 0.923,
    "F_latt_c": 0.991,
    "F_latt_product": 0.783,
    "F_latt_squared": 0.613,
    "omega_solid_angle": 6.136e-8,
    "pixel_area": 2.96e-8,
    "fluence": 1.23e12,
    "final_intensity": 456.78
  }
}
```

## Pixel Selection Strategy

Per `docs/parity_harness_spec.md` §2.6:

1. Choose a strong on-peak pixel near beam center
2. Prefer pixels with high intensity in golden data (top 10th percentile)
3. Document exact `(panel, slow, fast)` indices in trace filename
4. Use same pixel for both golden and PyTorch traces

## First Divergence Workflow

Per `docs/spec-db-tracing.md:15-26`:

1. Generate golden trace for selected pixel
2. Generate PyTorch trace for same pixel with identical inputs
3. Compare traces line-by-line (checkpoint-by-checkpoint)
4. Identify first checkpoint where values differ beyond float64 tolerance
5. Document first divergence in `parity/summary.md`:
   - Checkpoint name
   - Golden value
   - PyTorch value
   - Absolute delta
   - Relative delta (if applicable)

## Artifact Storage

Per `docs/parity_harness_spec.md` §4.1:

**Location:**
`plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/parity/`

**Files:**
- `golden_trace_panel{p}_s{s}_f{f}.log`
- `py_trace_panel{p}_s{s}_f{f}.log`
- `summary.md` (with first divergence notes)

## Integration with nanobrag_torch

**API Reference:** `docs/nanobrag_api.md` (debug_config)

**Expected Usage:**
```python
from nanobrag_torch import Simulator, DebugConfig

debug_config = DebugConfig(
    trace_pixel=(panel_idx, slow_idx, fast_idx),
    trace_output_path="py_trace_panel0_s1200_f1000.log"
)

simulator = Simulator(detector_config, beam_config, crystal_config)
output, trace = simulator.run(debug_config=debug_config)
```

**Note:** Actual API may differ; consult `nanobrag_torch` documentation when available.

## References

- `docs/parity_harness_spec.md` §2.6 — Trace capture workflow
- `docs/spec-db-tracing.md:10-26` — Normative tracing requirements
- `docs/development/testing_strategy.md:117` — Required trace checkpoint list
- `docs/nanobrag_api.md` — debug_config API (when available)
