# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 (Batch 1 Telemetry Fix)

## Summary
Fix RefinementEngine telemetry key mapping to use legacy "A"/"B"/"C" labels instead of "stage_a"/"stage_b"/"stage_c" for backward compatibility with test suite.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3: Test Harness Migration, Batch 1 telemetry bugfix)

## Branch
integration

## Mapped tests
```
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
Expected: All 5/5 tests PASSED (6th test test_stage_c_stage_a_baseline_detector_dist is not mapped in current selector list)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z_debug/`
- `pytest_smoke_tests_fixed.log` — Full pytest output for all 5 smoke tests after telemetry key fix
- `summary.md` — Turn summary (prepend to existing file if present)

---

## Do Now

**Root cause identified:** RefinementEngine.run() returns telemetry dict keyed by stage.name ("stage_a", "stage_b", "stage_c") but all tests and downstream consumers expect legacy keys ("A", "B", "C"). This broke all 6 migrated test functions in Phase D.3 Batch 1.

**Evidence:**
- pytest log shows assertions like `assert 'A' in telemetry_dict` failing with actual keys `{'stage_a': ...}`
- Engine code (dbex/refinement/engine.py:190) does `self._telemetry[stage.name] = telemetry`
- Facade (dbex/nanobrag_refinement.py:246, 428) explicitly converted to "A"/"B"/"C" for backward compatibility
- CLI refactor (dbex/refine_one.py:593, 611, 616) also expects "A"/"B"/"C" but tests were mocked so the issue was hidden

**Fix strategy:** Add telemetry key mapping layer in RefinementEngine.run() to convert "stage_a"/"stage_b"/"stage_c" → "A"/"B"/"C" before returning. This maintains backward compatibility with all existing test code without requiring 100+ test assertion updates.

### Step 1: Fix RefinementEngine telemetry key mapping

**File:** `dbex/refinement/engine.py`

**Action:** Modify the return statement of `run()` method to map stage names to legacy labels.

**Current code (line ~190-192):**
```python
            # Aggregate into telemetry dict keyed by stage name
            self._telemetry[stage.name] = telemetry

        return self._telemetry
```

**Replace with:**
```python
            # Aggregate into telemetry dict keyed by stage name
            self._telemetry[stage.name] = telemetry

        # ARCH-REFACTOR-001 Phase D.3: Map stage names to legacy labels for backward compatibility
        # Tests and downstream code expect "A"/"B"/"C" keys (not "stage_a"/"stage_b"/"stage_c")
        legacy_telemetry_dict = {}
        for stage_name, telem in self._telemetry.items():
            if stage_name == "stage_a":
                legacy_telemetry_dict["A"] = telem
            elif stage_name == "stage_b":
                legacy_telemetry_dict["B"] = telem
            elif stage_name == "stage_c":
                legacy_telemetry_dict["C"] = telem
            else:
                # Unknown stage name - pass through unchanged
                legacy_telemetry_dict[stage_name] = telem

        return legacy_telemetry_dict
```

**Rationale:** This preserves test backward compatibility while keeping Engine internals clean. The facade did the same mapping at lines 246/428 for the same reason.

### Step 2: Validation

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
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z_debug/pytest_smoke_tests_fixed.log
```

**Gate:** All 5/5 tests PASSED

**If tests still fail:**
1. Check that telemetry dict keys are now "A", "B", "C" (add debug print statement if needed)
2. Verify no other code is checking for "stage_a"/"stage_b"/"stage_c" keys that should use legacy keys
3. Capture failure signature in artifacts and mark blocked

### Step 3: Commit

**Message template:**
```
ARCH-REFACTOR-001 Phase D.3 Batch 1 bugfix: Map Engine telemetry keys to legacy labels (tests: 5/5 pass)

Fixed RefinementEngine.run() to return telemetry dict with legacy "A"/"B"/"C" keys instead of
"stage_a"/"stage_b"/"stage_c" for backward compatibility with test suite and CLI code.

Root cause:
- Engine internally uses stage.name ("stage_a", "stage_b", "stage_c") for telemetry aggregation
- All test assertions expect legacy keys ("A", "B", "C") from facade era
- Phase D.2 CLI refactor also expects "A"/"B"/"C" (lines 593, 611, 616) but wasn't caught
  because CLI tests were mocked

Implementation:
- Added telemetry key mapping layer in engine.py::run() before return
- Maps "stage_a" → "A", "stage_b" → "B", "stage_c" → "C" per facade precedent (lines 246/428)
- Preserves engine internals (self._telemetry still keyed by stage.name for artifacts access)
- Unknown stage names pass through unchanged for extensibility

Tests: 5/5 smoke selectors PASSED
- test_stage_a_expansion
- test_stage_a_engine_delegation_telemetry
- test_stage_b_shell_modifiers
- test_stage_c_detector_microslip
- test_stage_b_per_reflection_smoke

Metrics: 1 file touched (engine.py), +13 lines (telemetry key mapping), no behavioral regression
Phase D.3 Batch 1 telemetry compatibility fix complete; test migration can proceed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **Artifact key access:** Do NOT change engine._artifacts key structure — it should still use "stage_a"/"stage_b"/"stage_c" internally. Only the returned telemetry dict uses legacy labels.

2. **Internal telemetry tracking:** Keep self._telemetry keyed by stage.name for internal consistency. Only map to legacy labels in the return value.

3. **Unknown stages:** The mapping should pass through any unknown stage names unchanged (for future extensibility).

4. **Test collection:** After fix, run `pytest --collect-only tests/dbex/test_torch_refine_smoke.py` to verify all 5 tests are discovered.

5. **Telemetry structure preservation:** Do NOT change the RefinementTelemetry structure itself — only the dict keys that wrap it.

6. **Environment Freeze:** Do not install/upgrade packages. If an import fails, mark blocked.

7. **Initiative type boundaries:** This is an architecture initiative; do not change test semantics or gates.

8. **Rollback readiness:** If tests still fail after this fix, capture evidence and mark blocked in fix_plan.

9. **CLI impact:** This fix also resolves the latent bug in CLI refactor (Phase D.2) where code expects "A"/"B"/"C" keys.

10. **Facade comparison:** The facade (nanobrag_refinement.py) did this same mapping at lines 246 and 428. Follow that precedent exactly.

---

## If Blocked

**Scenario 1: Tests still fail with key errors**
- Add debug print of telemetry_dict.keys() before returning from engine.run()
- Verify mapping is producing correct "A"/"B"/"C" keys
- Check if any test assertions are checking for internal "stage_a"/"stage_b"/"stage_c" keys that shouldn't be
- Capture debug output in artifacts, mark blocked

**Scenario 2: New failures appear**
- Verify the mapping didn't break artifact access patterns
- Check that self._telemetry internal storage still uses stage.name
- Ensure legacy_telemetry_dict is a new dict (not modifying self._telemetry in place)
- Capture failure signature, mark blocked

**Scenario 3: Import or syntax errors**
- Verify the code changes are inside the run() method
- Check indentation and dict comprehension syntax
- Capture traceback in artifacts, mark blocked

**Fallback:** Capture all evidence in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z_debug/`, update Attempts History in `docs/fix_plan.md`, and switch focus per loop_discipline.

---

## Findings Applied

**Relevant findings from `docs/findings.md`:**

- **ARCH-REFACTOR-001 Phase D.2 reference:** CLI refactor expects "A"/"B"/"C" telemetry keys (dbex/refine_one.py:593, 611, 616).
- **Facade precedent:** dbex/nanobrag_refinement.py lines 246 and 428 map engine telemetry to legacy keys for backward compatibility.
- **Initiative type: architecture:** This work does NOT change external behavior, specs, or acceptance gates; purely fixes telemetry key structure for backward compatibility.
- **Environment Freeze:** Runtime is pre-provisioned; do not install/upgrade packages during loops.

---

## Pointers

**Reference documents:**
- Phase D.2 CLI refactor: `dbex/refine_one.py` lines 593, 611, 616 (expects "A"/"B"/"C" keys)
- Facade precedent: `dbex/nanobrag_refinement.py` lines 246, 428 (maps to "A"/"B"/"C")
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` (lines 365-395)
- Fix plan ledger: `docs/fix_plan.md` (lines 52-88, ARCH-REFACTOR-001 Attempts History)

**Code pointers:**
- Target file: `dbex/refinement/engine.py::run()` (line ~190-192)
- Test file: `tests/dbex/test_torch_refine_smoke.py` (all 5 migrated functions)
- Failing assertions: lines checking `assert "A" in telemetry_dict`, `assert "B" in telemetry_dict`, etc.

---

## Next Up

**After this loop (telemetry bugfix complete):**
1. Re-run Phase D.3 Batch 1 full migration validation with all 6 tests
2. Phase D.3 Batch 2: Migrate remaining test files
3. Phase D.4: Legacy helper import fixes
4. Phase D.5: Facade deletion

**Sign-off:** This is a critical bugfix for Phase D.3 Batch 1. All subsequent batches depend on this fix.

---

## Doc Sync Plan

**Not applicable this loop** (no new tests added/renamed; fixing telemetry structure compatibility).

---

## Mapped Tests Guardrail

All 5 mapped selectors already exist and should pass after telemetry key fix:
- `test_stage_a_expansion`
- `test_stage_a_engine_delegation_telemetry`
- `test_stage_b_shell_modifiers`
- `test_stage_c_detector_microslip`
- `test_stage_b_per_reflection_smoke`

Note: 6th test `test_stage_c_stage_a_baseline_detector_dist` was in original Do Now but not in current pytest command; will validate in next loop once these 5 pass.
