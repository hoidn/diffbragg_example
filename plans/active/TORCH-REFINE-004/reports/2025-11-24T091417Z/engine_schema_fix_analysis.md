# Engine Telemetry Schema Fix Analysis

**Date:** 2025-11-24T091417Z
**Initiative:** TORCH-REFINE-004 (Stage B Per-Reflection Mode Migration)
**Focus:** Phase 7 Blocker - Engine telemetry_version Schema Mismatch

## Problem Statement

Phase 6 implementation (commit 19dd43e) completed ASU mapping infrastructure successfully with all 5 unit tests PASSED. However, the regression guard `test_stage_b_shell_modifiers` FAILED with:

```
TypeError: __init__() got an unexpected keyword argument 'telemetry_version'
  at dbex/refinement/engine.py:144
```

## Root Cause Analysis

### Evidence Chain

1. **Error Location** (dbex/refinement/engine.py:144):
   ```python
   telemetry = RefinementTelemetry(**telemetry_core_dict)
   ```

2. **Import Source** (dbex/refinement/engine.py:18):
   ```python
   from .stage import RefinementStage, RefinementTelemetry
   ```
   - Engine imports `RefinementTelemetry` from `dbex/refinement/stage.py`

3. **Schema Divergence**:
   - **dbex/nanobrag_refinement.py:665**: `telemetry_version: str = "1.0"` ✓ EXISTS
   - **dbex/refinement/stage.py**: `telemetry_version` field ❌ MISSING

4. **Stage B Wrapper Flow** (dbex/refinement/stage_b.py:90-425):
   ```python
   from dbex.nanobrag_refinement import RefinementTelemetry  # Line 94
   telemetry_b = RefinementTelemetry(...)  # Constructs with telemetry_version
   telemetry_output = asdict(telemetry_b)  # Line 414 - dict includes telemetry_version
   return telemetry_output  # Returns dict with telemetry_version key
   ```

5. **Engine Reconstruction Failure**:
   - Stage B returns dict with `telemetry_version: "1.0"` key
   - Engine line 144 tries: `RefinementTelemetry(**telemetry_core_dict)`
   - But `dbex/refinement/stage.py::RefinementTelemetry` dataclass doesn't have that field
   - Python raises TypeError for unexpected kwarg

### Why This Wasn't Caught in Phase E

ARCH-REFINE-FLOW-001 Phase E (engine delegation + telemetry enrichment) completed 2025-11-23T172000Z. The schema mismatch wasn't detected because:

1. **Phase E Scope**: Added `engine_protocol` and `stage_modes` fields to `dbex/refinement/stage.py::RefinementTelemetry` (lines 159-161)
2. **Missing Field**: Did NOT add `telemetry_version` which exists in `dbex/nanobrag_refinement.py::RefinementTelemetry`
3. **Stage A Validation**: Phase E only validated Stage A-only engine delegation mode
4. **Stage B First Use**: test_stage_b_shell_modifiers is the FIRST time Stage B wrapper is called via engine delegation
5. **Schema Parity Gap**: Two RefinementTelemetry definitions exist with divergent fields

## Root Cause Classification

**Verdict:** Schema Evolution Defect (ARCH-REFINE-FLOW-001 Phase B incomplete)

- **NOT** a TORCH-REFINE-004 regression (Phase 6 code didn't touch engine or dataclass schemas)
- **NOT** a Stage B wrapper bug (Stage B correctly uses dbex.nanobrag_refinement.RefinementTelemetry)
- **YES** an ARCH-REFACTOR-001 Phase B incomplete migration:
  - Phase B (2025-11-24T085000Z) converted `dbex/nanobrag_refinement.py::RefinementTelemetry` to dataclass with `telemetry_version: str = "1.0"`
  - But ARCH-REFINE-FLOW-001 Phase A created NEW `dbex/refinement/stage.py::RefinementTelemetry` without full field parity
  - Fields added in Phase A4: `stage_type`, `mode`
  - Fields added in Phase E: `engine_protocol`, `stage_modes`
  - Field MISSING: `telemetry_version`

## Fix Specification

**Objective:** Add `telemetry_version` field to `dbex/refinement/stage.py::RefinementTelemetry` dataclass for schema parity.

### Code Changes

**File:** `dbex/refinement/stage.py`

**Location:** After line 161 (after `stage_modes` field, before `to_dict()` method)

**Addition:**
```python
    # ARCH-REFACTOR-001 Phase B: Schema versioning for future compatibility
    telemetry_version: str = "1.0"
```

**Rationale:**
1. **Field Default**: Use same default value `"1.0"` as dbex/nanobrag_refinement.py:665
2. **Placement**: After ARCH-REFINE-FLOW-001 Phase E fields (engine_protocol, stage_modes) to group by addition timeline
3. **Comment**: Reference ARCH-REFACTOR-001 Phase B as source (schema versioning initiative)
4. **No to_dict() changes needed**: `to_dict()` already uses `asdict()` fallback which will include this field automatically

### Validation Protocol

1. **Compilation Check**:
   ```bash
   python -c "from dbex.refinement.stage import RefinementTelemetry; print(RefinementTelemetry.__dataclass_fields__.keys())"
   ```
   Expected: `telemetry_version` appears in field list

2. **Regression Guard**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
   ```
   Expected: PASS (no TypeError, Stage B telemetry includes telemetry_version)

3. **Schema Parity Verification**:
   ```bash
   # Verify both dataclasses have same core fields
   python -c "
   from dbex.nanobrag_refinement import RefinementTelemetry as Old
   from dbex.refinement.stage import RefinementTelemetry as New
   old_fields = set(Old.__dataclass_fields__.keys())
   new_fields = set(New.__dataclass_fields__.keys())
   missing = old_fields - new_fields
   extra = new_fields - old_fields
   print(f'Missing from new: {missing}')
   print(f'Extra in new: {extra}')
   "
   ```
   Expected after fix: `Missing from new: set()` (no missing core fields)

## Decision Paths

### Path A: Test PASSES
- Condition: test_stage_b_shell_modifiers completes without TypeError
- Actions:
  1. Verify telemetry dict includes `telemetry_version: "1.0"`
  2. Mark Phase 7 blocker RESOLVED
  3. Update fix_plan.md TORCH-REFINE-004 status: blocked → in_progress
  4. Commit with message: "TORCH-REFINE-004: Fix engine telemetry_version schema (unblock Phase 7)"
  5. Return to Galph for Phase 7 planning

### Path B: Test FAILS (different error)
- Condition: No TypeError but different failure (e.g., assertion failure, runtime error)
- Actions:
  1. Document new error signature
  2. Classify as Phase 7 implementation issue vs schema issue
  3. If new schema field missing → iterate schema fix
  4. If Stage B logic issue → escalate to Galph with blocker report

### Path C: Compilation Error
- Condition: Python syntax error or import failure
- Actions:
  1. Fix syntax (likely indentation or missing comma)
  2. Retry compilation check
  3. Do not proceed to test until import succeeds

### Path D: Schema Parity Check Reveals More Missing Fields
- Condition: Verification script shows additional missing fields
- Actions:
  1. Add ALL missing fields from dbex.nanobrag_refinement.RefinementTelemetry
  2. Document which fields were added
  3. Rerun all validation steps
  4. Update decision.md with full schema reconciliation

## Estimated Effort

**Total:** <30 minutes (trivial 1-field addition)

- Code addition: 2 minutes (1 line + 1 comment)
- Compilation check: 1 minute
- Regression test: 15 minutes (test_stage_b_shell_modifiers runtime ~13s)
- Schema parity verification: 2 minutes
- Decision synthesis: 5 minutes
- Commit + artifacts: 5 minutes

**Confidence:** VERY HIGH (~98%)
- Trivial 1-line addition to existing dataclass
- Clear error signature matches predicted fix
- Validation path is deterministic (test either PASSES or has new error)
- No logic changes, only schema field addition

## Findings Applied

- **POLICY-001**: Environment Freeze ✓ (code-only change, no package installs)
- **ARCH-REFACTOR-001 Phase B**: Schema versioning pattern (telemetry_version field)
- **ARCH-REFINE-FLOW-001 Phase A4**: Stage identification fields (stage_type, mode)
- **ARCH-REFINE-FLOW-001 Phase E**: Engine delegation fields (engine_protocol, stage_modes)

## Layered-Scope Guard Check

**Question:** Is this a shared implementation bug requiring dedicated initiative?

**Answer:** NO

**Rationale:**
1. **Scope:** Telemetry schema field addition (1 line, dbex/refinement/stage.py only)
2. **Shared Code Impact:** dbex/refinement/stage.py IS shared (engine.py, stage wrappers), but change is additive (adds field, no semantics change)
3. **Risk:** MINIMAL (adding optional field with default value doesn't break existing code paths)
4. **Complexity:** TRIVIAL (single-loop fix, <30 minutes)
5. **Alternative:** Creating dedicated "ENGINE-SCHEMA-001" initiative would have >10x overhead (plan authoring, loop switching) vs 1-line fix

**Verdict:** Inline bugfix permitted per layered-scope guard "small, local, can be completed in this loop without changing shared semantics."

## Repeat-Failure Escalation Check

**Question:** Has this same failure occurred in two consecutive loops with same signature?

**Answer:** NO

**Rationale:**
1. **First Occurrence:** This is the FIRST loop attempting to run test_stage_b_shell_modifiers after Phase 6 ASU infrastructure implementation
2. **No Prior Failure:** Phase 6 loop (i=260) was implementation-only (no regression test executed due to blocker discovery)
3. **Root Cause Fresh:** Schema mismatch just discovered via Phase 6 regression attempt
4. **Not a Repeat:** No prior loop failed with this exact TypeError signature for TORCH-REFINE-004

**Verdict:** Repeat-failure escalation NOT triggered. Proceed with inline fix.

## Next Actions (After Fix Applied)

1. **Supervisor Housekeeping**:
   - Update fix_plan.md TORCH-REFINE-004 status: blocked → in_progress
   - Add Attempts History entry documenting schema fix (timestamp, blocker resolution, test PASS)
   - Update galph_memory.md focus entry (action_type: review_or_housekeeping, dwell reset to 0)

2. **Phase 7 Readiness Assessment**:
   - Phase 6 ✓ COMPLETE (all exit criteria met after regression PASS)
   - Phase 7 UNBLOCKED (engine schema parity restored)
   - Phase 7 scope ready: Optimization loop integration (apply_asu_modifiers, dynamic optimizer selection, integration smoke)

3. **Focus Continuation Decision**:
   - **Option A:** Continue TORCH-REFINE-004 Phase 7 planning (RECOMMENDED - blocker resolved, ready for implementation)
   - **Option B:** Pivot to different Tier 3 focus (NOT recommended - momentum lost, Phase 7 trivial scope ~2 hours)

**Recommendation:** Continue TORCH-REFINE-004 to Phase 7 planning next loop.
