# Input — Loop i=155

## Summary
Execute DB-AT-SUITE-CARE-001 Phase C conformance profile certification for Workflow Integration cluster.

## Mode
none

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
harness

## Focus
DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep (Phase C)

## Branch
integration

## Mapped tests
- Workflow Integration Profile: `KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k "DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024"` (13 tests, expect PASS)
- Determinism Profile: `KMP_DUPLICATE_LIB_OK=TRUE CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k DB_AT_002` (determinism harness check — may be blocked if fixture missing)

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/`

## Findings Applied (Mandatory)
- **TESTING-003** (Acceptance test registry maintenance): Phase C3 batch sync requires TEST_SUITE_INDEX.md + TESTING_GUIDE.md updates
- **RUNTIME-001** (Runtime execution guardrails): Conformance profile pytest commands include determinism flags
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Archive logs under `conformance_profiles/` subdirectory

## Pointers
- **SPEC**: `docs/spec-db-conformance.md:55-76` — Workflow Integration Profile criteria
- **ARCH**: `plans/active/DB-AT-SUITE-CARE-001/implementation.md:52-76` — Phase C tasks
- **Fix-plan**: `docs/fix_plan.md:267-295` — DB-AT-SUITE-CARE-001 Attempts History
- **Testing docs**: `docs/TESTING_GUIDE.md` — Canonical selector patterns, environment flags

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-TESTING-001** (Registry consistency): TEST_SUITE_INDEX.md must reflect actual test collection status
   - Owner: `docs/development/TEST_SUITE_INDEX.md`
   - Classify: implementation bug (registry rows may be stale after Phase B completions)

## Do Now (hard validity contract)

**Focus**: DB-AT-SUITE-CARE-001 — Phase C Conformance Profile Certification

**Implement**: Phase C tasks C1-C6 (no production code changes; docs/registry updates + pytest validation)
- `docs/development/TEST_SUITE_INDEX.md::DB_AT_* rows` — Validate 7 rows have complete metadata (status, spec refs, commands, artifact paths)
- `docs/TESTING_GUIDE.md::§2` — Cross-reference selector patterns for consistency

**Tasks**:
1. **C1 — Member plan Phase C completion**: Verify all 5 Workflow Integration member plans show Phase C complete (DB-AT-020/021/022/023/024 done per i=147/150/152/November/prior). DB-AT-002/010 deferred (blocked on Tier-0 dependencies).

2. **C2 — Conformance profile pytest runs**:
   - Execute Workflow Integration Profile command (expect 13/13 PASS — revalidation of i=154 result)
   - Archive log to `reports/2025-12-08T040000Z/conformance_profiles/workflow_integration_pytest.log`
   - Execute Determinism Profile command (DB-AT-002 — document status: PASS/FAIL/BLOCKED with reasoning)
   - Archive log to `reports/2025-12-08T040000Z/conformance_profiles/determinism_pytest.log`
   - Gradient-Safe Profile deferred (DB-AT-010 blocked_pending_environment via ARCH-GRADIENT-FLOW-001)

3. **C3 — TEST_SUITE_INDEX.md batch sync**:
   - Read current TEST_SUITE_INDEX.md
   - Validate 5 Workflow Integration rows (020/021/022/023/024) have: Active status, spec references, canonical commands, artifact paths, runtime estimates
   - Document any gaps or update if needed

4. **C4 — fix_plan.md ledger validation**:
   - Verify ≥5 Attempts History entries exist for Workflow Integration member plans in fix_plan.md:267-295
   - Cross-check timestamps against `plans/active/DB-AT-*/reports/` directories

5. **C5 — Exit criteria validation**:
   - Check 5 exit criteria per implementation.md Phase C validation checklist
   - Document deferrals: DB-AT-002 (determinism harness pending), DB-AT-010 (blocked_pending_environment)

6. **C6 — Author summary.md**:
   - Create `reports/2025-12-08T040000Z/summary.md` with Phase C completion status
   - Include: conformance profile results, registry sync status, exit criteria checklist, deferrals with justification

**Validating pytest selectors**:
- `pytest -v tests -k "DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024"` (expect 13 PASS)
- `pytest -v tests -k DB_AT_002` (document result)

## Touched
Phase C tasks: C1, C2, C3, C4, C5, C6

## Forbidden This Loop
- no new probes
- do not extend plan-local diagnostic scripts
- no changes to production code (dbex/*) — this is a docs/registry/validation loop
- do not modify Tier-0 blocked initiatives (ARCH-GRADIENT-FLOW-001, ARCH-SIM-CONSTRUCTION-001)

## How-To Map

### Environment setup
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export DBEX_SMOKE_DETECTOR_SIZE=full
export NANOBRAGG_DISABLE_COMPILE=1
export CUDA_VISIBLE_DEVICES=''  # For determinism profile only
export TORCHDYNAMO_DISABLE=1    # For determinism profile only
```

### C2 — Conformance profile pytest runs
```bash
# Create artifact directories
mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/conformance_profiles

# Workflow Integration Profile (expect 13 PASS)
KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -v tests -k "DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024" \
  2>&1 | tee plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/conformance_profiles/workflow_integration_pytest.log

# Determinism Profile (document status)
KMP_DUPLICATE_LIB_OK=TRUE CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -v tests -k DB_AT_002 \
  2>&1 | tee plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/conformance_profiles/determinism_pytest.log
```

### C3 — Registry validation
Read `docs/development/TEST_SUITE_INDEX.md` and validate 5 Workflow Integration rows.

### Artifact destinations
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/conformance_profiles/workflow_integration_pytest.log`
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/conformance_profiles/determinism_pytest.log`
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/summary.md`

## Pitfalls To Avoid
1. **Type discipline**: This is a harness loop; do not make production code changes
2. **No stacking on cliff**: Tier-0 blocked initiatives remain untouched
3. **Parity-first**: Workflow Integration Profile already validated (i=154); this is revalidation + certification
4. **Shadow-pipeline guard**: No new diagnostic scripts
5. **Probe saturation**: No instrumentation changes
6. **Evidence→Action**: Document test results accurately; do not fabricate outcomes
7. **Registry consistency**: Only update TEST_SUITE_INDEX.md with verified test status
8. **Determinism profile caveat**: DB-AT-002 may be blocked if golden fixtures incomplete; document actual status

## If Blocked
- If Workflow Integration Profile regresses (any test FAIL): Mark Phase C blocked, investigate regression signature, update Attempts History with failure details
- If Determinism Profile blocked (missing fixtures): Document in C5 exit criteria validation as deferral, proceed with Workflow Integration closure
- If TEST_SUITE_INDEX.md has structural issues: Create minimal fix OR document gap for future loop

## Doc Sync Plan (Conditional)
If any registry updates needed:
1. Run `pytest --collect-only tests -k DB_AT_` to verify selector collection
2. Update TEST_SUITE_INDEX.md rows for affected selectors
3. Cross-reference TESTING_GUIDE.md §2 for consistency

---

**End of input.md for Loop i=155**
