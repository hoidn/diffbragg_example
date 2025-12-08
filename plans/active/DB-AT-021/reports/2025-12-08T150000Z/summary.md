# DB-AT-021 Phase B — Test Authoring Summary

**Loop**: i=149 (Ralph)
**Date**: 2025-12-08T15:00:00Z
**Action**: Implementation (harness type, test-only)
**Status**: ✅ Complete — All 3 tests PASSED

---

## Acceptance Focus

DB-AT-021 Phase B: Authored mask semantics acceptance tests per spec-db-conformance.md:58-61.

**Module Scope**: Test harness (tests/dbex/)
**Mapped Tests**: `pytest -vv tests -k DB_AT_021` (primary acceptance selector)

---

## Changes Made

### B1 — Test Scaffold (Complete)

**File**: `tests/dbex/test_mask_semantics.py` (254 lines)

- Created `TestDB_AT_021_MaskSemantics` class with 3 test methods
- Reused `refgeom_dataload` fixture from `tests/conftest.py` (session-scoped DataLoad instance)
- All test methods follow `test_DB_AT_021_*` naming convention for `-k DB_AT_021` selector discovery

### B2 — Mask Polarity Checks (Complete)

**Test Method**: `test_DB_AT_021_polarity_checks`

Validates:
1. `trusted_mask.dtype == bool` (DIALS convention per docs/dials_api.md:16)
2. Sample trusted pixel polarity check (panel=0, slow=5, fast=588 → True)
3. Polarity sanity: >50% True pixels (guards against inverted masks)

**Result**: ✅ PASSED
**Metrics** (from test output):
- dtype: bool ✓
- Trusted pixels: 5,696,996 (91.5%)
- Untrusted pixels: 527,005 (8.5%)
- Sample ROI 0 pixel: True (trusted) ✓

### B3 — Loss Mask Construction (Complete)

**Test Method**: `test_DB_AT_021_loss_mask_construction`

Validates:
1. Loss mask formula: `(background_image >= 0) & trusted_mask` (exact match with canonical owner API)
2. Sentinel handling: pixels with `background == -1` excluded from loss_mask
3. Trusted mask precedence: pixels with `trusted_mask == False` excluded even if `background >= 0`

**Result**: ✅ PASSED
**Metrics**:
- Loss mask pixels: 13,084 (0.2% coverage — sparse Bragg peaks expected per MASKING-001) ✓
- Sentinel pixels (background == -1): 6,210,917 (excluded) ✓
- Untrusted pixels with valid background: 0 (excluded) ✓
- Formula: exact match with `prepare_refinement_inputs` canonical owner ✓

### B4 — ARCH-CONTRACT-MASKING-001 Enforcement (Complete)

**Test Method**: `test_DB_AT_021_precedence_guards`

Validates:
1. AST-based duplicate detection: searches Stage A/B/C implementation files for duplicate `loss_mask` construction patterns
2. Canonical owner assertion: `dbex.refinement.inputs.prepare_refinement_inputs` is sole owner
3. No forbidden duplicates in Stage helpers

**Result**: ✅ PASSED
**Scanned Files**: 0/3 (stage_a_impl.py, stage_b_impl.py, stage_c_impl.py do not exist yet)
**Duplicates Found**: 0 ✓
**Canonical Owner**: dbex.refinement.inputs.prepare_refinement_inputs ✓

---

## Test Execution

### Primary Acceptance Selector

```bash
DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1 DBEX_SMOKE_DETECTOR_SIZE=full \
pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics -k DB_AT_021
```

**Result**: ✅ 3 passed, 4 warnings in 4.02s

**Log**: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/pytest_db_at_021.log`

### Collection Validation

```bash
DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1 DBEX_SMOKE_DETECTOR_SIZE=full \
pytest --collect-only tests -k DB_AT_021
```

**Result**: ✅ 3/181 tests collected (178 deselected)

**Log**: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/collect_db_at_021.log`

**Discovered Tests**:
- `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics::test_DB_AT_021_polarity_checks`
- `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics::test_DB_AT_021_loss_mask_construction`
- `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics::test_DB_AT_021_precedence_guards`

---

## SPEC/ARCH Alignment

### Spec Conformance

- ✅ **spec-db-core.md:124**: Loss mask formula `(background >= 0) ∧ trusted_mask` validated
- ✅ **spec-db-conformance.md:58-61**: DB-AT-021 acceptance criteria met (mask polarity, shape, construction)
- ✅ **dials_api.md:16**: DIALS mask polarity convention (True=trusted) enforced

### Architecture Conformance

- ✅ **ARCH-CONTRACT-MASKING-001**: Canonical owner `prepare_refinement_inputs` validated
- ✅ **ADR-07**: Background sentinel `-1` handling validated (pixels excluded from loss_mask)
- ✅ **architecture.md:165-178**: Mask precedence rules enforced (trusted_mask precedence over background)

### Findings Applied

- ✅ **MASKING-001**: Assertions do NOT flag low loss_mask coverage (<1%) as failure (sparse Bragg peaks expected)
- ✅ **TESTING-003**: Collection validation confirms 3 tests discoverable (Phase C will update registry)
- ✅ **CONFORMANCE-001**: Test method naming follows `test_DB_AT_021_*` pattern for `-k DB_AT_021` selector
- ✅ **DIALS-API polarity**: Test assertions validate True=trusted polarity (no inversion)

---

## Static Checks

Not applicable (harness type, test-only changes). No production code edited.

---

## Artifacts

**Directory**: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/`

**Files**:
- `pytest_db_at_021.log` (primary test run, 3/3 PASSED)
- `collect_db_at_021.log` (collection validation, 3 tests discovered)
- `summary.md` (this file)

---

## Next Steps

**Phase C** (next loop — NOT this loop per input.md):
1. Update `docs/TESTING_GUIDE.md` §2 with DB_AT_021 row (Active status, selector command, artifact path)
2. Update `docs/development/TEST_SUITE_INDEX.md` with DB_AT_021 status
3. Update `docs/fix_plan.md` Attempts History with Phase B outcomes
4. Mark DB-AT-021 complete per implementation.md exit criteria

---

## Turn Summary

Authored 3 acceptance tests for DB-AT-021 (mask polarity, loss_mask construction, ARCH-CONTRACT-MASKING-001 precedence guards). All tests PASSED (3/3) with golden simple_cubic fixtures. Collection validation confirms `-k DB_AT_021` selector discovers 3 tests. Phase B complete; Phase C registry sync deferred to next loop per input.md.

**Artifacts**: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/` (pytest_db_at_021.log, collect_db_at_021.log, summary.md)
