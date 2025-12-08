# DB-AT-021 Phase B Planning Notes

**Initiative**: DB-AT-021 (Mask Semantics Guard)
**Loop**: i=149
**Actor**: Galph (Supervisor)
**Date**: 2025-12-08T15:00:00Z
**Phase**: B (Test Scaffold Authoring) — Planning

---

## Context

**Phase A Complete (Loop i=148)**:
- ✅ Asset availability confirmed (cross-ref i=143 DB-AT-SUITE-CARE-001 Phase B.2 validation)
- ✅ Spec alignment reconciled (no conflicts across spec-db-core.md:124, dials_api.md:45-62, architecture.md:165-178)
- ✅ Baseline probe captured (5.7M trusted pixels, 13K loss_mask pixels, ROI 0: 144/144 all-valid)
- ✅ Phase B scaffold fully scoped (3 test methods, ARCH-CONTRACT-MASKING-001 enforcement)

**Transition Decision**:
- Applied **dominant-hypothesis lock** (confidence 1.0 — test assertions fully grounded by Phase A baseline metrics)
- Applied **implementation floor** (1 planning loop complete, must delegate implementation now)
- DecisionStatus: exploring → patch_ready

---

## Phase B Scoping

### Test File: `tests/dbex/test_mask_semantics.py`

**Class**: `TestDB_AT_021_MaskSemantics`

**Fixture**: `refgeom_dataload`
- Instantiate `DataLoad("refGeom.expt", "refGeom.refl", "scaled.mtz", "747_mask.pkl")`
- Apply `pytest.skip` guard when assets missing (mirror DB-AT-020 pattern from i=146-147)
- Reuse from `tests/conftest.py` if already defined; otherwise define locally

### Test Methods (3)

#### 1. `test_polarity_checks` (B2)
**Objective**: Validate DIALS mask polarity convention (True=trusted, no inversion)

**Assertions**:
- `dataload.trusted_mask.dtype == bool`
- Sample trusted pixel: `dataload.trusted_mask[0, 582, 594] == True` (ROI 0 coordinates from baseline probe)
- Sample untrusted pixel validation (if coordinates available from baseline probe)
- No polarity inversion in production path

**Grounding**: Phase A baseline probe confirmed boolean dtype + polarity alignment

---

#### 2. `test_loss_mask_construction` (B3)
**Objective**: Validate canonical loss_mask construction per spec-db-core.md:124 formula

**Formula**: `loss_mask = (background_image >= 0) ∧ trusted_mask`

**Assertions**:
- Extract `background_image` and `trusted_mask` from DataLoad
- Compute expected: `expected_loss_mask = (background_image >= 0) & trusted_mask`
- Extract actual from RefinementInputs (via `prepare_refinement_inputs` call or direct DataLoad attribute)
- Assert element-wise equality (torch.equal or numpy equivalent)
- Validate background sentinel `-1` excludes pixels (per ADR-07)
- Validate trusted mask precedence (untrusted pixels excluded even if background >= 0)

**Grounding**: Phase A baseline probe validated DataLoad constructs loss_mask with 13K pixels matching formula

---

#### 3. `test_precedence_guards` (B4)
**Objective**: Enforce ARCH-CONTRACT-MASKING-001 (canonical owner precedence)

**Canonical Owner**: `dbex.refinement.inputs.prepare_refinement_inputs`

**Forbidden Duplicates**:
- `dbex/refinement/stage_a_impl.py`
- `dbex/refinement/stage_b_impl.py`
- `dbex/refinement/stage_c_impl.py`

**Detection Method**: AST or grep search for `loss_mask = (background.*>= 0) & trusted_mask` patterns

**Assertions**:
- If duplicates found → raise AssertionError with file:line references
- If no duplicates → assert canonical owner is sole source (via import inspection or doc cross-ref)
- Document any legacy exceptions in test comments with justification

**Grounding**: Phase A confirmed no duplicates detected during spec alignment

---

## Validation Strategy

**Primary Selector**: `pytest -vv tests -k DB_AT_021`

**Collection Validation**: `pytest --collect-only tests -k DB_AT_021`
- Expected: ≥3 tests collected
- Artifact: `collect_db_at_021.log`

**Expected Outcomes**:
- All 3 tests PASS
- No ARCH-CONTRACT-MASKING-001 violations detected
- Collection log confirms ≥3 tests discoverable via `-k DB_AT_021` pattern

---

## Findings Applied

**MASKING-001** (Loss mask coverage <1% is expected):
- Test assertions must NOT flag low coverage as failure
- Baseline probe showed 13K/6.2M pixels (0.21% coverage) — expected for sparse Bragg peaks

**TESTING-003** (Selector status transitions after collection validation):
- Phase C (next loop) will update TEST_SUITE_INDEX.md after collection log confirms ≥3 tests

**CONFORMANCE-001** (DB-AT selector pattern):
- Test method names follow `test_DB_AT_021_*` convention for `-k DB_AT_021` discovery

**DIALS-API polarity** (True=trusted per dials_api.md:16):
- Test assertions validate boolean dtype with True=trusted polarity (no inversion)

---

## Artifacts Plan

**Directory**: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/`

**Expected Deliverables** (Loop i=149, Ralph):
1. `pytest_db_at_021.log` — Primary test run log (3/3 PASS expected)
2. `collect_db_at_021.log` — Collection validation (≥3 tests expected)
3. `summary.md` — Phase B completion notes (test outcomes + metrics)

---

## Phase C Preview (Not This Loop)

**Registry Sync Tasks** (Loop i=150 estimated):
1. Update `docs/TESTING_GUIDE.md` §2 with DB-AT-021 row:
   - Status: Active
   - Selector: `pytest -k DB_AT_021`
   - Artifact path: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/`
   - Referenced findings: MASKING-001, TESTING-003, CONFORMANCE-001

2. Update `docs/development/TEST_SUITE_INDEX.md` with DB-AT-021 status

3. Update `docs/fix_plan.md` Attempts History with Phase A+B outcomes

4. Mark DB-AT-021 complete per implementation.md exit criteria

---

## Risks & Mitigation

**Risk**: DataLoad lacks `trusted_mask` or `loss_mask` attributes
**Mitigation**: Escalate to supervisor as ARCH-CONTRACT-DATA-LOAD-001 violation; Phase A baseline probe validated attributes exist

**Risk**: Duplicate loss_mask construction found in Stage helpers
**Mitigation**: Escalate to supervisor as ARCH-CONTRACT-MASKING-001 conformance failure; requires canonical owner API routing + duplicate removal

**Risk**: Spec conflicts emerge during test authoring
**Mitigation**: Halt and escalate to supervisor for spec_change type handling; Phase A confirmed alignment across 3 docs

**Risk**: Canonical assets missing since Phase B.2 validation
**Mitigation**: Re-run asset availability check; update skip guard logic; assets validated 6 loops ago (i=143), low probability

---

## Decision Rationale

**Why Phase B Now?**
- Phase A delivered complete spec alignment + baseline metrics (4/4 deliverables)
- Test scaffold fully scoped (3 test methods, ARCH-CONTRACT-MASKING-001 enforcement)
- No blockers detected (assets valid, spec aligned, baseline probe successful)
- Implementation floor requires delegation after 1 planning loop

**Why Confidence 1.0?**
- Phase A baseline probe validated exact metrics for assertions (5.7M trusted pixels, 13K loss_mask pixels, ROI 0 all-valid)
- Spec alignment confirmed across 3 docs (no conflicts)
- Canonical owner identified (`prepare_refinement_inputs`)
- Test methods directly mirror spec-db-conformance.md:58-61 acceptance criteria

**Why Patch-Ready?**
- Dominant-hypothesis lock applied (test assertions grounded by empirical baseline metrics)
- Implementation floor satisfied (1 planning turn complete)
- No further planning/evidence required

---

## Next Actions

**Loop i=149 (Ralph)**:
1. Author `tests/dbex/test_mask_semantics.py` with 3 test methods
2. Run `pytest -vv tests -k DB_AT_021`
3. Run `pytest --collect-only tests -k DB_AT_021`
4. Capture logs under `plans/active/DB-AT-021/reports/2025-12-08T150000Z/`
5. Author `summary.md` with Phase B outcomes

**Expected Duration**: 1 loop (test authoring harness type, no production code edits)

**Success Criteria**: 3/3 tests PASS, collection log shows ≥3 tests, no ARCH-CONTRACT violations

---

**END OF PLANNING NOTES**
