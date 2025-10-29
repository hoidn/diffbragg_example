# NANOBRAG-GOLDEN-001 Planning Notes — 2025-10-29T071728Z

## Loop Summary
This loop executed ROI-level evidence tasks to re-scope the DB-AT-001 canonical dataset plan under the Environment Freeze, following the supervisor's Do Now from `input.md`.

## Tasks Completed

### A2 — ROI HDF5 Inventory (NANOBRAG-GOLDEN-001::A2)
**Status**: ✓ Complete
**Artifact**: `roi_hdf5_scout.md`

**Findings**:
- Total ROI groups in `dbex_diffbragg_gpu.h5`: 92
- All ROIs are 12×12 pixel arrays
- **Critical gap**: `bbox` attributes are ALL `None` — no bounding box coordinates stored
- Intensity statistics captured (max values per ROI ranging from 0.0 to 38766.527)
- **Confirmed**: No full-panel datasets present (checked for `bragg_full`, `target_full`, `loss_mask_full`)

**Implications**:
- ROI slicing strategy (task A3 step 2) is BLOCKED: cannot slice torch tensors without bbox coordinates
- Must either:
  1. Re-extract bboxes from original `refGeom.refl` reflection table
  2. Accept that ROI-level parity cannot be spatially aligned to full-panel tensors
  3. Redesign golden dataset to be ROI-only without full-panel requirement

### A3 — Torch Replay Plan (NANOBRAG-GOLDEN-001::A3)
**Status**: ✓ Complete
**Artifact**: `torch_roi_plan.md`

**Findings**:
- Confirmed `capture_torch_only.py` exists in prior loop (2025-10-29T063817Z)
- Outlined 4-step replay plan including per-panel tensor emission, ROI slicing, deterministic naming
- Documented preconditions (nanobrag_torch availability, environment flags)
- **Dependency**: ROI slicing (step 2) requires bbox coordinates (BLOCKED by A2 gap)

**Recommendations**:
- Before executing torch replay, resolve bbox availability issue
- Consider modifying plan to emit full-panel tensors only, without ROI slices
- If ROI parity is mandatory, implement bbox re-extraction from refGeom.refl

### B1 — Manifest Update Outline (NANOBRAG-GOLDEN-001::B1)
**Status**: ✓ Complete
**Artifact**: `manifest_update_outline.md`

**Findings**:
- Current manifest points to `simple_cubic_fallback` dataset
- Proposed schema extensions:
  - `datasets` field: support hybrid ROI/panel entries with `kind` discriminator
  - `provenance` sub-sections for DiffBragg and torch captures
  - `roi_catalog` for bbox and ordering metadata
  - `spec_version` bump for contract changes
- Verification hooks: parity_loader updates, checksum validation

**Alignment**:
- Spec citations: `docs/spec-db-conformance.md:23-26`, `docs/spec-db-tracing.md:15-60`
- Ready for implementation once canonical tensors are captured

### D1 — Test/Doc Sync Evidence (NANOBRAG-GOLDEN-001::D1)
**Status**: ✓ Complete
**Artifacts**: `collect_db_at_001_parity.log`, `collect_db_at_001_forward.log`

**Findings**:
- DB_AT_001 parity selector: **14 tests collected** (0.23s)
- DB_AT_001 forward equivalence selector: **1 test collected** (1.01s)
- Both selectors are **Active** per TESTING-003 requirement (>0 tests)
- Total: 15 tests confirmed ready for execution

**Selector Compliance**:
- ✓ TESTING-003: All Active selectors collect >0 tests
- ✓ Collection logs captured for doc sync
- Ready for `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` updates

## Critical Gaps Identified

### Gap 1: Missing Bounding Box Coordinates
**Impact**: High
**Blocker for**: ROI slicing (A3 step 2), ROI-to-panel spatial alignment

**Root Cause**:
- `dbex.refine_one` stores ROI tensors under `/bragg/roi{N}` but does NOT persist bbox attributes
- Original bbox data lives in `refGeom.refl` reflection table but is not propagated to HDF5

**Mitigation Options**:
1. **Option A (Recommended)**: Re-extract bboxes from `refGeom.refl` using DIALS API
   - Implement helper to read reflection table and generate bbox catalog
   - Store bbox catalog as JSON alongside golden dataset
   - Update manifest with `roi_catalog` field

2. **Option B**: Modify `dbex.refine_one` to persist bbox attributes in future captures
   - Requires code change to `dbex/refine_one.py`
   - Does not help with existing `dbex_diffbragg_gpu.h5`

3. **Option C**: Redesign golden dataset to be ROI-only
   - Drop requirement for full-panel tensors
   - Parity tests compare ROI-to-ROI only (no spatial alignment checks)
   - Simplest but reduces parity coverage

### Gap 2: Environment Freeze Constraint
**Impact**: Medium
**Constraint**: Cannot install packages or modify toolchain

**Status**: Not blocking current loop (docs-only mode), but will constrain future capture loops if:
- nanobrag_torch API changes require updates
- torch version incompatibilities arise
- CUDA/driver issues resurface

**Mitigation**: DIFFBRAGG-001 finding documents GPU workaround for diffBragg forward pass bug; no further patches planned unless critical path is blocked.

## Spec Compliance Review

### Alignment with `docs/spec-db-core.md:20-41`
- ✓ Confirmed ROI inventory structure
- ✓ Validated absence of full-panel datasets
- ⚠ **Partial**: `[panel, slow, fast]` ordering not yet validated (pending tensor capture)
- ✗ **Gap**: Bbox semantics `(x0, x1, y0, y1)` not available in HDF5 metadata

### Alignment with `docs/spec-db-conformance.md:23-26`
- ✓ Manifest provenance planning complete (B1)
- ✓ Checksum strategy outlined
- ⚠ **Pending**: Actual SHA256 computation awaits tensor capture

### Alignment with `docs/spec-db-tracing.md:15-60`
- ✓ ROI diagnostics governance: stats logged (max intensity per ROI)
- ⚠ **Pending**: First-divergence metadata requires paired tensors (DiffBragg + torch)

### Alignment with `docs/forward_equivalence.md:21-52`
- ✓ Test selector evidence validated (15 tests collected)
- ⚠ **Pending**: Exit criteria (correlation ≥0.2, localization ≥0.9) require canonical tensors

## Findings Applied (Mandatory Cross-Check)

### DIFFBRAGG-001
**Status**: Acknowledged
**Action**: Planning prioritizes evidence/documentation for the diffBragg cleanup bug before any patch proposal
**Compliance**: ✓ This loop is docs-only; no code changes or patches proposed

### CONFORMANCE-001
**Status**: Applied
**Action**: Maintains focus on selector compliance while reshaping dataset plans
**Compliance**: ✓ D1 task validated both selectors are Active (>0 tests)

### TESTING-003
**Status**: Applied
**Action**: Ensures collect-only commands/log paths are defined for selector synchronization
**Compliance**: ✓ Collection logs captured; ready for doc sync

### PARITY-001
**Status**: Applied
**Action**: Preserves ROI ordering and first-divergence metadata obligations in the planning steps
**Compliance**: ✓ ROI inventory logged in deterministic order (roi0..roi91); first-divergence pending paired tensors

## Next Actions

### Immediate (Before Next Loop)
1. **Resolve bbox gap** (Gap 1):
   - Implement bbox re-extraction from `refGeom.refl`
   - Store bbox catalog as `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/bbox_catalog.json`
   - OR accept ROI-only golden dataset design

2. **Doc Sync** (per input.md Doc Sync Plan):
   - Update `docs/TESTING_GUIDE.md` §2 with artifact paths from this loop
   - Update `docs/development/TEST_SUITE_INDEX.md` to reference `collect_db_at_001_parity.log` and `collect_db_at_001_forward.log`

3. **Ledger Update** (Mandatory):
   - Append Attempts History entry to `docs/fix_plan.md` with:
     - Timestamp: 2025-10-29T071728Z
     - Metrics: 4/4 Do Now tasks completed, 92 ROIs inventoried, 15 tests collected, 1 critical gap identified
     - Artifacts: roi_hdf5_scout.md, torch_roi_plan.md, manifest_update_outline.md, collect logs (2)
     - First Divergence: n/a (planning loop)
     - Next Actions: Resolve bbox gap, execute doc sync, coordinate with supervisor on golden dataset scope

### Future (Pending Supervisor Guidance)
1. **Canonical Tensor Capture** (Phase A):
   - If bbox gap resolved: Execute A3 torch replay with ROI slicing
   - If ROI-only design accepted: Execute A3 torch replay for full-panel tensors only
   - Either way: Requires nanobrag_torch and GPU/CPU strategy per DIFFBRAGG-001

2. **Manifest Implementation** (Phase B):
   - After canonical tensors exist, implement B1 manifest schema
   - Update parity_loader fixtures (B2)
   - Author/update regeneration tooling (B3)

3. **Parity Harness Integration** (Phase C):
   - Swap dataset reference in tests (C1)
   - Enforce thresholds without synthetic noise (C2)
   - Sync testing docs (C3)

## References
- Initiative Plan: `plans/active/NANOBRAG-GOLDEN-001/implementation.md`
- Prior Loop Artifacts: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/`
- Supervisor Input: `input.md` (2025-10-29T071728Z)
- Spec Anchors:
  - `docs/spec-db-core.md:20-41` (data contracts, bbox semantics)
  - `docs/spec-db-conformance.md:23-26` (manifest/provenance)
  - `docs/spec-db-tracing.md:15-60` (ROI diagnostics governance)
  - `docs/forward_equivalence.md:21-52` (exit criteria)
- Applied Findings: DIFFBRAGG-001, CONFORMANCE-001, TESTING-003, PARITY-001

---
**Loop Status**: Complete (docs-only mode, no code changes)
**Exit Condition**: All Do Now tasks executed; critical gap identified and documented; awaiting supervisor guidance on golden dataset scope revision.
