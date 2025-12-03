# Root Cause Analysis — DIAG-NANOBRAGG-OVERSAMPLE-001 Phase A

**Date**: 2025-12-03T043000Z
**Initiative**: DIAG-NANOBRAGG-OVERSAMPLE-001
**Analyst**: Ralph (implementation engineer)

## Executive Summary

Debug instrumentation successfully identified the root cause of ARCH-SIM-CONSTRUCTION-001's reconstruction magnitude discrepancy (~23,317× scale error). The issue is **Case A**: `DetectorConfig.oversample` field is NOT being preserved across simulator runs. The field is correctly initialized to `3` but gets overwritten to `-1` after the first simulator invocation.

## Debug Output Excerpt

```
[DIAG-OVERSAMPLE] simulator.run() called with oversample=None
[DIAG-OVERSAMPLE] self.detector.config.oversample=3
[DIAG-OVERSAMPLE] oversample after config read: 3

[DIAG-OVERSAMPLE] simulator.run() called with oversample=None
[DIAG-OVERSAMPLE] self.detector.config.oversample=-1   ← CHANGED TO -1!
[DIAG-OVERSAMPLE] oversample after config read: -1
[DIAG-OVERSAMPLE] Entering auto-selection branch (oversample == -1)

[DIAG-OVERSAMPLE] simulator.run() called with oversample=None
[DIAG-OVERSAMPLE] self.detector.config.oversample=-1   ← STILL -1
[DIAG-OVERSAMPLE] oversample after config read: -1
[DIAG-OVERSAMPLE] Entering auto-selection branch (oversample == -1)

[... pattern repeats for all 209 subsequent simulator runs ...]
```

**Full debug output**: 1,166 lines total (see `pytest_db_at_028_debug.log`)
**Pattern**: First run correct (`oversample=3`), all 208 subsequent runs incorrect (`oversample=-1`)

## Case Identification

**Conclusion: Case A** — DetectorConfig.oversample field not preserved

**Evidence**:
1. ✅ First invocation shows `self.detector.config.oversample=3` (correct initialization)
2. ❌ Second invocation shows `self.detector.config.oversample=-1` (field was mutated)
3. ❌ All subsequent invocations show `self.detector.config.oversample=-1`
4. ✅ Caller never passes explicit override (`simulator.run() called with oversample=None`)
5. ❌ Auto-selection branch entered 208 times (despite explicit `oversample=3` config intent)

**Ruled out**:
- **Case B** (caller override): Debug logs show `oversample=None` on all calls, not `-1`
- **Case C** (auto-selection logic bug): The `if oversample == -1:` branch logic is correct; the problem is upstream mutation

## Root Cause Hypothesis

The `DetectorConfig` dataclass is likely being mutated after construction. Possible mechanisms:

1. **Config mutation during simulation**: The `Simulator.run()` method or downstream code might be modifying `self.detector.config.oversample` as a side effect
2. **Shared mutable config**: Multiple simulator instances sharing the same `DetectorConfig` object, with one mutating it
3. **Default value override**: The DetectorConfig initialization logic might be resetting fields to defaults after construction
4. **Dataclass field descriptor issue**: If `oversample` is a property/descriptor with setter logic, it might auto-reset to `-1`

**Most likely**: The detector config object is being mutated in-place during the first `Simulator.run()` call, overwriting `oversample=3` with `oversample=-1`.

## Impact Assessment

**Severity**: CRITICAL — Blocks ARCH-SIM-CONSTRUCTION-001 (Tier 0 architectural spine)

**Scope**:
- Affects ALL reconstruction forward simulations (209 per test)
- Causes ~23,317× magnitude discrepancy in reconstruction helpers
- Violates spec requirement for explicit oversample control (docs/spec-db-core.md §§20-40)

**Test Status**: DB-AT-028 acceptance criterion `chi²/pixel initial ≤ 1e2` fails (actual: 1.084e+05)

## Recommended Next Step

**Phase B Action**: Fix `DetectorConfig.oversample` preservation issue

**Implementation approach** (choose one based on further investigation):

1. **Option 1 — Deep copy config**: Clone `DetectorConfig` in `Simulator.__init__()` to prevent shared mutation
2. **Option 2 — Immutable config**: Convert `DetectorConfig` to frozen dataclass (`@dataclass(frozen=True)`)
3. **Option 3 — Fix mutation site**: Find and remove the code that overwrites `config.oversample` to `-1`

**Investigation steps for Phase B**:
1. Add debug instrumentation at END of `Simulator.run()` to confirm mutation happens during (not after) simulation
2. Search nanobrag_torch codebase for assignments to `.oversample` or `config.oversample`
3. Check if `DetectorConfig` has `__post_init__` or property setters that might auto-reset fields
4. Verify whether multiple `Simulator` instances share the same `DetectorConfig` object reference

**Estimated complexity**: LOW (likely 1-line fix once mutation site identified)

## Artifacts

- **Debug logs**: `pytest_db_at_028_debug.log` (1,275 lines)
- **Debug excerpt**: `debug_excerpt.txt` (first 60 DIAG lines)
- **Patch file**: `../../patches/nanobrag_debug_instrumentation.patch`
- **Build log**: `nanobragg_build.log`

## References

- **Blocking initiative**: ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)
- **Spec**: docs/spec-db-core.md §§20-40 (detector configuration, oversampling semantics)
- **Prior evidence**: ARCH-SIM-CONSTRUCTION-001 Phase C.4 summary (2025-12-04T235959Z)
- **Unblock decision**: Portfolio Status problems_ledger_service.md (2025-12-02T194500Z)
