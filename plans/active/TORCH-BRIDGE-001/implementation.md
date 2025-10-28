# Implementation Plan — TORCH-BRIDGE-001

ID: TORCH-BRIDGE-001
Title: Bridge DataLoad to `nanobrag_torch`
Owner: Unassigned
Status: pending

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
- [ ] A1: Define tensor outputs (target, masks, panel_slices) and verify shapes
- [ ] A2: Add small assertions for `[panel, slow, fast]` order and mask polarity

## Phase B — Config Hydration
### Checklist
- [ ] B1: Map Detector (CUSTOM, pixel size guard, beam centre swap)
- [ ] B2: Map Beam (wavelength, polarization) and Crystal (unit cell + A*)

## Phase C — Smoke Harness
### Checklist
- [ ] C1: Single-experiment run with stitched Bragg tensor and masked MSE
- [ ] C2: Save ROI triptych artifact under `plans/active/TORCH-BRIDGE-001/reports/<ts>/`

## Artifacts Index
- Reports root: `plans/active/TORCH-BRIDGE-001/reports/`
