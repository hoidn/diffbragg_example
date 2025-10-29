# NANOBRAG-GOLDEN-001 Loop Summary — 2025-10-29T071728Z

## Objective
Execute ROI-level evidence tasks to re-scope the DB-AT-001 canonical dataset plan under the Environment Freeze constraint (POLICY-001). This is a docs-only mode loop focused on planning and evidence gathering.

## Tasks Executed (4/4 Complete)

### ✓ A2 — ROI HDF5 Inventory
- **Artifact**: `roi_hdf5_scout.md`
- **Action**: Inspected `dbex_diffbragg_gpu.h5` from prior loop (2025-10-29T063817Z)
- **Findings**:
  - 92 ROI groups cataloged, all 12×12 pixels
  - Intensity statistics captured (max values: 0.0–38766.527)
  - **CRITICAL GAP**: All bbox attributes are `None` — no bounding box coordinates stored
  - No full-panel datasets present (checked for `bragg_full`, `target_full`, `loss_mask_full`)
- **Impact**: ROI slicing in torch replay (A3 step 2) is blocked without bbox coordinates

### ✓ A3 — Torch Replay Plan
- **Artifact**: `torch_roi_plan.md`
- **Action**: Outlined strategy to regenerate full-panel tensors using nanobrag_torch
- **Findings**:
  - Confirmed `capture_torch_only.py` script exists in prior loop
  - Documented 4-step replay plan with preconditions
  - ROI slicing step BLOCKED by missing bbox coordinates (A2 gap)
- **Recommendations**: Resolve bbox availability before executing torch replay OR emit full-panel tensors only

### ✓ B1 — Manifest Update Outline
- **Artifact**: `manifest_update_outline.md`
- **Action**: Drafted schema extensions for hybrid ROI/full-panel dataset
- **Findings**:
  - Current manifest points to `simple_cubic_fallback` (synthetic data)
  - Proposed fields: `datasets` (with kind discriminator), `provenance`, `roi_catalog`, `spec_version` bump
  - Verification hooks: parity_loader updates, checksum validation
- **Spec alignment**: Cites `docs/spec-db-conformance.md:23-26`, `docs/spec-db-tracing.md:15-60`

### ✓ D1 — Test/Doc Sync Evidence
- **Artifacts**: `collect_db_at_001_parity.log`, `collect_db_at_001_forward.log`
- **Action**: Ran pytest --collect-only for both DB_AT_001 selectors
- **Findings**:
  - Parity selector: 14 tests collected (0.23s)
  - Forward equivalence selector: 1 test collected (1.01s)
  - Both selectors **Active** per TESTING-003 requirement (>0 tests)
- **Doc sync complete**: Updated `docs/TESTING_GUIDE.md` §2.1 and `docs/development/TEST_SUITE_INDEX.md` with new artifact paths

## Critical Gap: Missing Bounding Box Coordinates

**Problem**: `dbex_diffbragg_gpu.h5` stores 92 ROIs but does NOT persist bbox attributes (all `None`). Original bbox data exists in `refGeom.refl` reflection table but is not propagated to HDF5.

**Mitigation Options**:
1. **Option A (Recommended)**: Re-extract bboxes from `refGeom.refl` using DIALS API
   - Implement helper to read reflection table and generate bbox catalog
   - Store as JSON alongside golden dataset
   - Update manifest with `roi_catalog` field

2. **Option B**: Modify `dbex.refine_one` to persist bbox attributes in future captures
   - Requires code change to `dbex/refine_one.py`
   - Does not help with existing HDF5 file

3. **Option C**: Redesign golden dataset to be ROI-only
   - Drop requirement for full-panel tensors
   - Parity tests compare ROI-to-ROI only (no spatial alignment)
   - Simplest but reduces parity coverage

## Spec Compliance Review

### docs/spec-db-core.md:20-41 (Data Contracts)
- ✓ ROI inventory structure confirmed
- ✓ Absence of full-panel datasets validated
- ⚠ `[panel, slow, fast]` ordering not yet validated (pending tensor capture)
- ✗ Bbox semantics `(x0, x1, y0, y1)` not available in HDF5 metadata

### docs/spec-db-conformance.md:23-26 (Manifest)
- ✓ Manifest provenance planning complete (B1)
- ✓ Checksum strategy outlined
- ⚠ Actual SHA256 computation awaits tensor capture

### docs/spec-db-tracing.md:15-60 (ROI Diagnostics)
- ✓ ROI diagnostics governance: stats logged (max intensity per ROI)
- ⚠ First-divergence metadata requires paired tensors (DiffBragg + torch)

### docs/forward_equivalence.md:21-52 (Exit Criteria)
- ✓ Test selector evidence validated (15 tests collected)
- ⚠ Exit criteria (correlation ≥0.2, localization ≥0.9) require canonical tensors

## Findings Applied (Cross-Check)

- **DIFFBRAGG-001**: ✓ This loop is docs-only; no code changes or patches proposed
- **CONFORMANCE-001**: ✓ D1 task validated both selectors are Active (>0 tests)
- **TESTING-003**: ✓ Collection logs captured; doc sync complete
- **PARITY-001**: ✓ ROI inventory logged in deterministic order (roi0..roi91)

## Metrics

- 4/4 Do Now tasks completed
- 92 ROIs inventoried
- 15 tests collected across 2 selectors (14 parity + 1 forward equivalence)
- 1 critical gap identified (missing bbox coordinates)
- 2 documentation files synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- 6 artifact files created

## Artifacts (All Present)

```
plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/
├── planning_notes.md                     (9.0K)  — Comprehensive loop summary with spec alignment
├── roi_hdf5_scout.md                     (5.5K)  — ROI inventory with stats and gap documentation
├── torch_roi_plan.md                     (988B)  — Torch replay strategy outline
├── manifest_update_outline.md            (809B)  — Proposed manifest schema extensions
├── collect_db_at_001_parity.log          (1.2K)  — Parity selector collection evidence
├── collect_db_at_001_forward.log         (1.2K)  — Forward equivalence selector collection evidence
└── summary.md                            (this file)
```

## Next Actions (Pending Supervisor Guidance)

### Immediate
1. **Resolve bbox gap**: Implement refGeom.refl re-extraction OR accept ROI-only dataset design
2. **Coordinate with supervisor**: Review evidence and decide on scope revision

### Future (After Scope Decision)
1. **If bbox gap resolved**: Execute torch replay with ROI slicing (A3 step 2)
2. **If ROI-only accepted**: Execute torch replay for full-panel tensors only
3. **After tensors captured**: Implement manifest schema (B1), update parity tests (C1-C2), sync docs (C3)

## Status
- **Loop Status**: Complete (docs-only mode, no code changes)
- **Initiative Status**: `in_progress` (awaiting scope decision)
- **Exit Condition**: All Do Now tasks executed; critical gap identified and documented; evidence artifacts staged for supervisor decision

## References
- Initiative Plan: `plans/active/NANOBRAG-GOLDEN-001/implementation.md`
- Supervisor Input: `input.md` (2025-10-29T071728Z)
- Prior Loop Artifacts: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/`
- Spec Anchors: `docs/spec-db-core.md:20-41`, `docs/spec-db-conformance.md:23-26`, `docs/spec-db-tracing.md:15-60`, `docs/forward_equivalence.md:21-52`
- Applied Findings: DIFFBRAGG-001, CONFORMANCE-001, TESTING-003, PARITY-001
