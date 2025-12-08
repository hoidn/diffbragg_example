# PERF-GPU-MEM-001 — GPU Memory Usage Analysis and Optimization

## Initiative
- ID: PERF-GPU-MEM-001
- Title: GPU Memory Usage Analysis and Optimization
- Owner: Galph / Ralph
- Spec Owner: docs/spec-db-runtime.md
- Status: pending

## Goals
1. Profile and document GPU memory allocation breakdown during Stage A/B/C refinement and reconstruction
2. Identify the largest memory consumers (tricubic interpolation, mosaic domain sampling, panel reconstruction)
3. Propose and implement memory reduction strategies (chunking, CPU offload, lazy allocation)
4. Enable full Stage A smoke tests to complete without OOM on 24GB GPUs

## Background

The Stage A smoke test (`test_stage_a_expansion`) hits CUDA OOM during the reconstruction phase:
```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 4.50 GiB.
GPU 0 has a total capacity of 23.56 GiB of which 3.44 GiB is free.
```

The OOM occurs at `nanobrag_torch/models/crystal.py:404` during tricubic interpolation's batched neighborhood gather:
```python
k_grid_coords = k_flr_flat.unsqueeze(-1) + offsets  # (B, 4)
```

This indicates the tricubic interpolation is creating large intermediate tensors when processing full-panel reconstructions.

## Phases Overview
- Phase A — Profiling: Instrument memory usage at key points; identify breakdown by component
- Phase B — Analysis: Document memory scaling laws; identify optimization candidates
- Phase C — Optimization: Implement memory reduction strategies; validate on 24GB GPU
- Phase D — Validation: Run full smoke tests; update runtime checklist

## Exit Criteria
1. Memory profiling report documents allocation breakdown for Stage A/B/C (by component: HKL grid, mosaic domains, panel simulation, tricubic interpolation)
2. At least one optimization reduces peak GPU memory by ≥30% for small-detector reconstruction
3. Stage A smoke test (`test_stage_a_expansion --smoke-detector-size=small`) completes without OOM on 24GB GPU
4. Test registry synchronized: `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` updated if new selectors added

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `spec-db-runtime.md §Device/Dtype Neutrality` — Optimizations must maintain device agnosticism
- [ ] **Spec Constraint:** `docs/pytorch_runtime_checklist.md §Vectorization` — Must not break vectorization patterns
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [TORCH-REFINE-CLEANUP-001]` — Documents OOM as env constraint
- [ ] **Finding/Policy ID:** `RUNTIME-001` (Runtime execution guardrails)

## Spec Alignment
- **Normative Spec:** docs/spec-db-runtime.md
- **Key Clauses:**
  - §Device/Dtype Neutrality — Code must work on CPU and CUDA
  - §Vectorization — Batch operations preferred but chunking allowed for memory management

## Architecture / Interfaces

- **Key Data Types:**
  - `Crystal.hkl_grid`: Dense P1 |F| grid (shape: `[h_range, k_range, l_range]`)
  - `Crystal._tricubic_interpolation`: Batched 4x4x4 neighborhood gather
  - `Simulator.run()`: Panel-level forward simulation
  - `build_final_bragg_from_stage_a_telemetry`: Full reconstruction from Stage A results

- **Boundary Definitions:**
  - `[RefinementEngine]` → `[StageA.run()]` → `[Simulator]` → `[Crystal.get_structure_factor()]`
  - Memory-intensive path: `[Reconstruction]` → `[full-panel Simulator.run()]` → `[tricubic interpolation on all pixels]`

- **Data-Flow Notes:**
  - HKL grid: ~4MB for typical crystal (25x24x5 × float32)
  - Tricubic neighborhood: B × 4 × 4 × 4 where B = num_pixels × mosaic_domains
  - For small detector (512×512) with 16 mosaic domains: B ≈ 4M → 256M floats → 1GB per coordinate
  - Three coordinates (h, k, l) → ~3GB just for coordinate grids

## Context Priming (read before edits)
- Primary docs/specs to re-read:
  - `docs/spec-db-runtime.md` §Vectorization, §Device/Dtype Neutrality
  - `docs/pytorch_runtime_checklist.md` §Memory hygiene
  - `nanobrag_torch/models/crystal.py` lines 350-450 (tricubic implementation)
- Required findings/case law:
  - RUNTIME-001 (Runtime execution guardrails)
  - REFINE-007 (Stage C chi² improvement gates)
- Related telemetry/attempts:
  - `plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/pytest_stage_a.log` (OOM evidence)
  - TORCH-REFINE-CLEANUP-001 (documented OOM as env constraint)

---

## Phase A — Profiling

### Checklist
- [ ] A0: **Nucleus:** Create minimal memory profiling probe that tracks GPU allocations during `Simulator.run()`
- [ ] A1: Add `torch.cuda.memory_allocated()` / `torch.cuda.max_memory_allocated()` instrumentation points
- [ ] A2: Profile Stage A closure execution (ROI mode vs panel mode)
- [ ] A3: Profile reconstruction path (`build_final_bragg_from_stage_a_telemetry`)
- [ ] A4: Profile tricubic interpolation specifically (`Crystal._tricubic_interpolation`)
- [ ] A5: Document memory breakdown in `reports/<timestamp>/memory_profile.md`

### Dependency Analysis
- **Touched Modules:** None (instrumentation only, no production code changes in Phase A)
- **Circular Import Risks:** None
- **State Migration:** N/A

### Notes & Risks
- Risk: Profiling overhead may affect timing measurements
- Mitigation: Use minimal instrumentation; separate memory profiling from performance benchmarks

---

## Phase B — Analysis

### Checklist
- [ ] B1: Calculate theoretical memory requirements for each component
  - HKL grid: `h_range × k_range × l_range × 4 bytes`
  - Mosaic domains: `n_domains × contribution`
  - Tricubic neighborhood: `B × 4 × 4 × 4 × 4 bytes × 3 coordinates`
- [ ] B2: Identify memory scaling laws (linear vs quadratic in detector size, mosaic domains)
- [ ] B3: Rank components by memory consumption
- [ ] B4: Identify optimization candidates (chunking, streaming, CPU offload)
- [ ] B5: Document analysis in `reports/<timestamp>/memory_analysis.md`

### Notes & Risks
- Risk: Theoretical estimates may differ from actual allocations due to PyTorch memory pooling
- Mitigation: Validate theoretical estimates against Phase A measurements

---

## Phase C — Optimization

### Checklist
- [ ] C1: **Chunked tricubic interpolation:** Process query points in batches instead of all at once
  - Target: Process 100K points per chunk instead of 4M
  - Expected reduction: 40× peak memory for tricubic path
- [ ] C2: **Lazy HKL grid allocation:** Only allocate neighborhoods when needed, not pre-expanded
- [ ] C3: **Panel-by-panel reconstruction:** Process one panel at a time instead of full detector
- [ ] C4: **CPU offload for reconstruction:** Move reconstruction to CPU when GPU memory is insufficient
- [ ] C5: Implement selected optimizations (prioritize by impact/complexity ratio)
- [ ] C6: Validate optimizations don't break existing tests

### Notes & Risks
- Risk: Chunking may introduce numerical differences due to order of operations
- Mitigation: Validate against non-chunked reference implementation with tight tolerances
- Risk: CPU offload may be too slow for production use
- Mitigation: Make offload configurable; document performance tradeoffs

---

## Phase D — Validation

### Checklist
- [ ] D1: Run Stage A smoke test with optimizations enabled
  - `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small`
- [ ] D2: Run partiality tests to ensure physics unchanged
  - `pytest -v tests/architecture/test_nanobrag_partiality.py`
- [ ] D3: Run gradcheck tests to ensure gradient flow preserved
  - `pytest -v tests -k DB_AT_010 --smoke-detector-size=full`
- [ ] D4: Document final memory usage and improvements
- [ ] D5: Update `docs/pytorch_runtime_checklist.md` with memory hygiene guidelines

### Notes & Risks
- Risk: Optimizations may have subtle effects on numerical results
- Mitigation: Run full parity suite before closing

---

## Artifacts Index
- Reports root: `plans/active/PERF-GPU-MEM-001/reports/`
- Memory profile: `<timestamp>/memory_profile.md`
- Analysis: `<timestamp>/memory_analysis.md`
- Optimization benchmarks: `<timestamp>/optimization_results.md`

---

## Appendix: Memory Estimation

### Current Memory Budget (24GB GPU)

| Component | Estimated Size | Notes |
|-----------|---------------|-------|
| HKL grid | ~4 MB | 25×24×5 × float32 |
| Mosaic domains (16) | ~variable | Per-domain orientation tensors |
| Panel simulation (512×512) | ~1 MB | Single panel output |
| Tricubic coordinates (B=4M) | ~3 GB | h,k,l coordinate grids |
| Tricubic neighborhoods (B×64) | ~1 GB | 4×4×4 per query point |
| PyTorch overhead | ~2-4 GB | CUDA context, allocator |
| **Total estimated** | **~8+ GB** | During reconstruction |

### Target After Optimization

| Component | Target Size | Strategy |
|-----------|-------------|----------|
| Tricubic coordinates | ~75 MB | Chunk to 100K at a time |
| Tricubic neighborhoods | ~25 MB | Chunk to 100K at a time |
| **Total target** | **~4 GB** | Fits in remaining GPU memory |
