# DIAG-NANOBRAGG-OVERSAMPLE-001 Phase B Summary — Deep Copy Fix Implementation

## Loop Outcome
**Status**: Implementation complete but FIX INSUFFICIENT — Phase A root cause analysis was incorrect

## Changes Made

### 1. Deep Copy Fix Implementation
**File**: `src/nanobrag-torch/src/nanobrag_torch/models/detector.py`

**Change 1 — Import** (line 8):
```python
from copy import deepcopy
```

**Change 2 — Deep copy config** (line 55):
```python
# Old:  self.config = config
# New:  self.config = deepcopy(config)  # Deep copy to prevent shared mutable state
```

**Rebuild**: Successfully rebuilt nanobrag_torch package (`nanobragg_rebuild.log`)

### 2. Validation Testing
- Ran DB-AT-028 with debug instrumentation enabled
- Test outcome: **FAILED** with chi²/pixel initial = 1.091e+05 (bound: ≤1e2)
- Baseline comparison: 1.091e+05 vs original 1.084e+05 (essentially unchanged)

### 3. Debug Analysis
Analyzed pytest_db_at_028_debug.log (1495 lines, 292 simulator runs):

**Oversample distribution**:
- `oversample=3`: 2 occurrences (first + last run only)
- `oversample=-1`: 290 occurrences
- Auto-selection branch entered: 290 times

**Pattern identified**:
```
Run 1:       oversample=3     ✅
Runs 2-291:  oversample=-1    ❌ (auto-selection, wrong!)
Run 292:     oversample=3     ✅
```

## Root Cause Correction

### Phase A Was Wrong
**Phase A hypothesis**: Single DetectorConfig instance being mutated from oversample=3 to -1 due to reference assignment in `Detector.__init__()`

**Actual problem**: Multiple **different** DetectorConfig instances being created with different oversample values:
- 2 instances have oversample=3 (correct, explicitly set)
- 290 instances have oversample=-1 (wrong, default value)

### Why Deep Copy Doesn't Fix It
The deep copy fix prevents mutation WITHIN each Detector instance (working as designed), but it doesn't prevent upstream code from creating NEW DetectorConfig instances with the default `oversample=-1` value.

**Analogy**: We fixed the house locks (deep copy), but burglars are still coming in because 290 houses were built with the wrong blueprints (wrong config instances created upstream).

## Config Lifecycle Investigation Needed

The fix needs to be upstream where DetectorConfig instances are created. Need to trace:

1. **Where are the 290 DetectorConfig(oversample=-1) instances created?**
   - Stage A refinement code?
   - Simulator warm cache?
   - ROI retargeting?

2. **Why only 2/292 have oversample=3?**
   - First run: Likely the initial config passed from test fixture
   - Last run: Unknown (needs investigation)
   - Middle 290 runs: Default configs being created somewhere

3. **Fix options**:
   - **Option A**: Ensure all DetectorConfig creation inherits oversample from initial config
   - **Option B**: Make DetectorConfig frozen/immutable to catch improper creation
   - **Option C**: Store oversample at RefinementContext level and pass explicitly

## Test Results
**DB-AT-028**: FAILED
- Acceptance criterion: chi²/pixel initial ≤ 1e2
- Actual value: 1.091e+05
- Status: ~1091× over bound (no improvement from baseline)

**DB-AT-029**: Not run (blocked on DB-AT-028)

## Metrics
- Files modified: 1 (detector.py)
- Lines added: +2 (import + deep copy)
- Lines changed: 1 (config assignment)
- Package rebuild: successful
- Test runtime: 16.40s
- Environment Freeze compliance: ✅ (patch file ready, rebuild documented)

## Artifacts
- `detector_deep_copy_fix.diff` (2-line change, cleanly isolated)
- `pytest_db_at_028_debug.log` (1495 lines, full debug trace)
- `debug_output_analysis.md` (pattern analysis)
- `nanobragg_rebuild.log` (build validation)
- `summary.md` (this document)

## Environment State
Tag: `nanobragg-deepcopy-fix-2025-12-03` (insufficient for resolution)

Deep copy fix keeps Detector instances safe, but doesn't address the real problem: multiple DetectorConfig instances with wrong defaults.

## Next Actions (for Galph)
1. Mark Phase B as "implemented but blocked — root cause mismatch"
2. Open Phase C: DetectorConfig lifecycle investigation
   - Use callchain.md to trace config creation from test fixture → Stage A → Simulator
   - Find where 290 DetectorConfig(oversample=-1) instances originate
   - Design fix at the config-creation level, not Detector level
3. Keep deep copy change (defensive programming, prevents future mutation issues)
4. Update DIAG-NANOBRAGG-OVERSAMPLE-001 exit criteria to reflect correct root cause

## Lessons Learned
- **Static analysis insufficient**: Phase A relied on code inspection; runtime debug logs revealed the true pattern
- **Test-driven investigation**: Debug instrumentation was essential to discover multiple-instance problem
- **Root cause validation**: Always validate hypothesis with runtime evidence before implementing fixes
- **Defensive still valuable**: Even though deep copy doesn't solve THIS problem, it prevents a different mutation class

## Blocked Items
- ARCH-SIM-CONSTRUCTION-001 (still blocked, oversample issue unresolved)
- ARCH-REFACTOR-001 Phase D.3 (DB-AT-028/029 gates still failing)

---

**Conclusion**: Deep copy fix is **technically correct** (prevents Detector-level mutation) but **strategically insufficient** (doesn't address upstream config creation). Root cause was misidentified in Phase A. Phase C needed to investigate DetectorConfig lifecycle.
