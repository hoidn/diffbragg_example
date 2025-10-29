# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T063817Z)

## Status: BLOCKED

The canonical capture attempt per input.md (2025-10-29T063817Z) is blocked by the diffBragg_forward CUDA bug. Full-panel DiffBragg baseline cannot be generated without patching simtbx C++/CUDA source code.

## Tasks Attempted

### A2: DiffBragg Baseline Capture

**Goal**: Capture GPU DiffBragg baseline (`bragg_diffbragg.npy`, `config_diffbragg.json`) using devId=0.

**Actions**:
1. Created `capture_forward.py` combining DiffBragg refinement + standalone forward pass + nanobrag_torch simulator.
2. Executed script with `CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE`.
3. **Result**: Script hit `GPUassert: invalid argument diffBraggCUDA.cu:708` during `diffBragg_forward` call.

**Fallback**:
1. Ran `DIFFBRAGG_USE_CUDA=1 python -m dbex.refine_one` successfully.
2. Generated `dbex_diffbragg_gpu.h5` (564K, 92 ROIs).
3. **Limitation**: HDF5 contains ROI-level data only (`/bragg/roi{0..91}`, each 12×12 pixels), NOT full-panel `[panel,slow,fast]` tensor.

**Root Cause**:
- `diffBragg_forward` standalone forward pass triggers simtbx C++/CUDA bug at diffBraggCUDA.cu:708 on BOTH CPU and GPU.
- `dbex.refine_one` sidesteps bug by storing Bragg data DURING refinement (never calls `diffBragg_forward` standalone).
- Prior finding DIFFBRAGG-001 claimed "GPU workaround works correctly" but this only applies to the CLI, not standalone forward passes.

### A3: nanobrag_torch Simulator (Blocked)

**Goal**: Run nanobrag_torch forward simulator across all panels.

**Status**: Did not execute - blocked by missing full-panel DiffBragg baseline required for paired metrics computation.

### B2: Selector Re-collection (Skipped)

**Goal**: Re-collect DB_AT_001 parity and forward equivalence selectors.

**Status**: Skipped - no new golden tensors generated.

## Artifacts

| File | Description | Status |
|---|---|---|
| `golden_dataset/logs/canonical_capture.log` | Full capture script output showing CUDA assertion | Generated |
| `golden_dataset/logs/diffbragg_refine_one.log` | Successful refine_one run (ROI-level output) | Generated |
| `golden_dataset/legacy/dbex_diffbragg_gpu.h5` | ROI-level HDF5 (92 ROIs, 12×12 each, 564K) | Generated |
| `capture_forward.py` | Combined DiffBragg + torch capture script | Authored, blocked |
| `capture_diffbragg_only.py` | DiffBragg extraction script | Authored, blocked |
| `capture_torch_only.py` | Torch-only simulator script | Authored, not executed |
| `blocking_summary.md` | Detailed blocker analysis with evidence | Generated |

## Metrics

- **DiffBragg refinement**: 1/1 successful (5 macro cycles, F=678151, sigZ=12.27, via `dbex.refine_one`)
- **DiffBragg full-panel forward pass**: 0/1 successful (CUDA bug)
- **nanobrag_torch runs**: 0 (blocked by missing DiffBragg baseline)
- **Selector re-collections**: 0 (skipped)
- **Scripts authored**: 3 (capture_forward.py, capture_diffbragg_only.py, capture_torch_only.py)

## Updated Findings

Extended **DIFFBRAGG-001** (docs/findings.md:15) to clarify:
- Bug affects BOTH CPU and GPU when `diffBragg_forward` is called standalone after refinement.
- "GPU workaround" only applies to `dbex.refine_one` CLI (which never makes standalone forward pass).
- No full-panel baseline achievable without simtbx source patch (violates Environment Freeze).

## Questions for Supervisor

1. **ROI-level parity acceptability**: Is ROI-level comparison (DiffBragg HDF5 ROIs vs torch full-panel ROIs) acceptable for NANOBRAG-GOLDEN-001 exit criteria?
2. **Plan revision**: Should the plan be revised to decouple DiffBragg/torch capture, allowing torch-only full-panel golden dataset + ROI-level DiffBragg reference?
3. **External dependency**: Is a simtbx C++/CUDA patch in scope, or should the initiative remain blocked?

## Recommendations

### Option A: ROI-level Parity (Preferred)

- Accept ROI-level DiffBragg baseline (`dbex_diffbragg_gpu.h5`).
- Generate torch full-panel baseline.
- Extract ROI regions from torch matching HDF5 ROI bboxes.
- Compute parity metrics on ROI overlap only.
- Document in manifest that DiffBragg baseline is ROI-level, not full-panel.

### Option B: Torch-only Golden Dataset

- Skip DiffBragg baseline entirely.
- Generate torch full-panel golden dataset with synthetic validation.
- Defer DiffBragg parity to future work when simtbx bug is fixed.

### Option C: External Patch (Violates Environment Freeze)

- Patch simtbx C++/CUDA source to fix diffBraggCUDA.cu:708 bug.
- Requires external maintainer involvement or forking simtbx.
- Violates Environment Freeze policy.

## Next Actions

- **Status**: blocked
- **Next action**: switch_focus (await supervisor guidance)
- **Rationale**: Cannot proceed with canonical capture plan as written due to simtbx bug; require supervisor decision on ROI-level vs full-panel baseline approach.

