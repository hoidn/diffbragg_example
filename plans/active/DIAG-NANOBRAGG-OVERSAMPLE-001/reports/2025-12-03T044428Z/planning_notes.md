# Phase B Planning Notes — DIAG-NANOBRAGG-OVERSAMPLE-001
**Date**: 2025-12-03T044428Z
**Phase**: B (DetectorConfig Mutation Fix)
**Analyst**: Galph (supervisor)

## Context

Phase A successfully identified root cause as **Case A**: `DetectorConfig.oversample` field is being mutated from 3 to -1 between the first and second `simulator.run()` calls.

**Evidence from Ralph's Phase A execution** (commit 1f880ed8):
- Debug instrumentation captured 1,166 lines
- Pattern: First invocation shows `self.detector.config.oversample=3` (correct)
- Second invocation shows `self.detector.config.oversample=-1` (mutated!)
- All 208 subsequent invocations show `-1` and enter auto-selection branch
- 617 total "auto-selected 3-fold oversampling" messages

## Root Cause Analysis

### Code Inspection Findings

**Mutation Mechanism Identified:**

File: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/models/detector.py`

Lines 28-30:
```python
# Use provided config or create default
if config is None:
    config = DetectorConfig()  # Use defaults
self.config = config  # ← STORES REFERENCE, NOT COPY!
```

**Problem**: The `Detector.__init__()` method stores a **reference** to the `DetectorConfig` object, not a copy. When the same `DetectorConfig` instance is:
1. Used to create multiple `Detector` instances, OR
2. Reused across `Simulator` instances, OR
3. Mutated by any code that has a reference to it

...then ALL `Detector`/`Simulator` instances that share that config will see the mutations.

**Why oversample changes from 3 to -1:**
- The most likely scenario is that some initialization or reset code is setting the config back to defaults
- OR multiple `DetectorConfig` instances are being created but a shared reference is somehow propagating

## Fix Strategy

### Option 1: Deep Copy in Detector.__init__() ✅ CHOSEN

**Implementation:**
1. Import `deepcopy` from `copy` module at top of `models/detector.py`
2. Replace line 30: `self.config = config` with `self.config = deepcopy(config)`

**Advantages:**
- Minimal, surgical change (2 lines: 1 import, 1 replacement)
- Preserves existing `__post_init__` logic in `DetectorConfig` (beam center auto-calculation, pivot selection, etc.)
- Each `Detector` instance gets its own independent config copy
- No downstream API changes required
- Complies with Environment Freeze exception (targeted fix, well-scoped)

**Code change:**
```python
# At top of models/detector.py (after existing imports)
from copy import deepcopy

# In Detector.__init__() method, line 30
self.config = deepcopy(config)  # Deep copy to prevent shared mutable state
```

### Option 2: Frozen Dataclass ❌ REJECTED

**Why rejected:**
- `DetectorConfig.__post_init__()` legitimately mutates fields (e.g., auto-calculating beam centers, setting pivot)
- Making it `frozen=True` would break this initialization logic
- Would require extensive refactoring of `DetectorConfig` to move mutation logic elsewhere
- Too broad for a diagnostics initiative targeting a specific bug

### Option 3: Find and Remove Mutation Site ❌ NOT FEASIBLE

**Why not feasible:**
- Debug logs don't show WHERE the mutation happens, only WHEN (between first and second run)
- Would require extensive instrumentation across the entire nanobrag_torch codebase
- Risk of missing the mutation site or finding multiple legitimate mutation sites
- Not aligned with "minimal targeted fix" philosophy of Environment Freeze exception

## Implementation Plan

### File Changes

**File**: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/models/detector.py`

**Change 1** — Add import (after existing imports, ~line 10):
```python
from copy import deepcopy
```

**Change 2** — Deep copy config (line ~30, in `__init__` method):
```python
# OLD:
self.config = config

# NEW:
self.config = deepcopy(config)  # Deep copy to prevent shared mutable state
```

### Validation Strategy

**Step 1**: Rebuild nanobrag_torch with the fix
```bash
cd /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch
pip install -e .
```

**Step 2**: Rerun DB-AT-028 with debug instrumentation STILL IN PLACE (from Phase A)
- This allows us to confirm oversample=3 is preserved across ALL 209 runs
- Expected debug output pattern:
  ```
  [DIAG-OVERSAMPLE] self.detector.config.oversample=3  # First run
  [DIAG-OVERSAMPLE] self.detector.config.oversample=3  # Second run ✅ FIXED!
  [DIAG-OVERSAMPLE] self.detector.config.oversample=3  # All subsequent runs
  ```
- Should see ZERO "Entering auto-selection branch" messages
- Should see ZERO "auto-selected N-fold oversampling" messages

**Step 3**: Validate DB-AT-028/029 acceptance criteria
- DB-AT-028: `chi²/pixel initial ≤ 1e2` (currently fails: 1.084e+05)
- DB-AT-029: `median ROI correlation before ≥ 0.2` (currently fails: -0.037)

**Step 4**: Remove debug instrumentation and create final patch
- Revert the Phase A debug prints (clean up simulator.py)
- Create Phase B patch file showing only the deep copy fix
- Save to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/detector_deep_copy_fix.patch`

## Expected Outcomes

### Success Metrics

1. **Debug logs**: All 209 simulator runs show `oversample=3` (not -1)
2. **Test results**: DB-AT-028/029 PASS
   - `chi²/pixel initial` drops from ~1e5 to ≤1e2
   - `median ROI correlation before` rises from ~-0.04 to ≥0.2
   - `bragg_after_mean` changes from ~1e-5 to ~0.24 (expected scale)
3. **Reconstruction magnitude**: ~23,317× discrepancy resolves
4. **ARCH-SIM-CONSTRUCTION-001**: Unblocked, can resume Phase C.5

### Risk Assessment

**LOW RISK** because:
- Change is 2 lines (1 import, 1 replacement)
- Deep copy is a standard Python pattern for preventing shared mutable state
- No API changes, no downstream consumers affected
- Existing tests will validate no regressions

**Potential issues**:
- Deep copy may have small performance cost (negligible: config is small, <20 fields)
- If any code intentionally relies on shared config mutation, it will break (unlikely based on code inspection)

## Artifacts

### This Loop (2025-12-03T044428Z)
- `planning_notes.md` (this file)
- `summary.md` (loop summary, to be written)

### Next Loop (Phase B implementation)
- `detector_deep_copy_fix.patch` (final clean patch)
- `pytest_db_at_028_fixed.log` (test run with fix)
- `pytest_db_at_029_fixed.log` (structure parity test)
- `debug_output_analysis.md` (confirm oversample=3 preserved)
- `nanobragg_rebuild.log` (rebuild output)

## Compliance

### Environment Freeze Exception Requirements

✓ **Requirement 1**: Patch file → `detector_deep_copy_fix.patch` (Phase B implementation loop)
✓ **Requirement 2**: Rebuild documentation → `nanobragg_rebuild.log` captures `pip install -e .` output
✓ **Requirement 3**: Testing confirms fix → DB-AT-028/029 validation
✓ **Requirement 4**: Update findings.md → DIAG-OVERSAMPLE-001 finding (already created Phase A, will update Phase B)
✓ **Requirement 5**: Environment tag → "nanobragg-deepcopy-fix-2025-12-03"

### Initiative Type Constraints

**Initiative type**: diagnostics
**Allowed work**: Adding non-intrusive telemetry and debugging tools, targeted bugfixes to unblock critical paths
**Not allowed**: Changing specs, adjusting tolerances, or gate logic

This fix is **100% compliant**: It's a targeted bugfix (deep copy) that prevents unintended shared mutable state, without changing any semantics, specs, or gates.

## Next Actions

1. **Galph** (this loop): Write `input.md` with explicit implementation instructions
2. **Ralph** (next loop): Implement deep copy fix, rebuild, validate
3. **Galph** (review loop): Confirm ARCH-SIM-CONSTRUCTION-001 unblocked, update portfolio

## References

- **Phase A artifacts**: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/`
- **Root cause analysis**: `root_cause_analysis.md`
- **Debug logs**: `pytest_db_at_028_debug.log` (1,166 lines)
- **Blocking initiative**: ARCH-SIM-CONSTRUCTION-001
- **Spec**: docs/spec-db-core.md §§20-40 (detector configuration, oversampling semantics)
