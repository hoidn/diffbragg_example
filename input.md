# Input for Ralph — Loop i=154

## Summary
Close DB-AT-SUITE-CARE-001 Phase B (Workflow Integration cluster complete) and prepare Phase C conformance certification.

## Mode
none

## ActionType
review_or_housekeeping

## DecisionStatus
validated

## InitiativeType
harness

## Focus
DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep (Phase B Closure)

## Branch
integration

## Mapped tests
- `pytest -v tests -k "DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024"` — Workflow Integration Profile (13 tests)

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/`

## Findings Applied (Mandatory)
- **TESTING-003**: Registry updates validated; all 5 Workflow Integration selectors are Active in TESTING_GUIDE.md
- **RUNTIME-001**: Environment flags documented (`KMP_DUPLICATE_LIB_OK=TRUE`, `DBEX_SMOKE_DETECTOR_SIZE=full`, `NANOBRAGG_DISABLE_COMPILE=1`)
- **DIAGNOSTICS-001**: Artifact structure follows standard pattern
- **CONFORMANCE-001**: All 5 member plans meet spec-db-conformance.md criteria

## Pointers

### SPEC
- `docs/spec-db-conformance.md:55-76` — Workflow Integration Profile (DB-AT-020/021/022/023/024)
- `docs/spec-db-workflow.md` — Calibration policy, mask semantics, bbox conventions
- `docs/spec-db-core.md` — Loss mask, background sentinel, ROI conventions

### ARCH
- `docs/TESTING_GUIDE.md:157-160` — Selector registry (all 5 selectors Active)
- `docs/development/TEST_SUITE_INDEX.md` — Selector metadata

### Plan
- `plans/active/DB-AT-SUITE-CARE-001/implementation.md` — Roll-up phases
- `docs/fix_plan.md:267-292` — DB-AT-SUITE-CARE-001 ledger entry

### Member Plans (Complete)
- `plans/active/DB-AT-020/implementation.md` — Reflection ingestion (complete i=147)
- `plans/active/DB-AT-021/implementation.md` — Mask semantics (complete i=150)
- `plans/active/DB-AT-022/implementation.md` — Background sentinel (complete i=152)
- `plans/active/DB-AT-023/implementation.md` — Calibration policy (complete November 2025, re-validated i=153)
- `plans/active/DB-AT-024/implementation.md` — Mapping consistency (active, tests pass)

## ARCH Contracts (mandatory)

1. **ARCH-CONTRACT-WORKFLOW-INTEGRATION-001** (Workflow Integration Profile)
   - Doc: `docs/spec-db-conformance.md:55-76`
   - Owner: `tests/dbex/test_reflection_ingestion.py`, `test_mask_semantics.py`, `test_background_semantics.py`, `test_calibration_policy.py`, `test_mapping_consistency.py`
   - Classification: Implementation conforms (13/13 tests PASS)

## Do Now (hard validity contract)

Execute **DB-AT-SUITE-CARE-001 Phase B Closure**:

1. **Implement:** Update `plans/active/DB-AT-SUITE-CARE-001/implementation.md`
   - Mark Phase B tasks B.4, B.5, B.6, B.7 as complete

2. **Validation: Workflow Integration Profile pytest**
   ```bash
   mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z
   KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full \
     DBAT024_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/db_at_024 \
     NANOBRAGG_DISABLE_COMPILE=1 \
     pytest -v tests -k "DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024" \
     2>&1 | tee plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/pytest_workflow_integration.log
   ```

3. **Create Phase B closure summary** at `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/phase_b_closure.md`:
   - Member plan status: DB-AT-020 (complete), DB-AT-021 (complete), DB-AT-022 (complete), DB-AT-023 (complete), DB-AT-024 (complete)
   - Test results: 13/13 PASSED
   - Blockers: B.1 (DB-AT-010 gradcheck) remains escalated to ARCH-GRADIENT-FLOW-001 (blocked_pending_environment)
   - Phase C readiness: Workflow Integration Profile ready for certification

4. **Update fix_plan.md Attempts History** for DB-AT-SUITE-CARE-001:
   - Add entry for Phase B closure
   - Note: Phase B.4/B.5/B.6/B.7 complete
   - Note: Workflow Integration Profile (13/13 PASS)
   - Next: Phase C conformance certification

5. **Artifacts:** Create files under `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/`:
   - `pytest_workflow_integration.log` — Full pytest output
   - `phase_b_closure.md` — Phase B summary and Phase C scope
   - `summary.md` — Loop summary

## Validation (Supervisor Pre-verified)

The following was validated by Galph before authoring this input.md:

| Selector | Tests | Status | Runtime |
|----------|-------|--------|---------|
| DB_AT_020 | 2 | PASSED | ~1s |
| DB_AT_021 | 3 | PASSED | ~4s |
| DB_AT_022 | 3 | PASSED | ~2s |
| DB_AT_023 | 4 | PASSED | ~8s |
| DB_AT_024 | 1 | PASSED | ~44s |
| **Total** | **13** | **PASSED** | **~60s** |

## How-To Map

```bash
# Step 1: Create artifact directory
mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z

# Step 2: Run Workflow Integration Profile pytest
KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full \
  DBAT024_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/db_at_024 \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -v tests -k "DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024" \
  2>&1 | tee plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/pytest_workflow_integration.log

# Step 3: Update implementation.md (mark B.4-B.7 complete)
# Step 4: Create phase_b_closure.md summary
# Step 5: Update fix_plan.md Attempts History
```

## Pitfalls To Avoid

1. **Do not run DB-AT-002 or DB-AT-010** — These are in different profiles (Determinism, Gradient-Safe); B.1 escalation to ARCH-GRADIENT-FLOW-001 is separate
2. **Use DBAT024_ARTIFACT_DIR** — DB-AT-024 skips without this environment variable
3. **Use DBEX_SMOKE_DETECTOR_SIZE=full** — Required by pytest setup guard for DB-AT selectors
4. **Do not claim full conformance** — Gradient-Safe profile (DB-AT-010) remains blocked
5. **Update implementation.md checkboxes** — Mark B.4-B.7 as `[x]`
6. **Include pytest log in artifacts** — Required for Phase C certification evidence

## If Blocked

- If pytest fails: capture full log, analyze failure signature, determine if test regression or environment issue
- If environment issue: record with `blocked_pending_environment` flag
- If test regression: create bug fix item in fix_plan.md, mark Phase B blocked

## Forbidden This Loop

- no new probes
- do not extend plan-local diagnostic scripts
- do not modify production code

## Phase C Preview (Next Loop)

Phase C (Conformance Profile Certification) will:
1. Execute conformance profile-level pytest commands
2. Update TEST_SUITE_INDEX.md with final status
3. Validate fix_plan.md coverage
4. Author final roll-up summary

---

**End of input.md for Loop i=154**
