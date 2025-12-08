# Engine Telemetry Schema Fix Decision

**Date:** 2025-11-24T091417Z
**Initiative:** TORCH-REFINE-004 (Stage B Per-Reflection Mode Migration)
**Focus:** Phase 7 Blocker Resolution - Engine telemetry_version Schema Mismatch

## Path Outcome: A (Test PASSES)

### Validation Results

1. **Compilation Check:** ✅ PASS
   - Command: `python -c "from dbex.refinement.stage import RefinementTelemetry; print('telemetry_version' in RefinementTelemetry.__dataclass_fields__)"`
   - Output: `True`
   - telemetry_version field successfully added to RefinementTelemetry dataclass

2. **Regression Guard:** ✅ PASS
   - Test: `test_stage_b_shell_modifiers`
   - Runtime: 13.68s
   - Result: 1 passed, 5 warnings
   - No TypeError on telemetry_version field
   - Stage B engine delegation operational

3. **Schema Parity Verification:** ✅ PASS
   - Missing from new: `set()` (no missing fields)
   - Extra in new: `set()` (complete parity achieved)
   - Both RefinementTelemetry dataclasses (dbex.nanobrag_refinement and dbex.refinement.stage) have identical field sets

### Code Changes

**File:** `dbex/refinement/stage.py`
**Lines Added:** +2 (line 163-164)

```python
# ARCH-REFACTOR-001 Phase B: Schema versioning for future compatibility
telemetry_version: str = "1.0"
```

**Placement:** After `stage_modes` field (line 161), before `to_dict()` method (line 166)

### Telemetry Verification

Stage B wrapper (`dbex/refinement/stage_b.py`) returns telemetry dict with `telemetry_version: "1.0"` key, and engine (`dbex/refinement/engine.py:144`) successfully constructs RefinementTelemetry(**telemetry_core_dict) without TypeError.

## Decision: Phase 7 Blocker RESOLVED

### Status Changes

- TORCH-REFINE-004 status: `blocked` → `in_progress`
- Phase 6: ✓ COMPLETE (all exit criteria met including regression guard)
- Phase 7: UNBLOCKED (engine telemetry schema parity restored)

### Root Cause Summary

Schema divergence from incomplete ARCH-REFINE-FLOW-001 Phase A migration:
- ARCH-REFACTOR-001 Phase B (2025-11-24T085000Z) added `telemetry_version` to dbex.nanobrag_refinement.RefinementTelemetry
- ARCH-REFINE-FLOW-001 Phase A (2025-11-23) created NEW dbex.refinement.stage.RefinementTelemetry without full field parity
- Gap discovered on first Stage B engine delegation test (test_stage_b_shell_modifiers)

### Next Steps

1. **Commit:** Schema fix + artifacts with message "TORCH-REFINE-004: Fix engine telemetry_version schema (unblock Phase 7)"
2. **Phase 7 Ready:** Optimization loop integration (apply_asu_modifiers, dynamic optimizer selection)
3. **Estimated Effort:** Phase 7 implementation ~1 loop (~2 hours)

## Artifacts

- `pytest_schema_fix.log` — Regression test output (13.68s, 1 passed)
- `schema_parity.log` — Field parity verification (complete parity confirmed)
- `decision.md` — This document (Path A outcome)

---

**Confidence:** VERY HIGH (100%) — All validation steps PASSED, schema parity achieved, regression guard operational.
