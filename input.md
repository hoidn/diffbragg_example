# Input for Ralph (Loop i=147)

**Summary**: DB-AT-020 Phase C registry sync & documentation (close out reflection ingestion acceptance test)

**Mode**: Docs

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: [DB-AT-020] — Reflection Ingestion Sanity

**Branch**: integration

**Mapped tests**:
- `pytest --collect-only tests -k DB_AT_020` (registry verification)
- `pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox` (regression check)

**Artifacts**: `plans/active/DB-AT-020/reports/2025-12-08T100000Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** (Acceptance test registry maintenance): Phase C registry sync is normative requirement; update `docs/development/TEST_SUITE_INDEX.md` row for DB-AT-020 with status=Active, spec refs, canonical command, artifact paths ✓
- **CONFORMANCE-001** (Acceptance test patterns): Ensure DB-AT-020 follows canonical selector pattern (`-k DB_AT_020`) and refGeom skip guards per spec-db-conformance.md ✓
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Validate Phase C artifacts include pytest logs + collect-only output under initiative reports/ directory ✓

**ARCH Contracts (mandatory)**:

1. **ARCH-CONTRACT-DATA-LOAD-001** (Canonical DataLoad API)
   - **Owner**: `dbex/data_load.py::DataLoad` class
   - **Classification**: Implementation bug within architecture (test validates owner API correctly)
   - **Relevant sections**: `docs/spec-db-core.md:22` (bbox exclusivity), `docs/dials_api.md:10-32` (reflection schema)

2. **TESTING-003** (Test registry synchronization)
   - **Owner**: `docs/development/TEST_SUITE_INDEX.md` + `docs/TESTING_GUIDE.md`
   - **Classification**: Implementation bug (registry out of sync with test reality)
   - **Relevant sections**: `docs/findings.md:TESTING-003`, `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md`

3. **ARCH-CONTRACT-CONFORMANCE-PROFILE-001** (Workflow Integration Profile)
   - **Owner**: `docs/spec-db-conformance.md` § Workflow Integration Profile
   - **Classification**: Implementation complete, documentation update required
   - **Relevant sections**: DB-AT-SUITE-CARE-001 implementation.md Phase C2

---

## Do Now

**Implement**: Phase C documentation updates (no production code changes)

1. **C1 — Evidence capture**:
   - Run `pytest -v tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox` (regression check, expect PASS)
   - Run `pytest --collect-only tests -k DB_AT_020` (registry verification)
   - Archive both logs under `plans/active/DB-AT-020/reports/2025-12-08T100000Z/`

2. **C2 — Docs update**:
   - Update `docs/development/TEST_SUITE_INDEX.md`:
     - Find DB-AT-020 row (if exists) or add new row
     - Set status: `Active`
     - Add spec references: `spec-db-core.md:22`, `dials_api.md:10-32`, `architecture.md:122`
     - Add canonical command: `DBEX_SMOKE_DETECTOR_SIZE=full AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`
     - Add environment flags: `DBEX_SMOKE_DETECTOR_SIZE=full`, `KMP_DUPLICATE_LIB_OK=TRUE`
     - Add artifact path: `plans/active/DB-AT-020/reports/2025-12-08T100000Z/`
     - Add runtime estimate: `~1.2s` (from Phase B pytest log)
     - Add applied findings: `TESTING-003`, `CONFORMANCE-001`, `MASKING-001`

   - Update `docs/TESTING_GUIDE.md` §2 (Acceptance Test Selectors):
     - Add DB-AT-020 entry with selector pattern: `-k DB_AT_020`
     - Cross-reference TEST_SUITE_INDEX.md for full metadata
     - Note skip behavior: test skips if `refGeom.refl` missing (mirrors smoke fixture guard per `tests/dbex/conftest.py::refgeom_dataload`)

3. **C3 — Ledger sync**:
   - Update `docs/fix_plan.md` § [DB-AT-SUITE-CARE-001] Attempts History:
     - Add entry: `2025-12-08T100000Z (Loop i=147, Ralph) — DB-AT-020 Phase C complete: Registry sync executed (TEST_SUITE_INDEX.md + TESTING_GUIDE.md updated with Active status, canonical commands, artifact paths). Regression check PASSED (92 ROIs, bbox/panel assertions green). Collect-only verification confirmed selector pattern (-k DB_AT_020) functional. Member plan closure complete; ready for DB-AT-SUITE-CARE-001 Phase B.4 coordination. Artifacts: plans/active/DB-AT-020/reports/2025-12-08T100000Z/ (pytest_db_at_020_regression.log, collect_db_at_020.log, summary.md).`

   - Update `plans/active/DB-AT-020/implementation.md`:
     - Mark Phase C tasks (C1/C2/C3) complete with checkmarks + timestamp `✅ 2025-12-08 (Loop i=147)`

4. **Create summary.md**:
   - Write `plans/active/DB-AT-020/reports/2025-12-08T100000Z/summary.md`:
     - Document Phase C completion (all tasks done)
     - Note pytest outcomes (regression PASS, collect-only verified)
     - List doc updates (2 files modified: TEST_SUITE_INDEX.md, TESTING_GUIDE.md)
     - Provide next steps: DB-AT-020 ready for closure; DB-AT-SUITE-CARE-001 Phase B.4 can proceed with next member plan

**Validating pytest selectors**:
- Primary: `pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox` (regression check)
- Secondary: `pytest --collect-only tests -k DB_AT_020` (registry verification)

**Touched**: DB-AT-020 Phase C (C1, C2, C3)

**Forbidden This Loop**:
- No production code changes (docs-only loop per Mode: Docs)
- Do not extend plan-local diagnostic scripts
- Do not run full test suite (only DB-AT-020 selectors)

---

## How-To Map

**Environment**:
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_DETECTOR_SIZE=full
export KMP_DUPLICATE_LIB_OK=TRUE
```

**Commands**:
```bash
# C1 - Regression check
cd /home/ollie/Documents/diffbragg_example
pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox \
  | tee plans/active/DB-AT-020/reports/2025-12-08T100000Z/pytest_db_at_020_regression.log

# C1 - Collect-only verification
pytest --collect-only tests -k DB_AT_020 \
  | tee plans/active/DB-AT-020/reports/2025-12-08T100000Z/collect_db_at_020.log
```

**Doc update targets**:
- `docs/development/TEST_SUITE_INDEX.md` (add/update DB-AT-020 row)
- `docs/TESTING_GUIDE.md` §2 (add DB-AT-020 selector entry)
- `docs/fix_plan.md` § [DB-AT-SUITE-CARE-001] Attempts History (append entry)
- `plans/active/DB-AT-020/implementation.md` (mark Phase C complete)

**Artifact destinations**:
- All pytest logs → `plans/active/DB-AT-020/reports/2025-12-08T100000Z/`
- Summary markdown → `plans/active/DB-AT-020/reports/2025-12-08T100000Z/summary.md`

---

## Pitfalls To Avoid

1. **Type discipline**: This is harness work (registry sync); do not retype to feature/bugfix/perf
2. **No stacking**: Phase B passed; this is clean closure work (no cliff, no parity localization needed)
3. **Evidence→Action**: Phase B provided concrete metrics (92 ROIs, 12×12 dimensions, 100% conformance); Phase C documents those in registry
4. **Findings paydown**: TESTING-003 explicitly requires registry sync; this loop satisfies that requirement
5. **Implementation floor**: After docs-only loop, DB-AT-020 must be marked complete or justify why not
6. **No shadow pipelines**: This is pure docs work; no new scripts allowed
7. **Probe saturation**: N/A (docs-only, no probes)
8. **SYNC must close**: No SYNC occurred; this reminder is not applicable
9. **Repeat-signature freeze**: N/A (first Phase C loop for this selector)
10. **Environment freeze**: No package installs; only doc file edits + pytest runs

---

## If Blocked

- If pytest regression fails: investigate failure signature, compare to Phase B baseline (92 ROIs, bbox assertions), escalate if DataLoad API changed
- If collect-only shows 0 collected items: verify test file name/path, check if refGeom.refl missing (expected skip), document in summary.md
- If TEST_SUITE_INDEX.md schema unclear: consult `docs/development/testing_strategy.md` §2.6 for row format examples
- If TESTING_GUIDE.md §2 missing: create new section "DB-AT Acceptance Test Selectors" with DB-AT-020 as first entry

---

## Pointers

**SPEC**:
- `docs/spec-db-conformance.md` § DB-AT-020 (acceptance criteria)
- `docs/spec-db-core.md:22` (bbox exclusivity)
- `docs/dials_api.md:10-32` (reflection schema)

**ARCH**:
- `docs/architecture.md:122` (DataLoad runtime guards)
- `plans/active/DB-AT-SUITE-CARE-001/implementation.md` (roll-up context)

**Testing Docs**:
- `docs/TESTING_GUIDE.md` (canonical commands, environment flags)
- `docs/development/TEST_SUITE_INDEX.md` (registry schema)
- `docs/development/testing_strategy.md` §2.6 (acceptance test patterns)

**Fix Plan**:
- `docs/fix_plan.md:249-270` (DB-AT-SUITE-CARE-001 section)
- `plans/active/DB-AT-020/implementation.md` (member plan phases)
- `plans/active/DB-AT-020/reports/2025-12-08T070000Z/summary.md` (Phase B completion evidence)
