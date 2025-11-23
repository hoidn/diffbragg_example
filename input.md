# Input — Phase C2.5 Validation & Documentation Sync

## Summary
Complete Phase C2.5 validation by updating test registry and verifying no DB-AT-024 regression from CPU fallback deferral.

## Mode
Docs

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.5 validation complete, prepare Phase C2 engine wiring)

## Branch
`integration`

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers[small]` (Active, validates core Stage B logic CUDA-only)
- `tests/dbex/test_mapping_consistency.py::test_mapping_consistency_nanobrag[DB_AT_024-refGeom-dbex]` (Active, parity check — CUDA path unchanged by CPU deferral)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/`

## Do Now

Ralph, complete Phase C2.5 validation and prepare for Phase C2 (Stage B engine wiring):

### 1. Test Registry Update (docs/TESTING_GUIDE.md §2 + docs/development/TEST_SUITE_INDEX.md)

**Context**: Phase C2.5 deferred CPU fallback support; full detector test now skipped. Test registry must reflect this limitation.

**Tasks**:
1. Run collection check to confirm current state:
   ```bash
   pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --collect-only > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/pytest_collect_stage_b.log 2>&1
   ```
   Verify: should collect exactly 1 test (small detector variant only)

2. Update `docs/TESTING_GUIDE.md` §2 Stage B entry:
   - Note: CPU fallback deferred (GRADIENT-003)
   - Coverage: small detector (CUDA-only)
   - Rationale: HKL grid CUDA→CPU transfer corruption (see findings)

3. Update `docs/development/TEST_SUITE_INDEX.md` Stage B row:
   - Status: Active (small detector)
   - Notes: Full detector skipped (GRADIENT-003 — CPU fallback deferred)

4. Archive collection log in artifacts directory

### 2. DB-AT-024 Regression Check

**Context**: CPU fallback deferral affects only full detector path. CUDA path (used by DB-AT-024) is unchanged. Verify no regression.

**Tasks**:
1. Run DB-AT-024 mapping consistency (collect-only first):
   ```bash
   pytest tests/dbex/test_mapping_consistency.py::test_mapping_consistency_nanobrag -k DB_AT_024 --collect-only > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/pytest_collect_db_at_024.log 2>&1
   ```

2. If collection succeeds (>0 tests), run full test:
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_mapping_consistency.py::test_mapping_consistency_nanobrag -k DB_AT_024 -v > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/pytest_db_at_024.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/pytest_db_at_024.log
   ```

3. Extract test result:
   - PASS: No regression, CUDA path validated ✓
   - FAIL: Investigate failure signature, document in decision.md
   - SKIP/ERROR: Document blocker in decision.md

4. Write JSON summary:
   ```json
   {
     "test_id": "DB_AT_024",
     "status": "PASS|FAIL|SKIP",
     "exit_code": <int>,
     "regression_detected": false,
     "notes": "CPU fallback deferral affects only full detector (skipped); CUDA path (DB-AT-024 uses small/canonical) unchanged"
   }
   ```
   Save to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/db_at_024_validation.json`

### 3. Phase C2.5 Completion Synthesis

**Tasks**:
1. Review Phase C2.5 checklist in `plans/active/ARCH-REFINE-FLOW-001/implementation.md`:
   - C2.5a: ✓ COMPLETE (skip marker added)
   - C2.5b: ✓ COMPLETE (collection verified 1 test)
   - C2.5c: ✓ COMPLETE (Phase C2 status updated with deferral)

2. Write `decision.md`:
   - **Verdict**: Phase C2.5 COMPLETE
   - **Test Registry**: Updated with CPU fallback limitation
   - **DB-AT-024**: PASS/FAIL/SKIP (from step 2)
   - **Next**: Phase C2 (Wire Stage B into engine) planning

3. Update `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase C2.5 section:
   - Mark C2.5 status: COMPLETE
   - Add validation artifacts reference

### 4. Documentation Hygiene

**Tasks**:
1. Verify `docs/findings.md` GRADIENT-003 entry matches Ralph's loop i=223 update:
   - Status: Deferred
   - Root cause documented
   - Future enhancement path described

2. Scan `docs/fix_plan.md` ARCH-REFINE-FLOW-001 Attempts History — ensure loop i=223 is recorded with:
   - Timestamp: 2025-11-23T140000Z
   - Action: Defer CPU fallback (Path C)
   - Outcome: Small detector PASSED (23.7% improvement), Phase C2.5 COMPLETE
   - Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T140000Z/

3. If missing, append concise Attempts History entry (1-2 sentences max)

### 5. Commit and Push

```bash
git add docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md docs/fix_plan.md plans/active/ARCH-REFINE-FLOW-001/
git commit -m "ARCH-REFINE-FLOW-001 Phase C2.5 validation: test registry + DB-AT-024 check — tests: not run"
git push
```

## How-To Map

### Collection Check Commands
```bash
# Stage B smoke (should collect 1 test)
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --collect-only

# DB-AT-024 (should collect 3+ tests)
pytest tests/dbex/test_mapping_consistency.py::test_mapping_consistency_nanobrag -k DB_AT_024 --collect-only
```

### Test Execution
```bash
# DB-AT-024 full run
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_mapping_consistency.py::test_mapping_consistency_nanobrag -k DB_AT_024 -v
```

### Artifact Paths
- Collection logs: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/pytest_collect_*.log`
- Test logs: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/pytest_*.log`
- Validation JSON: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/db_at_024_validation.json`
- Decision: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T132017Z/decision.md`

## Pitfalls To Avoid

1. **Test Registry Clarity**: Be specific about CPU fallback limitation vs Stage B functionality (core logic validated, CPU path deferred)
2. **DB-AT-024 Scope**: This test uses CUDA path (refGeom canonical detector), NOT affected by full detector CPU fallback skip
3. **Collection Before Execution**: Always run `--collect-only` first to verify selector status before expensive test runs
4. **Findings Hygiene**: Do NOT create GRADIENT-004 for gradient tracking error (it's a downstream symptom per GRADIENT-003)
5. **Dwell Accounting**: This is a docs/validation loop (no production code changes); next Galph loop MUST plan Phase C2 engine wiring with production code task
6. **Environment**: KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1 for all pytest runs
7. **Test Skip Reason**: Already correct in test_torch_refine_smoke.py:1133 — do NOT modify skip marker
8. **Commit Message**: Use "tests: not run" (docs-only loop, no test execution in THIS loop for Phase C2.5 artifacts)

## If Blocked

**Scenario A: DB-AT-024 collection fails (0 tests)**
- Check test file exists and selector syntax
- Document in decision.md: "DB-AT-024 collection blocked: <reason>"
- Mark Phase C2.5 validation: PARTIAL (registry updated, parity check blocked)
- Escalate to Galph with blocker details

**Scenario B: DB-AT-024 test fails**
- Extract failure signature from pytest log
- Check if failure is NEW (CPU fallback related) or PRE-EXISTING
- If NEW: document regression details, mark Phase C2.5: BLOCKED
- If PRE-EXISTING: note in decision.md, proceed (CPU deferral did not cause new failure)
- Escalate to Galph next loop with analysis

**Scenario C: Test registry files missing**
- Check `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` exist
- If missing: create skeleton structure per templates
- Document in decision.md: "Registry bootstrapped"

## Findings Applied

- **GRADIENT-003** (CPU Fallback Path Zero Bragg Output): Status Deferred, root cause HKL transfer corruption, small detector validates core Stage B (adhering to deferral decision)
- **POLICY-001** (Environment Freeze): Docs-only loop, no environment changes
- **TESTING-003** (Selector Status Transitions): Update registry after collection confirms test count
- **CONFORMANCE-001** (DB-AT Parity Profile): DB-AT-024 uses canonical environment flags
- **PERF-WARM-011/012** (Stage B CPU Fallback): Issue resolved by deferral — CPU path no longer attempted on full detector

## Pointers

- **Test Registry**: `docs/TESTING_GUIDE.md` §2 (Stage smoke selectors), `docs/development/TEST_SUITE_INDEX.md` (status table)
- **Findings**: `docs/findings.md` GRADIENT-003 (line 69)
- **Fix Plan**: `docs/fix_plan.md` ARCH-REFINE-FLOW-001 (Attempts History)
- **Implementation Plan**: `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase C2.5 (lines 322-363)
- **Spec**: `docs/spec-db-runtime.md` §34-39 (CPU/CUDA parity aspiration)
- **Ralph's Evidence**: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T140000Z/decision.md` (Phase C2.5 completion)

## Next Up

After Phase C2.5 validation complete, Galph next loop will plan Phase C2 (Wire Stage B into engine):
- Task: Remove Stage B inline code from `run_nanobrag_refinement`, delegate to `StageB` class via `RefinementEngine([StageA(), StageB()])`
- Scope: ~200 lines removal, engine wiring at line ~3100
- Validation: Stage B smoke (small detector) + telemetry schema check
- Risk: MEDIUM (invasive refactor, must preserve telemetry contract)

**FSM Note**: This is a docs/validation loop (dwell=2, planning→ready_for_implementation transition with docs task). Next Galph loop MUST provide production code Do Now per implementation floor rule (max 1 docs-only loop per focus).
