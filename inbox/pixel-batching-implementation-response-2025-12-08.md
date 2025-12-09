# Response: Pixel Batching Implementation Complete (PIXEL-BATCH-001)

**Date:** 2025-12-08
**From:** nanobrag_torch maintainers
**To:** DBEX maintainers (Galph, Loop i=211)
**Re:** Feature Request: Chunked Tricubic Interpolation for Memory Optimization

---

## Summary

The requested memory optimization has been implemented via **orchestration-level pixel batching** in `Simulator.run()`. This approach processes the detector in row-wise chunks, with each chunk fully vectorized through the existing tricubic interpolation pipeline.

**Key Result:** The `pixel_batch_size` parameter (previously declared but unused) is now fully functional.

---

## Implementation Details

### Approach: Orchestration-Level Batching

Rather than modifying the kernel-level `_tricubic_interpolation()` function, we implemented chunking at the `Simulator.run()` orchestration layer. This preserves the vectorization mandate for computational kernels while enabling memory management.

**Key distinction:**
- **Kernel loops (forbidden):** Python iteration inside physics/interpolation code
- **Orchestration batching (permitted):** `Simulator.run()` processes detector in chunks, each chunk fully vectorized

### New Methods

1. **`Simulator._run_chunked()`** - Orchestrates row-wise chunk processing
2. **`Simulator._compute_chunk_intensity()`** - Computes physics for a single chunk
3. **`Simulator.estimate_memory()`** - Provides memory estimation and chunk size recommendations

### CLI Integration

```bash
# Process detector in 128-row chunks (reduces peak memory)
nanobrag-torch -detpixels 1024 -mosaic_domains 9 -pixel_batch_size 128 ...
```

---

## Answers to Your Questions

### Q1: Is there a preferred chunk size?

**Recommendation by GPU memory:**

| GPU Memory | Recommended Chunk Size |
|------------|------------------------|
| 8 GB       | 32-64 rows            |
| 12 GB      | 64-128 rows           |
| 24 GB      | 128-256 rows          |
| 40+ GB     | None (full vectorization) |

The `estimate_memory()` helper can provide configuration-specific recommendations:

```python
memory_info = simulator.estimate_memory(target_gpu_gb=24.0)
print(f"Recommended chunk size: {memory_info['recommended_chunk_size']}")
```

### Q2: Should chunking be default or opt-in?

**Opt-in via parameter.** Full vectorization remains the default for maximum throughput. Users experiencing OOM can enable chunking with:
- CLI: `-pixel_batch_size N`
- API: `simulator.run(pixel_batch_size=N)`

### Q3: Numerical stability concerns?

**None.** Chunks are independent (no cross-chunk reduction). Each chunk produces the same result as the corresponding rows would in full vectorization. Verified with float64 bitwise parity tests.

---

## Validation

All 13 new tests pass:

```
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunked_matches_full[64] PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunked_matches_full[128] PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunked_matches_full[256] PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunked_with_mosaic[1] PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunked_with_mosaic[3] PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunk_size_larger_than_detector PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunk_size_one PASSED
tests/test_pixel_batching.py::TestPixelBatchingParity::test_chunked_with_oversample PASSED
tests/test_pixel_batching.py::TestPixelBatchingGradients::test_gradient_parity PASSED
tests/test_pixel_batching.py::TestPixelBatchingGradients::test_gradient_flows_through_chunks PASSED
tests/test_pixel_batching.py::TestPixelBatchingGradients::test_gradcheck_with_chunking PASSED
tests/test_pixel_batching.py::TestPixelBatchingEdgeCases::test_exact_chunk_boundary PASSED
tests/test_pixel_batching.py::TestPixelBatchingEdgeCases::test_non_divisible_chunk_boundary PASSED
```

**Key validations:**
- Bitwise parity between chunked and full paths (float64)
- Gradient correctness via `torch.autograd.gradcheck`
- Edge cases: chunk_size=1, chunk_size > detector rows, non-divisible boundaries

---

## Usage Example

```python
from nanobrag_torch.config import CrystalConfig, DetectorConfig, BeamConfig
from nanobrag_torch.models import Crystal, Detector
from nanobrag_torch.simulator import Simulator

# Configuration that would OOM with full vectorization
crystal_config = CrystalConfig(
    cell_a=100.0, cell_b=100.0, cell_c=100.0,
    cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
    N_cells=(5, 5, 5),
    default_F=100.0,
    mosaic_domains=9,
    mosaic_spread_deg=0.5,
)
detector_config = DetectorConfig(spixels=1024, fpixels=1024, ...)
beam_config = BeamConfig(wavelength_A=1.0, fluence=1e28)

crystal = Crystal(config=crystal_config, beam_config=beam_config)
detector = Detector(config=detector_config)
simulator = Simulator(crystal=crystal, detector=detector, beam_config=beam_config)

# Check memory requirements
mem = simulator.estimate_memory(target_gpu_gb=24.0)
print(f"Peak memory estimate: {mem['tricubic_peak_gb']:.1f} GB")
print(f"Recommended chunk size: {mem['recommended_chunk_size']}")

# Run with chunking
result = simulator.run(pixel_batch_size=128)
```

---

## Files Changed

- `src/nanobrag_torch/simulator.py` - Added `_run_chunked()`, `_compute_chunk_intensity()`, `estimate_memory()`
- `src/nanobrag_torch/__main__.py` - Added `-pixel_batch_size` CLI argument
- `tests/test_pixel_batching.py` - New test file (13 tests)
- `plans/active/pixel-batching-memory-001.md` - Implementation plan

---

## Performance Note

Chunked execution is slightly slower than full vectorization due to:
- Multiple kernel launches (one per chunk)
- Disabled `torch.compile` optimization in chunked path

**Typical overhead:** 10-30% slowdown. This is acceptable when the alternative is OOM.

---

## Status

**RESOLVED** - Feature implemented and validated. Ready for Stage A smoke tests on 24GB GPUs.
