# Input for Ralph (Loop i=152)

## Summary
DB-AT-022 Phase B.3 + Phase C: Test execution + Registry sync (Combined closure loop)

## Mode
Parity

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
harness

## Focus
DB-AT-022 — Background Sentinel Guard (Member of DB-AT-SUITE-CARE-001)

## Branch
integration

## Mapped Tests
- `KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_background_semantics.py -k DB_AT_022` (3 tests, expect PASS)
- `pytest --collect-only tests -k DB_AT_022` (expect 3 collected)

## Artifacts
`plans/active/DB-AT-022/reports/2025-12-08T200000Z/`

## Findings Applied (Mandatory)
- **MASKING-001** (Mask handling contracts): Sentinel -1 excluded from loss mask via `background >= 0` guard. ✅ Validated by Phase A probes and test implementation.
- **TESTING-003** (Selector status transitions): Registry updates this loop after tests confirmed PASSED. ✅ Applied — update TESTING_GUIDE.md + TEST_SUITE_INDEX.md.
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Structured artifacts archived under reports directory. ✅ Applied — artifacts scoped below.

**No blocking findings** — Phase B.3 + Phase C combined closure.

## Pointers

### Spec/Arch/Testing Docs
- **Spec**: `docs/spec-db-workflow.md:38` (background sentinels −1 MUST be masked consistently)
- **Spec**: `docs/spec-db-conformance.md:63-64` (DB-AT-022 acceptance: sentinel logic correct, ROI coverage matches metadata)
- **Arch**: `docs/architecture/data_telemetry_flow.md:34` (Background sentinel: −1 outside ROI; validated before prep)
- **Code**: `dbex/refinement/inputs.py:145-186` (Sentinel guard implementation)
- **Testing Guide**: `docs/TESTING_GUIDE.md` §2 (canonical pytest selectors)
- **Test Suite Index**: `docs/development/TEST_SUITE_INDEX.md` (test metadata registry)

### Fix Plan
- `docs/fix_plan.md` line 267-291 (DB-AT-SUITE-CARE-001 § Attempts History)

### Implementation Plan
- `plans/active/DB-AT-022/implementation.md` Phase B.3, Phase C checklist

### Phase A Evidence (Cross-Reference)
- `plans/active/DB-AT-022/reports/2025-12-08T180000Z/summary.md` (Phase A complete: 3/3 tasks done)
- `plans/active/DB-AT-022/reports/2025-12-08T180000Z/sentinel_probe.md` (Case A: Perfect match)

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-SENTINEL-001 (Background Sentinel Convention)
**Owner Module/API**: `dbex.refinement.inputs::prepare_refinement_inputs` (lines 145-186)

**Contract**: Background image uses −1 sentinel outside ROIs; loss mask excludes sentinel pixels via `background >= 0` guard.

**Enforcement**: Guard raises `ValueError` with actionable message when:
- Sentinel pixels (≤ -0.5) found inside ROI union
- Non-sentinel pixels (significantly different from -1) found outside ROI union

**Failure Classification**: No conformance failure — tests PASS per Galph i=152 pre-verification.

## Do Now (hard validity contract)

**Implement**: Combined Phase B.3 + Phase C closure for DB-AT-022 (docs-only after test confirmation)

Execute 2 tasks per implementation.md checklist:

**B3 — Test Execution & Artifact Capture**:
1. Run DB-AT-022 selectors with canonical flags:
   ```bash
   mkdir -p plans/active/DB-AT-022/reports/2025-12-08T200000Z/
   KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full \
     pytest -vv tests/dbex/test_background_semantics.py -k DB_AT_022 \
     2>&1 | tee plans/active/DB-AT-022/reports/2025-12-08T200000Z/pytest_db_at_022.log
   ```

2. Capture collect-only evidence:
   ```bash
   pytest --collect-only tests -k DB_AT_022 \
     2>&1 | tee plans/active/DB-AT-022/reports/2025-12-08T200000Z/collect_db_at_022.log
   ```

3. Verify **3/3 PASSED** (expected per Galph pre-verification):
   - `test_DB_AT_022_sentinel_complement`
   - `test_DB_AT_022_guard_enforcement`
   - `test_DB_AT_022_roi_coverage_metrics`

**Expected Outcome**: 3/3 tests PASSED, logs archived.

**C1-C3 — Registry Sync & Ledger Update**:
1. Update `docs/TESTING_GUIDE.md` §2 with DB-AT-022 entry:
   - Selector: `pytest -k DB_AT_022`
   - Required flags: `DBEX_SMOKE_DETECTOR_SIZE=full`
   - Status: Active
   - Artifact path: `plans/active/DB-AT-022/reports/2025-12-08T200000Z/`

2. Update `docs/development/TEST_SUITE_INDEX.md` with DB-AT-022 row:
   - Test module: `tests/dbex/test_background_semantics.py`
   - Selector pattern: `DB_AT_022`
   - Test count: 3
   - Status: Active
   - Applied Findings: MASKING-001, TESTING-003, DIAGNOSTICS-001

3. Update `docs/fix_plan.md` Attempts History:
   - Add loop i=152 entry under DB-AT-SUITE-CARE-001
   - Record test outcomes (3/3 PASSED)
   - Mark DB-AT-022 Phase B.3 + Phase C complete
   - Note DB-AT-022 initiative ready for closure

4. Update `plans/active/DB-AT-022/implementation.md`:
   - Mark B3, C1, C2, C3 complete with timestamps/loop references

5. Author `summary.md` in artifacts directory with:
   - Phase B.3 test results
   - Phase C registry sync confirmation
   - DB-AT-022 initiative closure readiness

**Artifacts Destination**: `plans/active/DB-AT-022/reports/2025-12-08T200000Z/`
- `pytest_db_at_022.log` (B3: full test output)
- `collect_db_at_022.log` (B3: collection verification)
- `summary.md` (combined Phase B.3 + C closure notes)

**Touched**: DB-AT-022 Phase B.3 (B3), Phase C (C1, C2, C3)

## Forbidden This Loop
- **No production code edits** (Phase B.3 + C is docs/registry sync only)
- **No new diagnostic scripts** (Phase A probes complete)

## How-To Map

**Phase B.3 + C Steps**:
1. Create artifacts directory (if not exists)
2. Execute pytest with canonical flags, tee output to log
3. Execute collect-only, tee output to log
4. Verify 3/3 PASSED
5. Update TESTING_GUIDE.md §2 with DB-AT-022 entry
6. Update TEST_SUITE_INDEX.md with DB-AT-022 row
7. Update fix_plan.md Attempts History
8. Update implementation.md (mark B3, C1-C3 complete)
9. Author summary.md

**Success Criteria**:
- 3/3 tests PASSED (pytest log confirms)
- 3 tests collected (collect-only log confirms)
- TESTING_GUIDE.md updated with DB-AT-022 entry
- TEST_SUITE_INDEX.md updated with DB-AT-022 row
- fix_plan.md Attempts History entry added
- implementation.md Phase B.3 + C marked complete
- summary.md authored

## Pitfalls To Avoid
1. **Missing env flag**: Always use `DBEX_SMOKE_DETECTOR_SIZE=full` for DB-AT selectors
2. **Incomplete logs**: Tee both pytest and collect-only output to artifact directory
3. **Registry drift**: Ensure TESTING_GUIDE.md and TEST_SUITE_INDEX.md match actual selector patterns
4. **Stale implementation.md**: Update checkboxes with loop number and timestamp

## If Blocked
- **Tests fail unexpectedly**: Capture full log, document failure signature in summary.md, escalate to supervisor (likely environment or asset drift)
- **Registry file locked/missing**: Note error, proceed with available docs, escalate remaining

---

**END OF INPUT.MD**
