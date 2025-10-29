# Planning Notes — 2025-10-29T075930Z

## Focus
NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

## Objective
Map the next implementation loop toward capturing canonical tensors by first extracting a verified ROI bounding-box catalog, drafting the torch capture playbook, and pre-planning manifest plus doc/test sync steps under Environment Freeze constraints.

## Reality Check
- `tests/fixtures/golden_data/simple_cubic/manifest.json` still references `simple_cubic_fallback`; canonical tensors absent.
- `refGeom.refl` contains 282 reflections with bbox data (validated via dxtbx import).
- Legacy HDF5 at `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5` stores 92 ROI groups but no bbox attributes.
- `nanobrag_torch` import remains unresolved in frozen environment; plan avoids execution until available.

## Key Tasks for Next Loop
1. Emit `roi_bbox_catalog.json` + `roi_bbox_summary.md` capturing bbox inventory and alignment with legacy HDF5.
2. Draft `torch_capture_playbook.md` detailing per-panel capture steps, seeding, and ROI slicing.
3. Prepare `manifest_delta_outline.md` covering canonical dataset metadata, provenance, and checksum hooks.
4. Refresh DB_AT_001 parity/forward collect-only logs under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/` and note doc sync updates.

## Findings Applied
- DIFFBRAGG-001 guards against re-running the broken DiffBragg forward path; documentation-first approach maintained.
- TESTING-003 enforces fresh selector logs for DB_AT_001 before changing activation status.
- PARITY-001 drives deterministic ROI ordering in the planned catalog.
- CONFIG-001 informs torch capture mapping requirements.

## Next Actions
Follow the Do Now checklist in `input.md`; validate catalog output before moving to torch playbook drafting.

