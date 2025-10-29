# NANOBRAG-GOLDEN-001 ROI-Level Canonical Dataset Planning (2025-10-29T071728Z)

## Context
- Previous loop (2025-10-29T070359Z) documented diffBraggCUDA.cu:708 cleanup bug blocking full-panel DiffBragg tensor capture.
- Canonical dataset exit criteria still require paired `[panel, slow, fast]` tensors; only ROI-level DiffBragg data exists today (`dbex_diffbragg_gpu.h5`).
- Environment Freeze remains in effect; no simtbx rebuilds or external package installs are permitted this loop.

## Planning Objectives
1. Evaluate whether ROI-level DiffBragg data plus full-panel torch tensors can satisfy spec requirements with updated manifest/test contracts.
2. Inventory the data we already have (ROI bounding boxes, HDF5 schema, existing torch capture scripts) and identify gaps for traceability.
3. Define evidence-gathering steps (A2/A3) that stay within policy while providing enough detail to request either a targeted simtbx patch or a spec amendment.

## Proposed Evidence Tasks
- Parse `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5` to catalog ROI extents, intensity stats, and confirm absence of `[panel,slow,fast]` tensor groups.
- Cross-check torch capture scripts under the same report directory to ensure we can regenerate full-panel tensors and downsample to ROI footprints.
- Draft manifest adjustments describing hybrid ROI/full-panel artifacts, including updated checksum/metadata fields and compatibility notes for parity_loader.
- Prepare testing/documentation updates covering ROI-aware selectors and describe how collect-only logs will be refreshed once evidence is captured.

## Key References
- docs/spec-db-core.md:20-41 — tensor dimensionality commitments.
- docs/spec-db-tracing.md:15-60 — ROI logging and diagnostics requirements.
- docs/findings.md:15 (DIFFBRAGG-001) — documented cleanup bug and patch policy.
- plans/active/NANOBRAG-GOLDEN-001/implementation.md — Phase checklists A-D.

## Next Steps
- Produce updated `input.md` with ROI evidence Do Now steps (A2, A3, B1, D1) and doc/test sync instructions.
- Append planning attempt entry to `docs/fix_plan.md` once Do Now is recorded.
- Maintain action state `planning` with dwell=2 unless ROI analysis unblocks diffBragg capture.
