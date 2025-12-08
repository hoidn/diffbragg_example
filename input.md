# Input for Ralph (Loop i=151)

## Summary
DB-AT-022 Phase A: Asset validation and background sentinel probes (Reality Check)

## Mode
Parity

## ActionType
planning

## DecisionStatus
exploring

## InitiativeType
harness

## Focus
DB-AT-022 — Background Sentinel Guard (Member of DB-AT-SUITE-CARE-001)

## Branch
integration

## Mapped Tests
- `pytest --collect-only tests/dbex/test_background_semantics.py` (verify test scaffold exists OR note creation needed in Phase B)
- No tests required to pass this loop (Phase A is planning/probing only)

## Artifacts
`plans/active/DB-AT-022/reports/2025-12-08T180000Z/`

## Findings Applied (Mandatory)
- **MASKING-001** (Mask handling contracts): Background sentinel −1 must be excluded from loss mask; `loss_mask = (background >= 0) ∧ trusted_mask` per spec-db-core.md:124. ✅ Applied — Phase A will validate sentinel coverage against this contract.
- **TESTING-003** (Selector status transitions only after pytest --collect-only confirms >0 tests): Phase A is planning; test authoring deferred to Phase B. ✅ Applied — no registry updates this loop.
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Probe outputs must be structured (JSON/markdown) and archived under reports/. ✅ Applied — Phase A artifacts scoped below.

**No blocking findings** — Phase A is evidence collection.

## Pointers

### Spec/Arch/Testing Docs
- **Spec**: `docs/spec-db-workflow.md:38` (background sentinels −1 MUST be masked consistently in loss/variance)
- **Spec**: `docs/spec-db-conformance.md:63-64` (DB-AT-022 acceptance: sentinel logic correct, ROI coverage matches metadata)
- **Spec**: `docs/spec-db-conformance.md:116` (loss mask formula: `(background >= 0) ∧ trusted_mask`)
- **Arch**: `docs/architecture/data_telemetry_flow.md:34` (Background sentinel: −1 outside ROI; validated before prep)
- **simtbx API**: `docs/simtbx_api.md:14` (background_image filled with −1 sentinel for invalid pixels)
- **Testing Guide**: `docs/TESTING_GUIDE.md` §2 (canonical pytest selectors)
- **Test Suite Index**: `docs/development/TEST_SUITE_INDEX.md` (comprehensive test metadata registry)

### Fix Plan
- `docs/fix_plan.md` line 267-289 (DB-AT-SUITE-CARE-001 § Attempts History)

### Implementation Plan
- `plans/active/DB-AT-022/implementation.md` Phase A checklist (A1, A2, A3)

### Prior Validation (Cross-Reference)
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md` (Phase B.2: 4 canonical assets VALID)
- `plans/active/DB-AT-021/reports/2025-12-08T150000Z/summary.md` (DB-AT-021 Phase B: mask semantics reference)

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-SENTINEL-001 (Background Sentinel Convention)
**Owner Module/API**: `dbex.data_load.DataLoad` + simtbx `get_roi_background_and_selection_flags`

**Contract**: Background image uses −1 sentinel outside ROIs; valid ROI pixels carry plane/robust background estimate. Loss mask excludes sentinel pixels via `background >= 0` guard.

**Forbidden Duplicates**: Alternative sentinel values (0, NaN) or inverted polarity in background construction.

**Failure Classification**: No conformance failure detected yet (Phase A probing).

## Do Now (hard validity contract)

**Implement**: Evidence collection for `docs/spec-db-conformance.md:63-64` DB-AT-022 acceptance criteria (Phase A — no production code changes)

Execute 3 Phase A tasks per implementation.md checklist (DB-AT-022 § Phase A):

**A1 — Asset Validation (Cross-Reference)**:
1. Cross-reference i=143 Phase B.2 asset validation:
   - Confirm refGeom assets (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`) remain valid
   - Record file presence check in `asset_availability.md`
   - If assets missing: HALT and escalate (blocker for Phase B)

**Expected Outcome**: 4/4 assets VALID (cross-ref confirms no change since i=143)

**A2 — Baseline Metrics Capture**:
1. Instantiate `DataLoad` with canonical inputs:
   ```python
   from dbex.data_load import DataLoad
   loader = DataLoad(
       expt_path="./refGeom.expt",
       refl_path="./refGeom.refl",
       mtz_path="./scaled.mtz",
       mask_path="./747_mask.pkl"
   )
   ```
2. Capture baseline metrics:
   - `loader.data.shape` (data shape: expected `(1, slow, fast)` single panel)
   - `loader.background_image.shape` (same as data)
   - `loader.bbox` (list of `(x0, x1, y0, y1)` tuples)
   - `len(loader.pids)` (ROI count, expected ~92 per DB-AT-020/021 probes)
   - Sample bbox dimensions (x1-x0, y1-y0 for first 5 ROIs)
3. Archive metrics in `baseline_metrics.md`

**Expected Outcome**: DataLoad instantiates without error; metrics capture confirms prerequisites from DB-AT-020/021 remain valid.

**A3 — Sentinel Coverage Probe**:
1. Compute sentinel mask:
   ```python
   import numpy as np
   bg = loader.background_image  # shape: (n_panels, slow, fast)
   sentinel_mask = np.isclose(bg, -1.0)  # True where background == -1
   sentinel_count = sentinel_mask.sum()
   total_pixels = bg.size
   sentinel_fraction = sentinel_count / total_pixels
   ```

2. Compute ROI union mask (pixels inside ANY ROI):
   ```python
   roi_union = np.zeros(bg.shape, dtype=bool)
   for (x0, x1, y0, y1), pid in zip(loader.bbox, loader.pids):
       roi_union[pid, y0:y1, x0:x1] = True
   roi_count = roi_union.sum()
   roi_fraction = roi_count / total_pixels
   ```

3. Compute overlap/complement analysis:
   ```python
   # Sentinel should be complement of ROI union (outside ROIs)
   overlap = (sentinel_mask & roi_union).sum()  # Should be 0
   complement_match = (sentinel_mask == ~roi_union).all()  # Should be True

   # Valid background pixels (inside ROIs, not sentinel)
   valid_bg = (bg >= 0) & roi_union
   valid_bg_count = valid_bg.sum()
   ```

4. Archive results in `sentinel_probe.md`:
   - Sentinel pixel count and fraction
   - ROI union pixel count and fraction
   - Overlap count (expected: 0)
   - Complement match (expected: True)
   - Valid background pixel count
   - Classification: Case A (perfect match), Case B (minor anomaly), Case C (significant mismatch)

**Expected Outcome**: Sentinel mask equals complement of ROI union, overlap == 0, coverage aligns with ROI area from reflection metadata.

**Artifacts Destination**: `plans/active/DB-AT-022/reports/2025-12-08T180000Z/`
- `asset_availability.md` (A1: cross-ref to i=143 validation)
- `baseline_metrics.md` (A2: DataLoad shape/count metrics)
- `sentinel_probe.md` (A3: sentinel coverage analysis with classification)
- `summary.md` (Phase A completion notes + Phase B scoping)

**Touched**: DB-AT-022 Phase A (A1, A2, A3)

## Forbidden This Loop
- **No production code edits** (Phase A is evidence collection)
- **No test authoring** (deferred to Phase B)
- **No registry updates** (docs/TESTING_GUIDE.md, TEST_SUITE_INDEX.md unchanged)

## How-To Map

**Phase A Steps**:
1. Create artifacts directory: `mkdir -p plans/active/DB-AT-022/reports/2025-12-08T180000Z/`
2. Execute A1: Cross-reference i=143 asset validation, confirm files exist, write `asset_availability.md`
3. Execute A2: Load DataLoad, capture shapes/counts, write `baseline_metrics.md`
4. Execute A3: Compute sentinel/ROI masks, analyze coverage, write `sentinel_probe.md`
5. Author `summary.md` with Phase A outcomes and Phase B implementation scoping
6. Update `plans/active/DB-AT-022/implementation.md` (mark A1/A2/A3 in progress or complete if time permits)

**Expected Artifact Summary**:
- `asset_availability.md`: 4 assets confirmed VALID (cross-ref)
- `baseline_metrics.md`: data shape, background shape, ROI count, sample bbox dimensions
- `sentinel_probe.md`: sentinel_fraction, roi_fraction, overlap=0, complement_match=True
- `summary.md`: Phase A complete, Phase B scope (B1 sentinel guard hardening, B2 test authoring, B3 pytest execution)

**Success Criteria**:
- DataLoad instantiates without error
- Sentinel mask == complement of ROI union (overlap == 0)
- Coverage fractions logged (sentinel_fraction + roi_fraction ≈ 1.0)
- All 4 artifacts authored and archived

## Pitfalls To Avoid
1. **Stale asset references**: Use i=143 asset checksums as ground truth; if files changed, note discrepancy.
2. **Array ordering**: Background and sentinel masks use `[panel, slow, fast]` per spec-db-core.md:22; do NOT swap axes.
3. **Sentinel value precision**: Use `np.isclose(bg, -1.0)` not exact equality; simtbx may use float −1.
4. **ROI bbox slicing**: `bbox = (x0, x1, y0, y1)` with x1/y1 exclusive; slice as `img[pid, y0:y1, x0:x1]` not `x0:x1, y0:y1`.
5. **Classification drift**: If overlap > 0 or complement doesn't match, classify as Case B/C (anomaly) and document for Phase B investigation — do NOT fail the loop.

## If Blocked
- **DataLoad import fails**: Record import error, check environment, escalate to supervisor (likely environment drift or dependency issue).
- **Assets missing**: Halt Phase A, update asset_availability.md with failure, escalate to supervisor (blocker for portfolio).
- **Sentinel anomaly (overlap > 0)**: Document as Case C, author hypothesis in sentinel_probe.md, continue with Phase A completion — Phase B will investigate.

---

**END OF INPUT.MD**
