# PERF-WARM-SIM-001 Phase D Validation Unblocking — Engine Delegation Telemetry Key Mapping Fix

## Summary
Fix engine delegation telemetry key mapping to restore Stage C smoke test validation for Phase D detector reuse implementation.

## Mode
none

## Focus
PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation (Phase D Validation Unblocking)

## Branch
integration

## Mapped Tests
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (BLOCKED → must PASS)
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, must remain PASSING)

## Artifacts
`plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/`

## Do Now

### Root Cause Analysis Complete

Ralph's Phase D implementation (commit 1bdeca3) is **code-complete** and compiles cleanly. The blocker is an ARCH-REFINE-FLOW-001 Phase E regression: when `use_engine_delegation=True`, `run_nanobrag_refinement` returns telemetry keyed by lowercase stage names (`"stage_a"`, `"stage_b"`, `"stage_c"`) but all smoke tests expect uppercase single-letter keys (`"A"`, `"B"`, `"C"`) per the legacy convention.

**Evidence:**
- `dbex/nanobrag_refinement.py:4491-4494` constructs `telemetry_out[stage_name]` where `stage_name = s.name` (returns `"stage_a"` per `dbex/refinement/stage_a.py:45,51`)
- `tests/dbex/test_torch_refine_smoke.py:979-982` expects `telemetry_dict["A"]` and `telemetry_dict["C"]`
- **All 5 tests** using `use_engine_delegation=True` are blocked by this mismatch (lines 380, 854, 975, 1284)

### Scope

This is a **trivial 5-line fix** to restore backward compatibility. Phase D detector reuse code is NOT involved.

### Implementation Steps

**Step 1: Add telemetry key mapping**
File: `dbex/nanobrag_refinement.py:4486-4496`

After line 4486 (`telemetry_out = {}`), before the loop at line 4487, add a mapping dict:
```python
# Map stage names to legacy single-letter keys for backward compatibility
stage_name_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}
```

Then at line 4494, change:
```python
telemetry_out[stage_name] = RefinementTelemetry(**telem_dict)
```

To:
```python
legacy_key = stage_name_map.get(stage_name, stage_name)  # Fallback to stage_name if unknown
telemetry_out[legacy_key] = RefinementTelemetry(**telem_dict)
```

**Step 2: Validation**
1. Run `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (must PASS, confirms Phase D validation unblocked)
2. Run `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, must remain PASSING)
3. Archive both logs to artifacts directory

**Step 3: Documentation**
Update `plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/summary.md` with Turn Summary documenting:
- Root cause (engine delegation telemetry key mismatch introduced in ARCH-REFINE-FLOW-001 Phase E commit 9bbd1e8)
- Fix applied (5-line telemetry key mapping)
- Validation outcome (Stage C smoke PASS confirms Phase D detector reuse operational)
- Next action (Ralph completes Phase D validation D4 with full telemetry suite)

**Step 4: Commit**
```bash
git add dbex/nanobrag_refinement.py plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/
git commit -m "PERF-WARM-SIM-001: Fix engine delegation telemetry keys (stage_a→A) for test compatibility

Phase D validation was blocked by ARCH-REFINE-FLOW-001 Phase E regression where
engine delegation returns telemetry keyed by 'stage_a'/'stage_b'/'stage_c' but
tests expect legacy 'A'/'B'/'C' keys. Added 5-line mapping for backward compat.

Unblocks: test_stage_c_detector_microslip (Phase D validation)
Fixes: test_stage_a_expansion, test_stage_a_engine_delegation_telemetry,
       test_stage_b_shell_small, test_stage_b_shell_full (all blocked by same issue)

tests: not run (fix applied, validation in next loop)"
git push
```

## How-To Map

### Compilation Check
```bash
python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('✓ Imports clean')"
```

### Test Execution
```bash
# Primary validation (Phase D blocker)
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --tb=short -o log_cli=true -o log_cli_level=INFO \
  > plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/pytest_stage_c_microslip_unblocked.log 2>&1

# Regression guard
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  --tb=short \
  > plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/pytest_stage_a_regression_guard.log 2>&1
```

### Decision Synthesis (4-Path Template)

**Path A (both tests PASS):**
Phase D validation UNBLOCKED. Proceed to Phase D4 full validation suite (Stage C smokes small+full, telemetry capture, summarize_stage_c_roi.py outputs, implementation.md Phase D mark COMPLETE).

**Path B (Stage C smoke still FAILs with different error):**
Engine delegation has additional bugs beyond telemetry keys. Debug new failure signature, compare against Phase D decision.md blocker analysis (KeyError at stage_a.py:107), document findings.

**Path C (regression guard FAILs):**
Telemetry key mapping introduced side effects. Rollback mapping, investigate why legacy paths broke, verify mapping logic only affects engine delegation paths.

**Path D (compilation FAILs):**
Syntax error in mapping code. Fix import/indentation, rerun compilation check.

## Pitfalls To Avoid

1. **Scope creep:** This is a 5-line fix for telemetry key backward compatibility. Do NOT refactor engine delegation inputs structure, stage wrapper logic, or telemetry schema. Phase D detector reuse code is CORRECT and must not be touched.

2. **Environment Freeze:** No package installs, no runtime changes. Code-only fix.

3. **Test registry sync:** NOT required (no new tests authored, existing selectors unchanged).

4. **Telemetry schema:** The mapping is cosmetic (dict key renaming for backward compatibility). Do NOT modify RefinementTelemetry dataclass fields or to_dict() method.

5. **Engine delegation paths:** Verify the mapping only affects the engine delegation return statement (line 4496). Legacy Stage A/B/C paths (lines 3935, 4060, 4986) already return uppercase keys and must not be touched.

6. **Stage name constants:** Do NOT modify `stage_a.py:45`, `stage_b.py:36`, `stage_c.py:36` `_name` assignments. The mapping allows stages to keep lowercase internal names while presenting uppercase keys externally.

## If Blocked

If tests still fail after fix:
1. Capture exact error signature (message, traceback, file:line)
2. Compare against Phase D decision.md blocker (KeyError at stage_a.py:107)
3. Document new failure mode in `phase_d_blocker_followup.md`
4. Return control to Galph with blocker report

## Findings Applied

- **ARCH-ENGINE-002:** Stage wrapper pattern with lazy imports — NOT relevant to this fix (engine delegation logic is correct, only telemetry key naming wrong)
- **POLICY-001:** Environment Freeze, code-only changes — COMPLIANT
- **TESTING-003:** Test registry sync conditional — NOT triggered (no new tests)

## Pointers

- **Root Cause:** `dbex/nanobrag_refinement.py:4428,4491-4494` (engine delegation telemetry key construction)
- **Stage Name Definitions:** `dbex/refinement/stage_a.py:45`, `dbex/refinement/stage_b.py:36`, `dbex/refinement/stage_c.py:36`
- **Test Expectations:** `tests/dbex/test_torch_refine_smoke.py:979-982,380,854,1284`
- **Phase D Implementation:** `dbex/nanobrag_refinement.py:381,647,693-770,3121-3165,3471-3515` (detector reuse, CORRECT, not modified in this fix)
- **Spec References:** `docs/spec-db-workflow.md §Stage C`, `docs/spec-db-runtime.md §2.1` (cache reuse contract)

## Next Up

After both tests PASS:
1. Phase D4 full validation suite (Stage C smokes small+full detectors with telemetry capture)
2. Update `implementation.md` Phase D checklist marking D1-D4 COMPLETE
3. Write Phase D closure summary documenting detector reuse implementation + telemetry key fix
4. Commit Phase D COMPLETE, return control to Galph for next Tier 2/3 focus selection
