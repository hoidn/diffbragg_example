# GPU Memory Profile — PERF-GPU-MEM-001 Phase A

**Generated:** 2025-12-08 14:46:21
**Duration:** 10.21s
**Status:** OOM during reconstruction

## Configuration

| Parameter | Value |
|-----------|-------|
| Detector size | small |
| Detector shape | (1024, 1024) |
| Total pixels | 1,048,576 |
| Number of ROIs | 29 |
| Mosaic domains | 9 (default) |
| Query batch size (B) | 9,437,184 |
| GPU | NVIDIA GeForce RTX 3090 |
| GPU VRAM | 25.30 GB |

## Memory Timeline

| Checkpoint | Allocated (GB) | Peak (GB) | Time (s) |
|------------|---------------:|----------:|---------:|
| init_clean | 0.000 | 0.000 | 0.10 |
| after_data_load | 0.000 | 0.000 | 0.39 |
| after_prepare_inputs | 0.000 | 0.000 | 0.41 |
| after_hkl_grid_build | 0.002 | 0.003 | 2.24 |
| after_build_context | 0.002 | 0.003 | 2.24 |
| before_engine_run | 0.002 | 0.003 | 2.24 |
| **oom_occurred** | **16.434** | **23.842** | 10.21 |
| final | 0.019 | 23.842 | 10.21 |

## OOM Details

**Error:** `CUDA out of memory. Tried to allocate 4.50 GiB.`

**Memory at OOM:**
- Allocated by PyTorch: 15.31 GiB
- Reserved by PyTorch: 20.04 GiB
- Failed allocation: 4.50 GiB

## Tricubic Interpolation Memory Analysis

The OOM occurs in `Crystal._tricubic_interpolation()` at `nanobrag_torch/models/crystal.py:404`.

### Query Batch Size Calculation

```
B = num_pixels × mosaic_domains × (phi_steps if rotation else 1)
B = 1,024 × 1,024 × 9 = 9,437,184
```

This matches the HKL stats log: `hit_rate=9279293/9437184 (98.33%)`

### Memory Breakdown by Component

| Component | Size Formula | Actual Size | Notes |
|-----------|-------------|-------------|-------|
| HKL grid | 51×59×64×4 | 0.77 MB | Negligible |
| h_grid_coords | B × 4 × 8 bytes | 287 MB | (B, 4) long tensor |
| k_grid_coords | B × 4 × 8 bytes | 287 MB | (B, 4) long tensor |
| l_grid_coords | B × 4 × 8 bytes | 287 MB | (B, 4) long tensor |
| h_array_grid | B × 4 × 8 bytes | 287 MB | Array indices |
| k_array_grid | B × 4 × 8 bytes | 287 MB | Array indices |
| l_array_grid | B × 4 × 8 bytes | 287 MB | Array indices |
| **sub_Fhkl** | B × 4 × 4 × 4 × 4 | **2.38 GB** | (B, 4, 4, 4) float32 |
| h_indices (float) | B × 4 × 4 bytes | 144 MB | For polin3 |
| k_indices (float) | B × 4 × 4 bytes | 144 MB | For polin3 |
| l_indices (float) | B × 4 × 4 bytes | 144 MB | For polin3 |
| **Subtotal** | - | **~4.5 GB** | Single pass |

### Autograd Overhead

With `requires_grad=True`, PyTorch stores:
- Forward pass intermediates for backward
- Gradient buffers

**Estimated total:** 4.5 GB × 2-3× = **~10-14 GB**

### Additional Allocations

During full reconstruction:
- Output tensor: B × 4 bytes = 36 MB
- Polynomial evaluation intermediates: ~2-4 GB
- PyTorch memory fragmentation: ~2-4 GB

**Total estimated:** ~16-23 GB (matches observed peak)

## Root Cause

The tricubic interpolation batches ALL query points at once:

```python
# nanobrag_torch/models/crystal.py:401-405
h_grid_coords = h_flr_flat.unsqueeze(-1) + offsets  # (B, 4) where B=9.4M
k_grid_coords = k_flr_flat.unsqueeze(-1) + offsets  # (B, 4)
l_grid_coords = l_flr_flat.unsqueeze(-1) + offsets  # (B, 4)

# Line 427-431: Advanced indexing creates (B, 4, 4, 4) = 603M floats = 2.4 GB
sub_Fhkl = self.hkl_data[
    h_array_grid[:, :, None, None],  # (B, 4, 1, 1)
    k_array_grid[:, None, :, None],  # (B, 1, 4, 1)
    l_array_grid[:, None, None, :]   # (B, 1, 1, 4)
]
```

## Scaling Analysis

| Detector | Pixels | B (9 domains) | sub_Fhkl | Est. Peak |
|----------|--------|--------------|----------|-----------|
| small (1024²) | 1.05M | 9.4M | 2.4 GB | ~23 GB |
| full (2463×2527) | 6.2M | 56M | **14.3 GB** | >50 GB |

The full detector would require ~50+ GB, far exceeding 24 GB GPUs.

## Recommendations

### Phase C.1: Chunked Interpolation (Highest Impact)

Process query points in chunks of 100K instead of 9.4M at once:

```python
chunk_size = 100_000  # ~100KB per coordinate grid
for i in range(0, B, chunk_size):
    chunk_h = h_flat[i:i+chunk_size]
    chunk_k = k_flat[i:i+chunk_size]
    chunk_l = l_flat[i:i+chunk_size]
    result[i:i+chunk_size] = _interpolate_chunk(chunk_h, chunk_k, chunk_l)
```

**Expected reduction:** 94× peak memory (from 2.4 GB to ~25 MB per chunk)

### Phase C.2: Lazy Neighborhood Allocation

Build sub_Fhkl incrementally per chunk rather than pre-allocating full (B, 4, 4, 4).

### Phase C.3: Panel-by-Panel Reconstruction

For multi-panel detectors, process one panel at a time.

### Phase C.4: CPU Fallback

For very large reconstructions, offload to CPU when GPU memory is insufficient.

## Files Referenced

- OOM source: `nanobrag_torch/models/crystal.py:404`
- Tricubic implementation: `nanobrag_torch/models/crystal.py:350-500`
- Simulator run: `nanobrag_torch/simulator.py:771-870`

## Artifacts

- `memory_metrics.json` — Raw profiling data
- `memory_profile.md` — This report
