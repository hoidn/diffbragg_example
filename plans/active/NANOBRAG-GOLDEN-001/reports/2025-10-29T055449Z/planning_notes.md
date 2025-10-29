# NANOBRAG-GOLDEN-001 Planning Notes — 2025-10-29T055449Z

## Context Refresh
- Fallback dataset `simple_cubic_fallback` still present under `tests/fixtures/golden_data/simple_cubic/manifest.json`; exit criteria unmet.
- Latest execution loop (2025-10-29T030352Z) captured DiffBragg refinement logs but `GPUassert: invalid argument diffBraggCUDA.cu:708` prevented exporting `bragg_diffbragg.npy`.
- Environment Freeze policy prohibits additional package installs; prior env rebuild steps in `input.md` are no longer compliant.

## Dependency Check
- Prerequisites `TORCH-BRIDGE-001`, `FORWARD-EQUIV-001`, and `PARITY-HARNESS-002` remain `done` (per docs/fix_plan.md), so focus stays on canonical dataset capture.

## Findings Alignment
- `CONFIG-001` and `CONFORMANCE-001` guard geometry + acceptance thresholds; any workaround must keep selectors `DB_AT_001` collecting >0 tests.
- `TESTING-003` requires fresh collect-only logs whenever selector artifacts shift; current evidence from 2025-10-29T030352Z remains valid but will need refresh after canonical tensors land.

## Rescope Drivers
- Environment rebuild steps (pip/mamba) conflict with Environment Freeze; upcoming Do Now must focus on analysing the DiffBragg CUDA failure and assessing CPU fallback viability inside existing env.
- Goal is to unblock Phase A2 (DiffBragg baseline export) without mutating toolchain: inspect `simtbx/diffBragg/src/diffBraggCUDA.cu` around line 708, cross-reference torch bridge inputs, and stage a CPU capture path if GPU cannot be validated.

## Proposed Next Actions
1. Source inspection + log correlation for `diffBraggCUDA.cu:708` to identify argument assumptions violated during `run_diffbragg` export.
2. Attempt CPU export (`devId=-1`) using existing `scratch/capture_diffbragg.py` harness, recording outcomes under a new report directory for traceability.
3. Refresh `input.md` Do Now with Environment Freeze-compliant steps (analysis first, CPU fallback second, diagnostics third) and update ledger attempt entry accordingly.


## Preliminary Observation
- `../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu:708` wraps `cudaFree(cp.cu_sourceI_scale)` in `gpuErr(...)`; the invalid-argument assert suggests the pointer was never allocated or was freed earlier, pointing to lifecycle tracking mismatches for source intensity scalars during export.
