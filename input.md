# Input for Ralph (Loop i=149)

## Summary
DB-AT-021 Phase B: Author mask semantics acceptance tests (harness type, test-only)

## Mode
TDD

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
harness

## Focus
DB-AT-021 — Mask Semantics Guard (Member of DB-AT-SUITE-CARE-001)

## Branch
integration

## Mapped Tests
- `pytest -v tests -k DB_AT_021` (primary acceptance selector)
- `pytest --collect-only tests -k DB_AT_021` (collection validation)

## Artifacts
`plans/active/DB-AT-021/reports/2025-12-08T150000Z/`

## Findings Applied (Mandatory)
- **MASKING-001** (Loss mask coverage <1% is expected for sparse Bragg peaks): Test assertions must NOT flag low coverage as failure.
- **TESTING-003** (Selector status transitions only after pytest --collect-only confirms >0 tests): Phase C will validate collection before updating TEST_SUITE_INDEX.md.
- **CONFORMANCE-001** (DB-AT parity selectors use `-k DB_AT_0XX` pattern): Test method naming follows `test_DB_AT_021_*` convention.
- **DIALS-API polarity** (True=trusted per dials_api.md:16): Test assertions validate boolean dtype with True=trusted polarity.

**No relevant findings requiring pre-implementation action** — Phase A confirmed spec alignment.

## Pointers

### Spec/Arch/Testing Docs
- **Spec**: `docs/spec-db-core.md:124` (loss_mask normative formula: `(background >= 0) ∧ trusted_mask`)
- **Spec**: `docs/spec-db-conformance.md:58-61` (DB-AT-021 acceptance criteria)
- **DIALS API**: `docs/dials_api.md:45-62` (mask polarity conventions)
- **Architecture**: `docs/architecture.md:165-178` (mask precedence + ADR-07 background sentinel)
- **Testing Guide**: `docs/TESTING_GUIDE.md` (canonical pytest selectors)

### Fix Plan
- `docs/fix_plan.md` line 240 (DB-AT-SUITE-CARE-001 § Member Plan Coordination)

### Implementation Plan
- `plans/active/DB-AT-021/implementation.md` Phase B checklist

### Phase A Artifacts
- `plans/active/DB-AT-021/reports/2025-12-08T120000Z/summary.md` (spec alignment + baseline metrics)
- `plans/active/DB-AT-021/reports/2025-12-08T120000Z/spec_alignment.md` (polarity reconciliation table)
- `plans/active/DB-AT-021/reports/2025-12-08T120000Z/baseline_probe.md` (DataLoad metrics: 5.7M trusted pixels, 13K loss_mask pixels)

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-MASKING-001 (Loss Mask Construction)
**Owner Module/API**: `dbex.refinement.inputs.prepare_refinement_inputs`

**Contract**: Constructs `loss_mask = (background_image >= 0) ∧ trusted_mask` per spec-db-core.md:124. Background sentinel `-1` excludes pixels outside ROIs. Trusted mask boolean polarity: True=trusted, no inversion.

**Forbidden Duplicates**: Alternative loss_mask construction in:
- Stage A/B/C helpers (`dbex/refinement/stage_*_impl.py`)
- Test harness boilerplate (except direct DataLoad API calls for validation)
- Plan-local diagnostic scripts (must delegate to DataLoad API)

**Failure Classification**: Implementation bug within architecture (Phase A confirmed no duplicate construction detected; Phase B test will enforce precedence).

## Do Now (hard validity contract)

**Implement**: `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics`

Author 3 test methods per Phase B checklist (DB-AT-021 § Phase B):

**B1 — Test Scaffold**:
1. Create `tests/dbex/test_mask_semantics.py` with `TestDB_AT_021_MaskSemantics` class
2. Add `refgeom_dataload` fixture (or reuse from `tests/conftest.py` if exists):
   - Instantiate `DataLoad` with `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`
   - Apply `pytest.skip` guard when assets missing (mirror DB-AT-020 pattern)
3. Ensure test methods are discoverable via `-k DB_AT_021` selector pattern

**B2 — Mask Polarity Checks** (`test_polarity_checks`):
1. Load `747_mask.pkl` via `DataLoad` fixture
2. Assert `dataload.trusted_mask.dtype == bool` (DIALS convention)
3. Validate sample trusted pixel: `assert dataload.trusted_mask[0, 582, 594] == True` (ROI 0 coordinates from baseline probe)
4. Validate sample untrusted pixel (use baseline probe to identify untrusted coordinates if available, else skip)
5. Confirm no polarity inversion in production path

**B3 — Loss Mask Construction** (`test_loss_mask_construction`):
1. Extract `background_image` and `trusted_mask` from `DataLoad`
2. Compute expected: `expected_loss_mask = (background_image >= 0) & trusted_mask`
3. Extract actual from `RefinementInputs` (call `prepare_refinement_inputs` or inspect `DataLoad.loss_mask` if attribute exists)
4. Assert `torch.equal(actual_loss_mask, expected_loss_mask)` or numpy equivalent
5. Validate sentinel handling: assert pixels where `background == -1` are excluded from `loss_mask`
6. Validate trusted mask precedence: assert pixels where `trusted_mask == False` are excluded even if `background >= 0`

**B4 — ARCH-CONTRACT-MASKING-001 Enforcement** (`test_precedence_guards`):
1. Use AST or grep to search for duplicate `loss_mask` construction patterns in:
   - `dbex/refinement/stage_a_impl.py`
   - `dbex/refinement/stage_b_impl.py`
   - `dbex/refinement/stage_c_impl.py`
2. If duplicates found, raise `AssertionError` with file:line references
3. If no duplicates, assert canonical owner is `prepare_refinement_inputs` (validate via import inspection or doc cross-reference)
4. Document any exceptions in test comments with justification (if legacy paths exist, cross-ref to findings)

**Validation Commands**:
```bash
# Primary acceptance selector
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics -k DB_AT_021

# Collection validation (for Phase C registry sync)
pytest --collect-only tests -k DB_AT_021 > plans/active/DB-AT-021/reports/2025-12-08T150000Z/collect_db_at_021.log 2>&1
```

**Artifacts Destination**: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/`
- `pytest_db_at_021.log` (primary test run)
- `collect_db_at_021.log` (collection validation)
- `summary.md` (Phase B completion notes)

**Touched**: DB-AT-021 Phase B (B1, B2, B3)

## Forbidden This Loop
- **No production code edits** (harness type, test-only)
- **No fix_plan updates** until Phase C (per standard member plan pattern)
- **No new plan-local diagnostic scripts** (Phase A baseline probe sufficient)

## How-To Map

**Test Authoring Steps**:
1. Create `tests/dbex/test_mask_semantics.py`
2. Import `pytest`, `DataLoad`, `prepare_refinement_inputs` (if accessible)
3. Define `refgeom_dataload` fixture with skip guard (or reuse from conftest)
4. Author 3 test methods (B2, B3, B4) per specifications above
5. Run primary selector: `pytest -vv tests -k DB_AT_021`
6. Run collection validation: `pytest --collect-only tests -k DB_AT_021`
7. Capture both logs under artifacts directory
8. Author `summary.md` with test outcomes + metrics

**Expected Outcomes**:
- All 3 tests PASS (polarity, loss_mask construction, precedence guards all validate per spec)
- Collection log shows ≥3 tests collected with `-k DB_AT_021` pattern
- No ARCH-CONTRACT-MASKING-001 violations detected (canonical owner is sole source)

**Phase C Preview** (not this loop):
- Update `docs/TESTING_GUIDE.md` §2 with DB_AT_021 row (Active status, selector command, artifact path)
- Update `docs/development/TEST_SUITE_INDEX.md` with DB_AT_021 status
- Update `docs/fix_plan.md` Attempts History with Phase B outcomes
- Mark DB-AT-021 complete per implementation.md exit criteria

## Pitfalls To Avoid
1. **Polarity inversion**: Do NOT apply `~trusted_mask` or `1 - trusted_mask`; DIALS convention is True=trusted (direct polarity).
2. **Sentinel tolerance**: Background sentinel is `-1` (exact), not `< 0` (per ADR-07).
3. **Loss mask duplication**: Test must NOT re-implement `(background >= 0) & trusted_mask`; validate canonical owner only.
4. **Skip guard**: Fixture must `pytest.skip` when canonical assets missing (not fail/error).
5. **Selector pattern**: Test method names must include `DB_AT_021` substring for `-k DB_AT_021` discovery.
6. **Type discipline**: This is harness type (test-only); do NOT edit production modules under `dbex/` unless blocking test authoring.

## If Blocked
- **Missing DataLoad attribute**: If `DataLoad` lacks `trusted_mask` or `loss_mask` attributes, flag as architecture conformance issue and escalate to supervisor (ARCH-CONTRACT-DATA-LOAD-001 violation).
- **Duplicate loss_mask construction found**: Flag as ARCH-CONTRACT-MASKING-001 violation; escalate to supervisor with file:line evidence for conformance remediation.
- **Spec conflicts during test authoring**: If mask polarity or loss_mask formula contradicts Phase A spec alignment, halt and escalate to supervisor for spec_change type handling.
- **Asset unavailability**: If canonical assets deleted/moved since Phase B.2 validation, re-run asset availability check and update skip guard logic.

## Doc Sync Plan (Conditional)
**NOT REQUIRED THIS LOOP** — Test authoring (Phase B) does not trigger registry sync. Phase C (next loop) will execute:
1. Run `pytest --collect-only tests -k DB_AT_021` (already in validation commands above)
2. Store collection log: `plans/active/DB-AT-021/reports/2025-12-08T150000Z/collect_db_at_021.log`
3. Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` after tests PASS

---

**END OF INPUT.MD**
