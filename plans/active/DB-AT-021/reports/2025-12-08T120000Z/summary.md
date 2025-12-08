# DB-AT-021 Phase A Summary

**Initiative**: DB-AT-021 (Mask Semantics Guard)
**Loop**: i=148
**Actor**: Ralph
**Date**: 2025-12-08T12:00:00Z
**Phase**: A (Planning & Evidence)

---

## Phase A Completion Status

**Status**: ✅ COMPLETE — All 4 deliverables shipped

| Deliverable | Status | Artifact |
|-------------|--------|----------|
| A1: Asset Availability Check | ✅ Complete | `asset_availability.md` |
| A2: Spec Alignment | ✅ Complete | `spec_alignment.md` |
| A3: Baseline Probe | ✅ Complete | `baseline_probe.md`, `baseline_probe.py` |
| A4: Phase A Summary (this doc) | ✅ Complete | `summary.md` |

---

## Key Findings

### A1: Asset Availability (Cross-Reference DB-AT-SUITE-CARE-001 Phase B.2)

**All 4 canonical assets validated** (Loop i=143, 5 loops prior):
- ✅ `refGeom.expt` — 5.1K, SHA256: 184d744fe62d51c1
- ✅ `refGeom.refl` — 202K, SHA256: 7ab679640d867a8c
- ✅ `scaled.mtz` — 2.8M, SHA256: 341108a13c56bc82
- ✅ `747_mask.pkl` — 6.0M, SHA256: 3603bd8aa32a36fd

**Location**: Repository root (not under `tests/fixtures/`)

**Skip behavior for Phase B**: Mirror DB-AT-020 pattern (pytest.skip when assets missing)

---

### A2: Spec Alignment

**Status**: ✅ ALIGNED — No conflicts detected across 3 docs

| Aspect | spec-db-core.md | dials_api.md | architecture.md |
|--------|----------------|--------------|-----------------|
| **Trusted polarity** | True=trusted (line 34) | True=trusted (line 16) | True=trusted (line 54) |
| **Loss mask formula** | `(background >= 0) ∧ trusted_mask` (line 124) | (external API doc) | `(bg_mask_tensor & trusted_mask_tensor)` (line 57) |
| **Background sentinel** | `-1` outside ROIs (line 124 implication) | (not specified) | `-1` sentinel (ADR-07, line 105) |
| **Inversion required?** | No (direct polarity) | No for `nanobrag_torch` path | No (direct polarity, line 61) |

**ARCH-CONTRACT-MASKING-001 Canonical Owner**:
- **Module**: `dbex.refinement.inputs.prepare_refinement_inputs`
- **Contract**: Constructs `loss_mask = (background_image >= 0) ∧ trusted_mask` per spec-db-core.md:124
- **Forbidden duplicates**: Alternative loss_mask construction in Stage helpers, test harness, or plan-local scripts

**DB-AT-021 Acceptance Criteria** (spec-db-conformance.md:58-61):
- Setup: Load DIALS trusted mask; convert to simulator mask; verify mask/loss application on sample ROIs
- Expectation: Simulator zeros masked pixels post-compute; loss excludes masked/background-invalid pixels

---

### A3: Baseline Probe

**DataLoad Mask Metrics** (refGeom.expt/refl/mtz, 747_mask.pkl):

```
trusted_mask_shape:               (1, 2527, 2463)  # [panel, slow, fast]
trusted_mask_dtype:               bool             # DIALS convention
trusted_pixel_count:              5,696,996        # True=trusted
untrusted_pixel_count:            527,005          # False=untrusted
loss_mask_pixel_count:            13,084           # (background >= 0) & trusted_mask
```

**Sample ROI 0** (bbox: (582, 594, 0, 12)):
```
roi_trusted_pixels:               144 / 144        # All pixels trusted in this ROI
roi_loss_mask_pixels:             144 / 144        # All pixels pass loss mask
roi_background_valid_pixels:      144              # No sentinel (-1) pixels
roi_background_sentinel_pixels:   0                # Sentinel count
```

**Validation**:
- ✅ `trusted_mask.dtype == bool` (DIALS polarity: True=trusted)
- ✅ `loss_mask` construction matches spec-db-core.md:124 formula
- ✅ Background sentinel `-1` honored (ROI 0 has no sentinel pixels inside ROI boundary)
- ✅ `DataLoad` correctly exposes `trusted_mask` attribute (ARCH-CONTRACT-DATA-LOAD-001 compliance)

**Probe discipline**:
- Probe script: 89 LOC (under 100 LOC limit per PROBE-FREEZE-001)
- Thin wrapper: Calls `DataLoad` API directly; no semantics duplication
- Output: Structured metrics in `baseline_probe.md`

---

## Phase B Scoping

**Test Scaffold Design**: `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics`

**3 Test Methods** (mapped to DB-AT-021 acceptance criteria):

1. **`test_polarity_checks`**:
   - Load `747_mask.pkl` via `DataLoad`
   - Assert `trusted_mask.dtype == bool`
   - Verify sample trusted pixel (True) and untrusted pixel (False)
   - Confirm no polarity inversion in production path

2. **`test_loss_mask_construction`**:
   - Mock or fixture: `background_image` with sentinel `-1` in some regions
   - Call `prepare_refinement_inputs` or inspect `DataLoad` + manual construction
   - Assert `loss_mask[i,j] == True` where `(background[i,j] >= 0) and trusted_mask[i,j]`
   - Assert `loss_mask[i,j] == False` where `(background[i,j] == -1) or not trusted_mask[i,j]`
   - Validate against spec-db-core.md:124 normative formula

3. **`test_precedence_guards`** (ARCH-CONTRACT-MASKING-001 enforcement):
   - Search for duplicate loss_mask construction logic in production paths
   - If found, flag as ARCH-CONTRACT-MASKING-001 violation
   - Validate canonical owner (`prepare_refinement_inputs`) is the single source of truth
   - Confirm simulator mask receives DIALS polarity directly (1=include, no inversion)

**Fixture Strategy**:
- Check if `refgeom_dataload` fixture exists in `tests/conftest.py` or `tests/dbex/conftest.py`
- If shared across ≥3 member plans, extract to shared conftest.py
- Otherwise, define locally in `test_mask_semantics.py`
- Wrap with skip guard when canonical assets missing (mirror DB-AT-020 pattern)

**Acceptance Selector**: `pytest -v tests -k DB_AT_021` (per spec-db-conformance.md:61)

---

## Next Loop Preview (Phase B Implementation)

**Deliverables** (Loop i=149, estimated):
1. Author `tests/dbex/test_mask_semantics.py` with 3 test methods above
2. Run `pytest -v tests -k DB_AT_021` to validate acceptance criteria
3. Update `docs/development/TEST_SUITE_INDEX.md` with DB-AT-021 row (deferred to Phase C per standard pattern)
4. Update `docs/fix_plan.md` Attempts History with Phase A/B outcomes
5. Commit: `DB-AT-021: Phase B acceptance tests (tests: DB_AT_021)`

**Prerequisites**:
- Phase A artifacts (this loop) provide spec alignment + baseline metrics
- No production code edits required for Phase B (harness type, test-only)
- No fix_plan updates until Phase C (per input.md §Forbidden This Loop)

**Escalation triggers**:
- If duplicate loss_mask construction found → architecture type conformance work
- If ARCH-CONTRACT-MASKING-001 violation requires consolidation → escalate to supervisor
- If spec conflicts emerge during test authoring → spec_change type

---

## Artifacts

**Directory**: `plans/active/DB-AT-021/reports/2025-12-08T120000Z/`

| File | Description | LOC |
|------|-------------|-----|
| `asset_availability.md` | A1: Asset cross-reference + skip behavior design | N/A (doc) |
| `spec_alignment.md` | A2: Mask polarity reconciliation across 3 docs | N/A (doc) |
| `baseline_probe.py` | A3: DataLoad inspection script (thin wrapper) | 89 |
| `baseline_probe.md` | A3: Baseline metrics output | N/A (generated) |
| `summary.md` | A4: Phase A completion notes (this doc) | N/A (doc) |

---

## Turn Summary

Phase A complete: validated canonical assets (cross-ref i=143), reconciled mask polarity specs (no conflicts), captured baseline DataLoad metrics (trusted=5.7M pixels, loss_mask=13K pixels, ROI 0 all-valid), scoped Phase B test scaffold (3 test methods, ARCH-CONTRACT-MASKING-001 enforcement). Next: Phase B test authoring (Loop i=149).

Artifacts: `plans/active/DB-AT-021/reports/2025-12-08T120000Z/` (5 files: asset_availability.md, spec_alignment.md, baseline_probe.{py,md}, summary.md)
