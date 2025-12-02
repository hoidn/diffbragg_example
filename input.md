# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 Validation

## Summary
Validate Phase D.3 Batch 1 test migration completion by running all 5 migrated smoke tests (Engine bugfixes now resolved).

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3: Validate Batch 1 test migration)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
  --smoke-detector-size=small
```
Expected: 4/5 or 5/5 tests PASSED (ASU gradient flow in last test may fail as Stage B issue)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T214805Z/`
- `pytest_phase_d3_validation.log` — Full pytest output for all 5 smoke tests
- `summary.md` — Turn summary (prepend to existing file if present)
- `metrics.txt` — Test results summary with pass/fail breakdown

---

## Do Now

**Context**: Engine bugfixes complete (commit f3ab680d). All 5 test_torch_refine_smoke.py functions were migrated to Engine pattern in commit 7b0a016d, but were blocked by telemetry key mismatch and Engine bugs. Those blockers are now resolved:
- Telemetry key mapping (stage_a → "A", etc.) added to engine.py
- StageAArtifacts always created (even in cold mode)
- engine_protocol and stage_modes fields populated

This is a **validation-only loop** to confirm Phase D.3 Batch 1 is complete. No code changes required.

---

### Step 1: Create Artifacts Directory

```bash
mkdir -p plans/active/ARCH-REFACTOR-001/reports/2025-12-02T214805Z
```

---

### Step 2: Run All 5 Smoke Tests

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T214805Z/pytest_phase_d3_validation.log
```

**Expected outcomes:**
1. **test_stage_a_expansion**: PASSED (Stage A-only, validates basic Engine pattern)
2. **test_stage_a_engine_delegation_telemetry**: PASSED (validates engine_protocol field population)
3. **test_stage_b_shell_modifiers**: PASSED (Stage A+B shell mode)
4. **test_stage_c_detector_microslip**: PASSED (Stage A+C detector offsets)
5. **test_stage_b_per_reflection_smoke**: May PASS or FAIL on ASU gradient flow assertion

**Note on test #5**: If it fails on "ASU modifiers unchanged (mean=1.000000, gradient flow broken)", this is a known Stage B issue (not a migration issue). The Engine artifacts validation already passed in the bugfix loop, so the migration itself is successful.

---

### Step 3: Document Results

Create `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T214805Z/metrics.txt`:

```
# Phase D.3 Batch 1 Validation Results

Tests run: 5/5
Tests passed: X/5
Tests failed: Y/5

## Individual Test Results
- test_stage_a_expansion: [PASSED/FAILED]
- test_stage_a_engine_delegation_telemetry: [PASSED/FAILED]
- test_stage_b_shell_modifiers: [PASSED/FAILED]
- test_stage_c_detector_microslip: [PASSED/FAILED]
- test_stage_b_per_reflection_smoke: [PASSED/FAILED]

## Known Issues
- If test_stage_b_per_reflection_smoke FAILED: ASU gradient flow issue (Stage B concern, not migration issue)

## Conclusion
Phase D.3 Batch 1 migration: [SUCCESSFUL/BLOCKED]
- All facade calls removed from test_torch_refine_smoke.py ✓
- All tests use RefinementEngine pattern ✓
- Telemetry key compatibility validated ✓
- Engine artifacts storage validated ✓
- Next: Phase D.3 Batch 2 (test_stage_a_smoke_parity.py) or Phase D.4
```

---

### Step 4: Commit

**If 4/5 or 5/5 tests PASSED:**

```bash
git add -A
git commit -m "$(cat <<'EOF'
ARCH-REFACTOR-001 Phase D.3 Batch 1 validation complete (tests: X/5 pass)

Validated all 5 test_torch_refine_smoke.py functions after Engine bugfixes:
- test_stage_a_expansion: PASSED (Stage A-only)
- test_stage_a_engine_delegation_telemetry: PASSED (engine_protocol populated)
- test_stage_b_shell_modifiers: PASSED (Stage A+B shell mode)
- test_stage_c_detector_microslip: PASSED (Stage A+C detector offsets)
- test_stage_b_per_reflection_smoke: [PASSED/FAILED - ASU gradient flow]

Migration complete:
- All 6 original functions migrated to Engine pattern (commit 7b0a016d)
- Telemetry key fix applied (commit a6f39bac)
- Engine bugfixes applied (commit f3ab680d)
- X/5 validation tests passing

Phase D.3 Batch 1 complete. Next: Phase D.3 Batch 2 (test_stage_a_smoke_parity.py).

Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T214805Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push
```

**If 3/5 or fewer tests PASSED:**
Mark blocked in commit message and capture detailed failure signatures in artifacts.

---

## Pitfalls To Avoid

1. **This is validation only**: Do NOT modify test code. We're checking that previous migrations work after bugfixes.

2. **ASU gradient flow is expected**: test_stage_b_per_reflection_smoke may fail on "ASU modifiers unchanged" - this is a Stage B issue, NOT a migration issue.

3. **All tests already migrated**: Commit 7b0a016d migrated all 6 functions (one was test_stage_b_asu_mapping_smoke, which became test_stage_b_per_reflection_smoke).

4. **Engine bugfixes**: Commit f3ab680d fixed the 2 Engine bugs, so tests should pass now.

5. **Telemetry key fix**: Commit a6f39bac fixed the telemetry key mismatch, so "A"/"B"/"C" keys work.

6. **Don't escalate ASU issue**: If only test_stage_b_per_reflection_smoke fails on ASU, Phase D.3 Batch 1 is still COMPLETE (4/5 is success).

7. **Environment Freeze**: Do not install/upgrade packages. If an import fails, mark blocked.

8. **Initiative type: architecture**: This is structural refactoring (facade → Engine), not behavior change.

9. **Batch scope**: This is Batch 1 only (test_torch_refine_smoke.py). Batch 2 (test_stage_a_smoke_parity.py) and tooling (stage_a_adam.py) come next.

10. **Success criteria**: 4/5 or 5/5 tests PASSED = Phase D.3 Batch 1 complete. 3/5 or fewer = blocked, needs investigation.

---

## If Blocked

**Scenario 1: Multiple tests fail with telemetry key errors**
- Check that commit a6f39bac is present (telemetry key mapping)
- Verify engine.py:192-206 has the legacy_telemetry_dict mapping
- Check that Engine.run() returns the mapped dict, not self._telemetry
- Capture error signatures, mark blocked

**Scenario 2: Tests fail with engine_protocol=None or missing artifacts**
- Check that commit f3ab680d is present (Engine bugfixes)
- Verify engine.py has _compute_engine_protocol() and _compute_stage_modes() methods
- Verify stage_a.py:2046+ always creates StageAArtifacts
- Capture error signatures, mark blocked

**Scenario 3: Tests fail with import errors (missing RefinementEngine, etc.)**
- Check that test_torch_refine_smoke.py has module-scope imports from dbex.refinement
- Verify commit 7b0a016d is present (test migration)
- Check for syntax errors or missing imports
- Capture import errors, mark blocked

**Scenario 4: Tests fail with unexpected errors (not telemetry/artifacts/imports)**
- Capture full traceback in pytest log
- Document failure signature in metrics.txt
- Check if failure is Engine-related or test-specific
- Mark blocked with detailed error description

**Fallback:** If 3/5 or fewer tests pass, capture all evidence in artifacts directory, update Attempts History in `docs/fix_plan.md` with detailed failure signatures, and mark ARCH-REFACTOR-001 Phase D.3 blocked pending investigation.

---

## Findings Applied

**Relevant findings from `docs/findings.md`:**

- **ARCH-REFACTOR-001 Phase D.3**: Test migration follows CLI blueprint (D.2) with Engine pattern
- **Engine telemetry key mapping**: Legacy "A"/"B"/"C" keys required for backward compatibility
- **StageAArtifacts always created**: Even in cold mode (enable_stage_a_warm_cache=False)
- **engine_protocol and stage_modes**: Phase E telemetry fields populated after stage loop
- **Environment Freeze**: Runtime is pre-provisioned; do not install/upgrade packages during loops
- **Initiative type: architecture**: Structural refactoring (facade removal), not behavior change

---

## Pointers

**Reference documents:**
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` Phase D.3 checklist
- CLI blueprint: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/cli_refactor_blueprint.md`
- Test migration: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z/planning_notes.md`
- Engine bugfixes: `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T220000Z/test_results_summary.md`

**Code pointers:**
- Test file: `tests/dbex/test_torch_refine_smoke.py` (5 functions migrated)
- Engine telemetry: `dbex/refinement/engine.py::RefinementEngine.run()` lines 192-206
- Engine helpers: `dbex/refinement/engine.py::_compute_engine_protocol()`, `_compute_stage_modes()`
- Stage A artifacts: `dbex/refinement/stage_a.py::StageA.run()` line ~2050

**Previous commits:**
- Test migration: commit 7b0a016d (all 6 functions migrated)
- Telemetry key fix: commit a6f39bac (3/5 tests passed)
- Engine bugfixes: commit f3ab680d (artifacts + Phase E fields)

---

## Next Up

**After this loop (if 4/5 or 5/5 tests PASSED):**
1. Mark Phase D.3 Batch 1 complete in implementation.md
2. Proceed to Phase D.3 Batch 2: Migrate `tests/dbex/test_stage_a_smoke_parity.py` (1 function)
3. Or skip to Phase D.4: Fix legacy imports in `test_physics_loss_current.py`
4. Then Phase D.5: Facade deletion (comprehensive 12-step checklist)

**If test_stage_b_per_reflection_smoke fails on ASU:**
- Document as known Stage B issue
- Open separate initiative for ASU gradient flow investigation (not blocking ARCH-REFACTOR-001)
- Continue with Phase D.3 Batch 2 or D.4

**Sign-off:** This is a validation-only loop. No code changes. Just confirming the migration works after bugfixes.

---

## Doc Sync Plan

**Not applicable this loop** (no new tests added/renamed; validation run only).

---

## Mapped Tests Guardrail

All 5 mapped selectors exist and should collect:
- `test_stage_a_expansion` ✓
- `test_stage_a_engine_delegation_telemetry` ✓
- `test_stage_b_shell_modifiers` ✓
- `test_stage_c_detector_microslip` ✓
- `test_stage_b_per_reflection_smoke` ✓

If any selector collects 0, this is an error (test was renamed or deleted by accident).
