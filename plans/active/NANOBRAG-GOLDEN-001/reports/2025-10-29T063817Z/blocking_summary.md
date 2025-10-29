# NANOBRAG-GOLDEN-001 Blocking Summary (2025-10-29T063817Z)

## Status: BLOCKED - diffBragg_forward CUDA bug prevents full-panel baseline capture

## Blocker Description

The canonical capture plan (input.md lines 20-432) requires paired full-panel `[panel,slow,fast]` tensors from both DiffBragg and nanobrag_torch. However, attempts to capture a full-panel DiffBragg baseline hit the CUDA bug documented in **DIFFBRAGG-001** (docs/findings.md:15).

### Root Cause

`simtbx.modeling.forward_models.diffBragg_forward` reliably triggers `GPUassert: invalid argument diffBraggCUDA.cu:708` on both CPU (devId=-1) and GPU (devId=0) modes when called as a standalone forward pass after refinement.

The simtbx C++/CUDA cleanup code attempts to `cudaFree()` pointers that were never allocated or were already freed, causing the assertion failure.

### Evidence

1. **Capture script attempt**: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_forward.py`
   Invokes the refinement loop (5 macro cycles) followed by `diffBragg_forward` to generate full-panel Bragg tensor.
   **Result**: CUDA assertion at line 708 (see `golden_dataset/logs/canonical_capture.log`).

2. **HDF5 inspection**: `dbex.refine_one` successfully completes refinement and writes `dbex_diffbragg_gpu.h5`.
   **However**: The HDF5 file stores ROI-level data only (92 ROIs, each 12×12 pixels) under `/bragg/roi{0..91}`, NOT a full [panel,slow,fast] tensor.
   The CLI never calls `diffBragg_forward` as a standalone function after refinement, so it sidesteps the bug.

3. **Prior successful run**: 2025-10-29T032100Z used `dbex.refine_one` directly, which wrote HDF5 with ROI-level Bragg data. No full-panel tensor was ever generated.

### Implications

- **Cannot generate full-panel DiffBragg baseline** without patching simtbx C++/CUDA source.
- The input.md script (lines 20-432) assumes `diffBragg_forward` will succeed, but this is not achievable given DIFFBRAGG-001.
- ROI-level comparison is feasible (DiffBragg HDF5 ROIs vs torch full-panel ROIs), but this diverges from the plan's expectation of paired full-panel tensors.

## Attempted Workarounds

| Approach | devId | Result |
|---|---|---|
| Custom capture script (capture_forward.py) | 0 (GPU) | CUDA assertion at line 708 |
| dbex.run_diffbragg function | 0 (GPU) | CUDA assertion at line 708 (see prior loop 2025-10-29T055449Z) |
| dbex.refine_one CLI | 0 (GPU) | Success, but emits ROI-level data only (no full-panel tensor) |

## Next Actions

1. **Escalate to supervisor**: Clarify whether:
   - ROI-level parity (DiffBragg HDF5 ROIs vs torch full-panel ROIs) is acceptable for NANOBRAG-GOLDEN-001.
   - Full-panel baseline requirement can be relaxed, OR
   - simtbx C++/CUDA patch is required (external dependency, violates Environment Freeze).

2. **Alternative path (if ROI-level acceptable)**:
   - Keep `dbex_diffbragg_gpu.h5` (ROI-level DiffBragg data).
   - Run torch full-panel forward simulator.
   - Extract ROI regions from torch tensor matching HDF5 ROI bboxes.
   - Compute parity metrics on ROI overlap only.
   - Document in manifest that DiffBragg baseline is ROI-level, not full-panel.

3. **Update findings**: Extend DIFFBRAGG-001 to note that `diffBragg_forward` fails on BOTH CPU and GPU when called standalone after refinement, and that `dbex.refine_one` avoids the bug by never calling it.

## Artifacts

- `golden_dataset/logs/canonical_capture.log` — Full capture script output showing CUDA assertion.
- `golden_dataset/logs/diffbragg_refine_one.log` — Successful refine_one run (ROI-level output).
- `golden_dataset/legacy/dbex_diffbragg_gpu.h5` — ROI-level HDF5 (92 ROIs, 12×12 each).
- `capture_forward.py`, `capture_diffbragg_only.py`, `capture_torch_only.py` — Attempted scripts.

## References

- **DIFFBRAGG-001** (docs/findings.md:15): CPU mode broken at diffBraggCUDA.cu:708, GPU workaround claimed but not validated for standalone forward pass.
- **input.md lines 20-432**: Canonical capture script assuming full-panel DiffBragg tensor.
- **docs/spec-db-core.md:20-41**: `[panel,slow,fast]` contract for golden tensors.
- **dbex/run_diffbragg.py:126-138**: `diffBragg_forward` invocation pattern (same as capture script, but hits CUDA bug).
- **prior loop 2025-10-29T055449Z**: Documented CPU fallback failure and claimed GPU workaround; however, that workaround only applies to `dbex.refine_one` (which doesn't call `diffBragg_forward` standalone).

