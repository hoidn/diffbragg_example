# DB-AT-SUITE-CARE-001 Phase B.1 (Second Attempt) — Planning Notes

**Loop**: i=136 (Galph planning)
**Date**: 2025-12-07T204336Z
**Focus**: DB-AT-SUITE-CARE-001 Phase B.1 — DB-AT-010 Full Verification (Harness Now Clean)

---

## Context

### Previous Attempt (Loop i=133)
- **Outcome**: BLOCKED by test harness collection errors
- **Issues**: 2 import errors prevented test execution
  1. `test_nanobrag_smoke.py:30` — `prepare_refinement_inputs` moved to `dbex.refinement.inputs`
  2. `test_vis_triptych_smoke.py:7` — `plot_z_scores` renamed to `compute_z_scores`
- **Assets Status**: Phase B.2 complete — 4/4 canonical refGeom assets validated

### Resolution Chain (Loops i=134-135)
- **Loop i=134 (Phase B.3)**: Ralph fixed 2 import errors. Collection check: PASSED (0 errors).
- **Loop i=135 (Phase B.4)**: Ralph fixed 3 test signature bugs exposed by B.3. All tests: PASSED.

**Current State**: Test harness is clean. Ready to resume original Phase B.1 objective.

---

## Objective (Phase B.1 — Second Attempt)

Re-run DB-AT-010 with canonical flags to:
1. **Verify current test status** (PASSING or FAILING?)
2. **Document actual failure signature** (if failing: gradcheck crystal_cell_a regression still present?)
3. **Record exit code, pytest log, and classification** for member plan audit
4. **Unblock portfolio advancement** (determine if Tier-0 escalation still needed)

**Key Difference from i=133**: This time the test harness is clean, so tests will actually execute.

---

## Scope

### What Ralph Will Do

1. **Execute DB-AT-010 Full Verification**
   - Command (canonical flags per TESTING_GUIDE.md):
     ```bash
     env KMP_DUPLICATE_LIB_OK=TRUE \
         DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_verification/ \
         NANOBRAGG_DISABLE_COMPILE=1 \
         pytest -v tests -k DB_AT_010 --smoke-detector-size=full
     ```
   - Expected selector match: 5 tests collected (per i=133 pre-collection count)
   - Capture: exit code, full pytest log, artifact directory contents

2. **Classify Test Status**
   - **IF exit code 0** (all tests PASSED):
     - Classification: DB-AT-010 **PASSING** (previously reported gradcheck regression resolved)
     - Note: gradcheck `crystal_cell_a` failure was either fixed upstream or was false positive
   - **IF exit code 1** (tests FAILED):
     - Classification: DB-AT-010 **FAILING** (gradcheck regression still present)
     - Extract: failure signature, failing test name(s), assertion/error message, tolerance exceedance
   - **IF exit code 2** (collection errors):
     - Classification: **HARNESS ISSUE** (escalate to Phase B.3/B.4 continuation)
     - Unexpected: B.3/B.4 should have resolved all imports

3. **Document Findings**
   - Create `db_at_010_status_verification.md` with:
     - Test execution details (command, exit code, tests collected/selected/deselected)
     - Classification (PASSING / FAILING / HARNESS ISSUE)
     - Failure signature (if FAILING)
     - Conformance analysis (RUNTIME-001, TESTING-003, refGeom usage)
     - Next action recommendation (Tier-0 escalation OR Phase B advancement)

4. **Create Summary**
   - `summary.md` with:
     - Phase B.1 outcome (second attempt)
     - Key findings (test status, failure signature if any)
     - Portfolio implications (blocker resolved OR still blocking)
     - Next steps

---

## Expected Outcomes

### Best Case (Exit Code 0 — All Tests PASSED)
- **Implication**: DB-AT-010 gradcheck regression is resolved
- **Action**: Mark Phase B.1 complete, proceed to Phase B.3-B.5 (member plan audit/status updates)
- **Portfolio Impact**: Tier-0 blocker resolved, Gradient-Safe conformance profile unblocked

### Likely Case (Exit Code 1 — Gradcheck Failure Persists)
- **Implication**: DB-AT-010 Phase D gradcheck `crystal_cell_a` regression still present
- **Action**: Mark Phase B.1 complete (status verified), escalate to Tier-0 (per implementation.md Phase B.1 task description)
- **Portfolio Impact**: Tier-0 blocker confirmed, requires upstream TorchCrystal bridge audit or `.item()` coercion patch

### Worst Case (Exit Code 2 — Collection Errors Remain)
- **Implication**: Phase B.3/B.4 fixes incomplete or new import errors introduced
- **Action**: Debug new import errors, extend Phase B.3/B.4, re-attempt Phase B.1
- **Portfolio Impact**: Harness initiative extends, delays member plan audit

---

## Validation

**Success Criteria (This Loop)**:
- DB-AT-010 test execution completes (exit code 0 or 1, not 2)
- `db_at_010_status_verification.md` artifact exists with classification
- `summary.md` artifact exists with next action recommendation
- Pytest log captured in `db_at_010_verification/` directory

**Phase B.1 Completion Criteria** (per implementation.md):
- Test status verified (PASSING or FAILING documented)
- Failure signature extracted (if FAILING)
- Next action determined (Tier-0 escalation OR Phase B advancement)

---

## Risks & Mitigations

### Risk 1: New Import Errors (Probability: Low)
- **Mitigation**: Phase B.3/B.4 fixes covered both known import errors. Ralph ran full file regression checks.
- **Response**: If exit code 2, debug immediately and extend Phase B.3/B.4.

### Risk 2: Gradcheck Failure Signature Changed (Probability: Medium)
- **Mitigation**: Document exact failure signature from pytest log. Compare to original member plan audit notes.
- **Response**: If signature differs, note in findings and escalate with updated signature.

### Risk 3: Test Hangs (Probability: Low)
- **Mitigation**: Use pytest default timeout (~2 minutes per test). Kill after 10 minutes total if hung.
- **Response**: If hung, document timeout, mark HANGING instead of FAILING, escalate as separate harness issue.

---

## Pointers

### SPEC
- **docs/spec-db-conformance.md** — DB-AT-010 acceptance criteria (gradcheck contract)
- **docs/TESTING_GUIDE.md** — Canonical flags (`NANOBRAGG_DISABLE_COMPILE=1`, `--smoke-detector-size=full`)

### ARCH
- **plans/active/DB-AT-010/implementation.md** — Member plan details (Phase D gradcheck regression)
- **plans/active/DB-AT-SUITE-CARE-001/implementation.md** — Phase B.1 task definition

### FINDINGS
- **TESTING-003** (Acceptance test registry maintenance)
- **RUNTIME-001** (Runtime execution guardrails)

### PREVIOUS ARTIFACTS
- **i=133**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_status_verification.md` (collection errors, import issues)
- **i=134**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/summary.md` (Phase B.3 import fixes)
- **i=135**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/summary.md` (Phase B.4 signature fixes)

---

## Ralph's Do Now (Next Loop i=136)

Execute DB-AT-010 full verification with canonical flags, classify test status (PASSING/FAILING/HARNESS ISSUE), extract failure signature (if FAILING), and create 2 artifacts (`db_at_010_status_verification.md`, `summary.md`). Harness is now clean (B.3/B.4 complete), so tests should execute successfully (exit code 0 or 1).

**Mapped Tests**: `tests -k DB_AT_010` (5 tests expected, canonical flags per TESTING_GUIDE.md)

**Artifacts Path**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/`

**Expected Runtime**: ~5-10 minutes (5 tests, full detector size, no compile)

---

**Authored by**: Galph (Loop i=136)
**Branch**: integration
**Commit**: None yet (planning only)
