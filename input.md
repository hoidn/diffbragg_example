# Input for Ralph — Loop i=136

**Summary**: Re-run DB-AT-010 full verification (harness now clean after Phase B.3/B.4 fixes) to determine current test status and unblock portfolio advancement.

**Mode**: none

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: [DB-AT-SUITE-CARE-001] — Acceptance Suite Upkeep (DB-AT-002/010/020/021/022/023/024)

**Branch**: integration

**Mapped tests**: `tests -k DB_AT_010` (5 tests expected, canonical flags: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k DB_AT_010 --smoke-detector-size=full`)

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/`

---

## Findings Applied (Mandatory)

- **TESTING-003** (Acceptance test registry maintenance): Normative requirement for TEST_SUITE_INDEX.md updates when acceptance tests change status. This verification determines DB-AT-010's current status for registry sync.
  - Adherence: Document test status (PASSING/FAILING) in verification report; use for Phase C registry update.

- **RUNTIME-001** (Runtime execution guardrails): Acceptance tests must respect canonical environment flags per TESTING_GUIDE.md.
  - Code: `docs/TESTING_GUIDE.md` (canonical flags: `NANOBRAGG_DISABLE_COMPILE=1`, `--smoke-detector-size=full`)
  - Adherence: Use exact flags in pytest command; validate in verification report.

---

## ARCH Contracts (mandatory)

1. **ARCH-CONTRACT-TESTING-001** (Test harness import stability)
   - **Owner module/API**: `dbex.refinement.inputs::prepare_refinement_inputs`, `dbex.vis::compute_z_scores`
   - **Classification**: Implementation bug (Phase B.3/B.4 fixed import/signature drift)
   - **Pointers**: `docs/architecture.md` §Test Stability (test imports must match current API)

2. **ARCH-CONTRACT-REFGEOM-001** (Canonical refGeom asset locations)
   - **Owner module/API**: Workspace root assets (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`)
   - **Classification**: Implementation conformance (Phase B.2 validated all 4 assets exist)
   - **Pointers**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md`

3. **ARCH-CONTRACT-DB-AT-010** (Gradcheck crystal_cell_a acceptance)
   - **Owner module/API**: `tests/dbex/test_gradcheck_smoke.py::DB_AT_010` (selector contract)
   - **Classification**: TBD (this verification determines: implementation bug OR gradcheck contract relaxation needed)
   - **Pointers**: `docs/spec-db-conformance.md` §Gradient-Safe Profile, `plans/active/DB-AT-010/implementation.md` Phase D

---

## Pointers

### SPEC
- **docs/spec-db-conformance.md** — DB-AT-010 acceptance criteria (gradcheck contract)
- **docs/TESTING_GUIDE.md:45-78** — Canonical environment flags and selector patterns

### ARCH
- **plans/active/DB-AT-SUITE-CARE-001/implementation.md** — Phase B.1 task definition
- **plans/active/DB-AT-010/implementation.md** — Member plan details (Phase D gradcheck regression)
- **plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/planning_notes.md** — Loop context and validation criteria

### TESTING
- **docs/TESTING_GUIDE.md** — Canonical commands and artifact expectations
- **docs/development/TEST_SUITE_INDEX.md** — DB-AT-010 registry row (will be updated based on this verification)

---

## Do Now (hard validity contract)

**Phase B.1 — DB-AT-010 Full Verification (Second Attempt)**

1. **Execute DB-AT-010 test suite** with canonical flags:
   ```bash
   env KMP_DUPLICATE_LIB_OK=TRUE \
       DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_verification/ \
       NANOBRAGG_DISABLE_COMPILE=1 \
       pytest -v tests -k DB_AT_010 --smoke-detector-size=full \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/pytest_db_at_010_verification.log 2>&1
   ```

   Capture exit code:
   ```bash
   echo $? > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_exit_code.txt
   ```

2. **Classify test status** based on exit code:
   - Exit code 0: DB-AT-010 **PASSING** (gradcheck regression resolved)
   - Exit code 1: DB-AT-010 **FAILING** (extract failure signature from pytest log)
   - Exit code 2: **HARNESS ISSUE** (new collection errors, escalate)

3. **Extract failure signature** (if exit code 1):
   - Failing test name(s)
   - Assertion/error message
   - Gradcheck parameter (expect `crystal_cell_a`)
   - Tolerance exceedance value

4. **Create verification report** `db_at_010_status_verification.md`:
   - Test execution details (command, exit code, tests collected/selected/deselected)
   - Classification (PASSING / FAILING / HARNESS ISSUE)
   - Failure signature (if FAILING)
   - Conformance analysis (RUNTIME-001: canonical flags used, TESTING-003: refGeom assets referenced)
   - Next action recommendation:
     - IF PASSING: Proceed to Phase B.3-B.5 (member plan audit), Tier-0 blocker resolved
     - IF FAILING: Escalate to Tier-0 (TorchCrystal bridge audit per implementation.md Phase B.1)
     - IF HARNESS ISSUE: Extend Phase B.3/B.4 (new import errors)

5. **Create loop summary** `summary.md`:
   - Phase B.1 outcome (second attempt)
   - Key findings (test status, failure signature if any)
   - Portfolio implications (blocker resolved OR still blocking)
   - Artifacts list
   - Next steps

**Validation**:
- Exit code captured (0, 1, or 2)
- Pytest log exists in artifacts directory
- Verification report classifies test status
- Summary recommends next action

**Artifacts Path**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/`

---

## Forbidden This Loop

- No new probes (verification run only)
- No production code changes (harness verification, not implementation)
- Do not modify test files (Phase B.3/B.4 complete, treat as frozen)

---

## How-To Map

1. Change to repo root: `cd /home/ollie/Documents/diffbragg_example`

2. Execute DB-AT-010 verification command (single shell invocation with output redirect + exit code capture):
   ```bash
   env KMP_DUPLICATE_LIB_OK=TRUE \
       DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_verification/ \
       NANOBRAGG_DISABLE_COMPILE=1 \
       pytest -v tests -k DB_AT_010 --smoke-detector-size=full \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/pytest_db_at_010_verification.log 2>&1; \
   echo $? > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_exit_code.txt
   ```

3. Read exit code and pytest log to classify status

4. Write `db_at_010_status_verification.md` with classification and findings

5. Write `summary.md` with Phase B.1 outcome and next action recommendation

**Expected Runtime**: ~5-10 minutes (5 tests, full detector size, no compile)

---

## Pitfalls To Avoid

1. **Don't trust old member plan audit** — i=133 classification was based on collection errors, not actual test status. This loop determines real status.

2. **Capture exact failure signature** — If FAILING, document exact parameter, tolerance, observed vs expected values for upstream escalation.

3. **Validate canonical flags** — Ensure `NANOBRAGG_DISABLE_COMPILE=1` and `--smoke-detector-size=full` are used per TESTING_GUIDE.md.

4. **Don't confuse exit codes**:
   - 0 = all tests PASSED
   - 1 = tests FAILED (expected for known gradcheck regression)
   - 2 = collection errors (unexpected, Phase B.3/B.4 should have fixed)

5. **No implementation work this loop** — This is verification only. No code changes, no new tests, no probes.

6. **Follow parity-first interpretation** — If gradcheck fails, document signature but don't attempt fix. Escalate to Tier-0 per implementation.md Phase B.1 task.

7. **Respect type discipline** — DB-AT-010 gradcheck failure is a harness issue (test tolerance) or upstream issue (TorchCrystal bridge). Don't retype to spec_change without supervisor approval.

8. **No stacking on cliffs** — If exit code 2 (new collection errors), stop immediately and escalate. Don't attempt workarounds.

9. **Environment freeze** — No pip installs, no package upgrades. Treat missing imports as blockers per CLAUDE.md.

10. **Document, don't speculate** — Report test status factually. Avoid hypothesizing why gradcheck might fail. Upstream diagnosis is separate initiative.

---

## If Blocked

If exit code 2 (new collection errors):
- Record collection error details in verification report
- Mark Phase B.1 BLOCKED (harness issue)
- Recommend extending Phase B.3/B.4 to debug new import errors
- Do NOT attempt fixes this loop

If tests hang (>10 minutes):
- Kill pytest process
- Document timeout in verification report
- Mark Phase B.1 BLOCKED (test hang)
- Recommend separate debugging initiative

If pytest command fails to execute (e.g., environment issues):
- Document error in verification report
- Mark Phase B.1 BLOCKED (environment issue)
- Escalate to supervisor per CLAUDE.md environment freeze policy

---

## Doc Sync Plan (Conditional)

Not applicable this loop (verification only, no test changes).

Future: Phase C.3 will sync TEST_SUITE_INDEX.md based on this verification's test status classification.
