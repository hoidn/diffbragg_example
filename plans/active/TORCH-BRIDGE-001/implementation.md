# Implementation Plan — TORCH-BRIDGE-001

ID: TORCH-BRIDGE-001
Title: Bridge DataLoad to `nanobrag_torch`
Owner: Unassigned
Status: in_progress

## Goals
- Prepare tensors and configs consumable by `nanobrag_torch` while preserving DBEX tensor ordering and mask semantics.
- Provide per-panel slices for stitching and a masked loss compatible with existing ROI logic.

## Phases Overview
- Phase A — Scaffolding & I/O: adapters, shapes, and masks
- Phase B — Config Hydration: Detector/Beam/Crystal mapping
- Phase C — Smoke Harness: single-experiment flow and artifact capture

## Exit Criteria
1. Helper returns background-subtracted targets, trusted/background masks, and per-panel slices aligned to `[panel, slow, fast]`.
2. Detector/beam/crystal configs hydrate the torch simulator per the crosswalk and API docs.
3. Bridge raises when pixel pitch is not square.
4. Smoke harness exercises one DIALS experiment; artifacts recorded with ROI triptych.

## Phase A — Scaffolding & I/O
### Checklist
- [x] A1: Define tensor outputs (target, masks, panel_slices) and verify shapes
- [x] A2: Add small assertions for `[panel, slow, fast]` order and mask polarity

**Completed:** 2025-10-28T222910Z
**Artifacts:** plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/
**Module:** dbex/nanobrag_bridge.py (RefinementInputs, prepare_refinement_inputs)
**Tests:** tests/dbex/test_nanobrag_bridge.py (4 tests, all passing)

## Phase B — Config Hydration
### Checklist
- [x] B1: Map Detector (CUSTOM, pixel size guard, beam centre swap)
- [x] B2: Map Beam (wavelength, polarization) and Crystal (unit cell + A*)

**Completed:** 2025-10-28T224846Z
**Artifacts:** plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/
**Module:** dbex/nanobrag_bridge.py (added config stubs and 3 helper functions)
**Tests:** tests/dbex/test_nanobrag_bridge_configs.py (14 new tests, all passing)

## Phase C — Smoke Harness
### Checklist
- [x] C1: Single-experiment run with stitched Bragg tensor and masked MSE
  - Build pytest harness around `DataLoad` outputs and bridge helpers
  - Guard `nanobrag_torch` import (fallback to stub for now) and stitch `[panel, slow, fast]`
  - Emit masked MSE plus per-panel intensity stats for reports
- [x] C2: Save ROI triptych artifact under `plans/active/TORCH-BRIDGE-001/reports/<ts>/`
  - Render data/model/residual triptych for at least one ROI via matplotlib
  - Persist summary metrics (`smoke_metrics.json`) alongside the image artifact

**Completed:** 2025-10-28T231200Z
**Artifacts:** plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/
**Module:** tests/dbex/test_nanobrag_smoke.py (3 tests, all passing)
**Tests:** pytest -v tests/dbex/test_nanobrag_smoke.py (3/3 passed, 1.83s, CPU)

## Artifacts Index
- Reports root: `plans/active/TORCH-BRIDGE-001/reports/`
