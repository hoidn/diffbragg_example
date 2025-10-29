# NANOBRAG-GOLDEN-001 Blocking Summary (2025-10-29T070359Z)

## Status: BLOCKED

## Root Cause
DiffBragg `diffBragg_forward` standalone forward pass fails with CUDA assertion at `diffBraggCUDA.cu:708` on BOTH CPU (devId=-1) and GPU (devId=0) modes. This is a simtbx C++/CUDA cleanup bug affecting `cudaFree()` calls on unallocated/double-freed pointers.

## Evidence
- **Prior attempt log**: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/logs/canonical_capture.log`
- **Excerpt**: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/logs/diffbragg_forward_excerpt.log`
- **Error signature**: `GPUassert: invalid argument diffBraggCUDA.cu:708`

## Impact on Canonical Dataset Generation
The canonical golden dataset requires **full-panel** `[panel, slow, fast]` Bragg tensors from both DiffBragg and nanobrag_torch for paired comparison per:
- `docs/spec-db-core.md:20-41` (tensor contracts)
- `docs/forward_equivalence.md:21-52` (exit criteria)
- `plans/nanobrag_integration_plan.md:32-73` (Phase 1 deliverables)

### What Works
- `dbex.refine_one` successfully produces **ROI-level** output stored in HDF5 format during refinement (92 ROIs × 12×12 pixels)
- Example: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5`

### What's Blocked
- Full-panel DiffBragg baseline export (no `bragg_diffbragg.npy` array produced)
- Paired DiffBragg/torch metrics (correlation, MSE, RMSE, max|Δ|, sum ratios)
- Canonical dataset manifest creation pointing to validated full-panel tensors

## Attempted Workarounds
1. ✗ CPU fallback (devId=-1): Same CUDA error persists
2. ✗ GPU mode (devId=0): Same CUDA error persists
3. ✓ `dbex.refine_one` workaround: Works but produces ROI-level, not full-panel output
4. ✗ Standalone `diffBragg_forward` after refinement: Reliably triggers the bug

## Environment Freeze Constraint
Per `CLAUDE.md` and `docs/index.md:8`, the runtime is **pre-provisioned** and MUST NOT be modified during loops. The simtbx C++/CUDA bug cannot be patched without violating this policy.

## Return Conditions
1. **External simtbx patch**: Upstream fix to diffBraggCUDA.cu:708 cleanup logic
2. **Plan revision**: Accept ROI-level parity instead of full-panel comparison
3. **Decoupled capture**: Generate torch tensors independently and defer DiffBragg baseline requirement

## Applied Findings
- DIFFBRAGG-001 (docs/findings.md:15): Documents this C++/CUDA bug and ROI-level workaround
- CONFORMANCE-001 (docs/findings.md:7): DB_AT_001 acceptance thresholds remain documented during block
- TESTING-003 (docs/findings.md:13): Selector evidence must stay current when adjusting ledger status

## References
- Implementation plan: `plans/active/NANOBRAG-GOLDEN-001/implementation.md`
- Prior blocker documentation: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/blocking_summary.md`
- Finding ledger: `docs/findings.md:15` (DIFFBRAGG-001)
- Fix plan ledger: `docs/fix_plan.md:15-36`
