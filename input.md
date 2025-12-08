# Input for Ralph (Loop i=150)

## Summary
DB-AT-021 Phase C: Registry sync and documentation closure (docs-only)

## Mode
Docs

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
- `pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics -k DB_AT_021` (regression check)
- `pytest --collect-only tests -k DB_AT_021` (collection validation)

## Artifacts
`plans/active/DB-AT-021/reports/2025-12-08T170000Z/`

## Findings Applied (Mandatory)
- **TESTING-003** (Selector status transitions only after pytest --collect-only confirms >0 tests): Phase C will validate collection before updating TEST_SUITE_INDEX.md. ✅ Applied — Phase B collection log confirms 3 tests.
- **CONFORMANCE-001** (DB-AT parity selectors use `-k DB_AT_0XX` pattern): Test method naming follows `test_DB_AT_021_*` convention. ✅ Applied — Phase B scaffold conforms.
- **MASKING-001** (Loss mask coverage <1% is expected for sparse Bragg peaks): Registry entry must NOT flag low coverage as failure. ✅ Applied — will document in TEST_SUITE_INDEX.md notes.

**No blocking findings** — Phase C is docs-only; all implementation complete in Phase B.

## Pointers

### Spec/Arch/Testing Docs
- **Spec**: `docs/spec-db-core.md:124` (loss_mask normative formula)
- **Spec**: `docs/spec-db-conformance.md:58-61` (DB-AT-021 acceptance criteria)
- **DIALS API**: `docs/dials_api.md:45-62` (mask polarity conventions)
- **Architecture**: `docs/architecture.md:165-178` (mask precedence + ADR-07)
- **Testing Guide**: `docs/TESTING_GUIDE.md` §2 (canonical pytest selectors + Active test status registry)
- **Test Suite Index**: `docs/development/TEST_SUITE_INDEX.md` (comprehensive test metadata registry)

### Fix Plan
- `docs/fix_plan.md` line 267-289 (DB-AT-SUITE-CARE-001 § Attempts History)

### Implementation Plan
- `plans/active/DB-AT-021/implementation.md` Phase C checklist (C1, C2, C3)

### Phase B Artifacts (Evidence for Registry Sync)
- `plans/active/DB-AT-021/reports/2025-12-08T150000Z/summary.md` (Phase B completion: 3/3 tests PASSED)
- `plans/active/DB-AT-021/reports/2025-12-08T150000Z/pytest_db_at_021.log` (primary test run, 4.02s)
- `plans/active/DB-AT-021/reports/2025-12-08T150000Z/collect_db_at_021.log` (3 tests collected)

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-MASKING-001 (Loss Mask Construction)
**Owner Module/API**: `dbex.refinement.inputs.prepare_refinement_inputs`

**Contract**: Constructs `loss_mask = (background_image >= 0) ∧ trusted_mask` per spec-db-core.md:124. Background sentinel `-1` excludes pixels outside ROIs. Trusted mask boolean polarity: True=trusted, no inversion.

**Forbidden Duplicates**: Alternative loss_mask construction in Stage A/B/C helpers (validated by Phase B test_DB_AT_021_precedence_guards).

**Failure Classification**: No conformance failure detected (Phase B test PASSED with 0 duplicates found).

## Do Now (hard validity contract)

**Implement**: Registry sync for `tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics` (docs-only, no production code changes)

Execute 3 Phase C tasks per implementation.md checklist (DB-AT-021 § Phase C):

**C1 — Evidence Capture**:
1. Run regression check to validate Phase B tests still pass:
   ```bash
   DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1 \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics -k DB_AT_021
   ```
   Capture output to `plans/active/DB-AT-021/reports/2025-12-08T170000Z/pytest_db_at_021_regression.log`

2. Run collection validation to confirm selector pattern functional:
   ```bash
   DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1 \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   pytest --collect-only tests -k DB_AT_021
   ```
   Capture output to `plans/active/DB-AT-021/reports/2025-12-08T170000Z/collect_db_at_021.log`

**Expected Outcomes**:
- Regression check: 3 passed, 4 warnings, ~4s runtime (match Phase B metrics)
- Collection validation: 3/181 tests collected (178 deselected), selector pattern confirmed functional

**C2 — Docs Update**:
1. **Update `docs/development/TEST_SUITE_INDEX.md`**:
   - Add DB-AT-021 row after DB-AT-020 row (maintain numerical ordering)
   - Columns to populate:
     - **Selector**: `DB-AT-021`
     - **Status**: `Active`
     - **Description**: `Mask semantics guard (polarity, loss_mask construction, ARCH-CONTRACT-MASKING-001 precedence)`
     - **Spec References**: `docs/spec-db-core.md:124`, `docs/dials_api.md:45-62`, `docs/architecture.md:165-178`
     - **Canonical Command**: `DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1 DBEX_SMOKE_DETECTOR_SIZE=full AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_mask_semantics.py::TestDB_AT_021_MaskSemantics -k DB_AT_021`
     - **Environment Flags**: `DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1`, `DBEX_SMOKE_DETECTOR_SIZE=full`, `KMP_DUPLICATE_LIB_OK=TRUE`
     - **Artifact Path**: `plans/active/DB-AT-021/reports/2025-12-08T170000Z/`
     - **Runtime Estimate**: `~4s`
     - **Applied Findings**: `MASKING-001, TESTING-003, CONFORMANCE-001, DIALS-API polarity`
     - **Skip Behavior**: `test skips when refGeom.expt/refGeom.refl missing (mirrors smoke fixture guard)`

2. **Update `docs/TESTING_GUIDE.md` §2 (Test Taxonomy)**:
   - Locate "Mask semantics guard" entry (if exists) or add new entry after Reflection ingestion section
   - Update with:
     - Test names: `test_DB_AT_021_polarity_checks`, `test_DB_AT_021_loss_mask_construction`, `test_DB_AT_021_precedence_guards`
     - Canonical metrics (from Phase B summary.md):
       - Trusted pixels: 5,696,996 (91.5%)
       - Loss mask pixels: 13,084 (0.2% coverage — sparse Bragg peaks expected per MASKING-001)
       - Duplicates found: 0 (ARCH-CONTRACT-MASKING-001 enforcement)
     - Skip guard documentation: test skips when refGeom assets missing
     - Artifact path: `plans/active/DB-AT-021/reports/2025-12-08T170000Z/`

**C3 — Ledger Sync**:
1. **Update `docs/fix_plan.md` § [DB-AT-SUITE-CARE-001] Attempts History**:
   - Add new entry after line 288 (DB-AT-020 Phase C entry):
     ```
     * 2025-12-08T170000Z (Loop i=150, Ralph) — DB-AT-021 Phase C complete: Registry sync executed (TEST_SUITE_INDEX.md + TESTING_GUIDE.md updated with Active status, canonical commands, artifact paths). Regression check PASSED (3 tests: polarity checks, loss_mask construction, ARCH-CONTRACT-MASKING-001 precedence guards). Collect-only verification confirmed selector pattern (-k DB_AT_021) functional (3 tests collected: test_DB_AT_021_polarity_checks, test_DB_AT_021_loss_mask_construction, test_DB_AT_021_precedence_guards). Member plan closure complete; ready for DB-AT-SUITE-CARE-001 Phase B.4 coordination. Touched: DB-AT-021 Phase C (C1, C2, C3). Tests: pytest -vv tests -k DB_AT_021 (PASSED, ~4s); pytest --collect-only tests -k DB_AT_021 (3 selected). Artifacts: plans/active/DB-AT-021/reports/2025-12-08T170000Z/ (pytest_db_at_021_regression.log, collect_db_at_021.log, summary.md).
     ```

2. **Update `plans/active/DB-AT-021/implementation.md`**:
   - Mark Phase C tasks (C1/C2/C3) complete with checkmarks
   - Add timestamp: `✅ 2025-12-08 (Loop i=150)`

**Artifacts Destination**: `plans/active/DB-AT-021/reports/2025-12-08T170000Z/`
- `pytest_db_at_021_regression.log` (regression check)
- `collect_db_at_021.log` (collection validation)
- `summary.md` (Phase C completion notes including doc changes summary)

**Touched**: DB-AT-021 Phase C (C1, C2, C3)

## Forbidden This Loop
- **No production code edits** (docs-only per Mode: Docs)
- **No new test authoring** (Phase B complete)
- **No plan-local diagnostic scripts** (not needed for registry sync)

## How-To Map

**Registry Sync Steps**:
1. Create artifacts directory: `mkdir -p plans/active/DB-AT-021/reports/2025-12-08T170000Z/`
2. Run regression check (pytest command from C1), capture log
3. Run collection validation (pytest --collect-only from C1), capture log
4. Update TEST_SUITE_INDEX.md (add DB-AT-021 row with all metadata)
5. Update TESTING_GUIDE.md §2 (add/update Mask semantics entry)
6. Update fix_plan.md Attempts History (add DB-AT-021 Phase C entry at line ~289)
7. Update implementation.md Phase C checklist (mark C1/C2/C3 complete)
8. Author summary.md with test outcomes + doc changes summary

**Expected Doc Diff Summary**:
- `docs/development/TEST_SUITE_INDEX.md`: +1 row (DB-AT-021)
- `docs/TESTING_GUIDE.md` §2: +1 entry or updated existing Mask semantics entry
- `docs/fix_plan.md`: +1 Attempts History entry (~289)
- `plans/active/DB-AT-021/implementation.md`: Phase C tasks marked complete

**Success Criteria**:
- Regression check PASSES (3/3 tests)
- Collection validation shows 3 tests collected
- TEST_SUITE_INDEX.md DB-AT-021 row has all required columns populated
- fix_plan.md Attempts History entry includes metrics + artifact path

## Pitfalls To Avoid
1. **Stale metrics**: Use Phase B actual metrics (5.7M trusted pixels, 13K loss_mask pixels), not placeholder values.
2. **Registry inconsistency**: Ensure TEST_SUITE_INDEX.md and TESTING_GUIDE.md both reference same artifact path (2025-12-08T170000Z).
3. **Ledger insertion point**: Add DB-AT-021 entry AFTER DB-AT-020 entry (line 288) to maintain chronological ordering.
4. **Skip guard documentation**: Mirror DB-AT-020 pattern (skip when assets missing, not fail/error).
5. **Type discipline**: This is docs-only (Mode: Docs); do NOT edit production modules under `dbex/` or `tests/` (except implementation.md checklist).

## If Blocked
- **Regression check fails**: If Phase B tests now fail, halt and escalate to supervisor with pytest log (potential environment drift or test flakiness).
- **Collection validation shows ≠3 tests**: If collect-only discovers different test count, halt and escalate (test discovery regression).
- **Doc template mismatch**: If TEST_SUITE_INDEX.md or TESTING_GUIDE.md schema differs from DB-AT-020 pattern, consult existing rows and adapt format to match.

## Doc Sync Plan (Conditional)
**REQUIRED THIS LOOP** — Phase C execution (registry sync):
1. Run `pytest --collect-only tests -k DB_AT_021` (already in C1 validation commands)
2. Store collection log: `plans/active/DB-AT-021/reports/2025-12-08T170000Z/collect_db_at_021.log`
3. Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` per C2 specifications

---

**END OF INPUT.MD**
