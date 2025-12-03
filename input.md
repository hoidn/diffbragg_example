# Input for Ralph (Loop 2025-12-03T044428Z)

## Summary
Implement deep copy fix in nanobrag_torch Detector class to prevent DetectorConfig.oversample field mutation, resolving the root cause identified in Phase A (Case A: shared mutable state).

## Mode
none (diagnostics: targeted bugfix per Environment Freeze exception clause)

## InitiativeType
diagnostics

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch oversample parameter investigation (Phase B: fix DetectorConfig mutation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (will validate oversample=3 preserved, chi²/pixel ≤1e2)
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity` (will validate ROI correlation ≥0.2)

## Artifacts
`plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T044428Z/`
- `detector_deep_copy_fix.patch` (final clean patch showing only the 2-line fix)
- `pytest_db_at_028_debug.log` (test run WITH debug instrumentation to confirm oversample=3 preserved)
- `pytest_db_at_028_clean.log` (test run AFTER removing debug prints, final validation)
- `pytest_db_at_029_clean.log` (structure parity test, final validation)
- `debug_output_analysis.md` (analysis confirming oversample=3 across all 209 runs)
- `nanobragg_rebuild.log` (rebuild output)
- `environment_tag.txt` (environment state tag)
- `summary.md` (loop summary)

## Do Now

**Root Cause Recap**: Phase A identified that `Detector.__init__()` stores a reference to the `DetectorConfig` object (`self.config = config`), allowing shared mutable state when the same config instance is reused. This causes `oversample=3` to mutate to `-1` between simulator runs.

**Fix Strategy**: Add deep copy in `Detector.__init__()` so each Detector instance gets its own independent config copy.

### Task 1: Implement Deep Copy Fix

**File**: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/models/detector.py`

**Change 1** — Add import at module top (after existing imports, around line 10):

Find the import block at the top of the file and add:
```python
from copy import deepcopy
```

**Change 2** — Deep copy config in `__init__` method (around line 30):

Find this line inside `Detector.__init__()`:
```python
self.config = config
```

Replace it with:
```python
self.config = deepcopy(config)  # Deep copy to prevent shared mutable state
```

**Expected diff**:
```diff
+from copy import deepcopy

 class Detector:
     def __init__(self, config: Optional[DetectorConfig] = None, device=None, dtype=torch.float32):
         ...
         if config is None:
             config = DetectorConfig()
-        self.config = config
+        self.config = deepcopy(config)  # Deep copy to prevent shared mutable state
```

### Task 2: Rebuild nanobrag_torch

**Commands**:
```bash
cd /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch
pip install -e . > /home/ollie/Documents/diffbragg_example/plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T044428Z/nanobragg_rebuild.log 2>&1
```

**Validation**: Build succeeds, logs captured.

### Task 3: Rerun DB-AT-028 WITH Debug Instrumentation

**Purpose**: Confirm that `oversample=3` is now preserved across all 209 simulator runs (not mutating to -1).

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv -s tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T044428Z/pytest_db_at_028_debug.log 2>&1
```

**Expected debug output pattern** (should see this CONSISTENTLY for all 209 runs):
```
[DIAG-OVERSAMPLE] simulator.run() called with oversample=None
[DIAG-OVERSAMPLE] self.detector.config.oversample=3  ← STAYS 3 (not -1!)
[DIAG-OVERSAMPLE] oversample after config read: 3
```

**Should NOT see**:
- `[DIAG-OVERSAMPLE] Entering auto-selection branch` (should never enter if oversample=3)
- `auto-selected N-fold oversampling` messages

**Expected test result**: PASS (chi²/pixel initial ≤ 1e2)

### Task 4: Analyze Debug Output

Create `debug_output_analysis.md` with:

1. Extract all `[DIAG-OVERSAMPLE] self.detector.config.oversample=` lines from the debug log
2. Count occurrences of `oversample=3` vs `oversample=-1`
3. Confirm ZERO `oversample=-1` occurrences (all should be 3)
4. Confirm ZERO "Entering auto-selection branch" occurrences
5. Document first divergence point (should be NONE)

**Example analysis template**:
```markdown
# Debug Output Analysis — DIAG-NANOBRAGG-OVERSAMPLE-001 Phase B

## Summary
Deep copy fix successfully prevents DetectorConfig.oversample mutation.

## Oversample Values Across 209 Runs
- `oversample=3`: 209 occurrences ✅
- `oversample=-1`: 0 occurrences ✅

## Auto-Selection Branch
- "Entering auto-selection branch": 0 occurrences ✅
- "auto-selected N-fold oversampling": 0 occurrences ✅

## Conclusion
Fix SUCCESSFUL. DetectorConfig.oversample=3 preserved across all simulator runs.
```

### Task 5: Remove Debug Instrumentation

**File**: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py`

Remove the debug print statements added in Phase A (lines with `[DIAG-OVERSAMPLE]`):
- Lines ~770-772 (first debug block)
- Lines ~775-777 (second debug block)
- Lines ~787-789 (third debug block)

**Validation**: Clean `git diff` should show ONLY the deep copy changes (import + line 30), not the debug prints.

### Task 6: Create Final Patch File

**Commands**:
```bash
cd /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch
git add src/nanobrag_torch/models/detector.py
git diff --cached > /home/ollie/Documents/diffbragg_example/plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/detector_deep_copy_fix.patch
```

**Expected patch content**: Should show ONLY:
1. `from copy import deepcopy` import
2. `self.config = deepcopy(config)` replacement

(NOT the debug prints, those were removed in Task 5)

### Task 7: Final Validation (Clean Run)

Rerun both acceptance tests WITHOUT debug instrumentation:

```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T044428Z/pytest_db_at_028_029_clean.log 2>&1
```

**Expected**: Both tests PASS
- DB-AT-028: `chi²/pixel initial ≤ 1e2` ✅ (currently fails: 1.084e+05)
- DB-AT-029: `median ROI correlation before ≥ 0.2` ✅ (currently fails: -0.037)

### Task 8: Update docs/findings.md

Find the existing `[DIAG-OVERSAMPLE-001]` entry (added in Phase A) and update it:

**Old entry**:
```markdown
### [DIAG-OVERSAMPLE-001] nanobrag_torch Oversample Parameter Handling Investigation

**Status**: In Progress (Phase A complete: root cause identified as Case A)

**Root Cause**: (to be filled after log analysis: Case A/B/C with brief explanation)

**Resolution Path**: (to be filled: Phase B fix plan or escalation recommendation)
```

**Updated entry**:
```markdown
### [DIAG-OVERSAMPLE-001] nanobrag_torch Oversample Parameter Handling Investigation

**Status**: RESOLVED (Phase B complete: deep copy fix implemented and validated)

**Context**: ARCH-SIM-CONSTRUCTION-001 stuck due to suspected nanobrag_torch `oversample` parameter issue. Explicit `DetectorConfig(oversample=3)` setting didn't prevent auto-selection code path, causing ~23,317× magnitude discrepancy in reconstruction helpers.

**Investigation**: Phase A added debug instrumentation, captured 1,166 debug lines showing `oversample=3` on first invocation then `oversample=-1` on all 208 subsequent runs. Root cause: `Detector.__init__()` stored reference to DetectorConfig instead of deep copy, enabling shared mutable state across Simulator instances.

**Root Cause**: Case A — DetectorConfig.oversample field mutation due to shared mutable state. File: `models/detector.py` line 30: `self.config = config` (reference assignment instead of deep copy).

**Resolution**: Phase B implemented deep copy fix in `Detector.__init__()`: imported `deepcopy` from `copy` module, replaced `self.config = config` with `self.config = deepcopy(config)`. Validated via DB-AT-028/029 acceptance tests (both PASS after fix, previously FAIL). Debug logs confirm `oversample=3` preserved across all 209 simulator runs (zero `-1` occurrences, zero auto-selection branch entries).

**Impact**: Unblocked ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy resolved), unblocked ARCH-REFACTOR-001 Phase D.3 (DB-AT-028/029 acceptance gates now passing).

**References**:
- Initiative: DIAG-NANOBRAGG-OVERSAMPLE-001
- Patch: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/detector_deep_copy_fix.patch`
- Artifacts: Phase A `2025-12-03T043000Z/`, Phase B `2025-12-03T044428Z/`
- Unblocks: ARCH-SIM-CONSTRUCTION-001, ARCH-REFACTOR-001
```

### Task 9: Tag Environment State

**Command**:
```bash
echo "nanobragg-deepcopy-fix-2025-12-03" > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T044428Z/environment_tag.txt
```

**Rationale**: Documents environment state per Environment Freeze exception requirement #5.

### Task 10: Write Loop Summary

Create `summary.md` documenting:
- Fix implemented (deep copy in Detector.__init__())
- Debug validation results (oversample=3 preserved across all runs)
- Final clean validation results (DB-AT-028/029 PASS)
- Environment Freeze compliance confirmed (all 5 requirements met)
- Initiatives unblocked (ARCH-SIM-CONSTRUCTION-001, ARCH-REFACTOR-001 Phase D.3)

## How-To Map

### Step-by-step execution order:

1. **Edit detector.py**: Add `from copy import deepcopy` import, replace `self.config = config` with `self.config = deepcopy(config)`
2. **Rebuild nanobrag_torch**: `cd src/nanobrag-torch && pip install -e . > .../nanobragg_rebuild.log 2>&1`
3. **Run DB-AT-028 with debug**: Capture debug logs to confirm oversample=3 preserved
4. **Analyze debug output**: Extract [DIAG-OVERSAMPLE] lines, confirm zero `-1` occurrences
5. **Remove debug prints**: Clean up simulator.py (remove Phase A instrumentation)
6. **Create final patch**: `git diff --cached > .../detector_deep_copy_fix.patch`
7. **Final validation**: Rerun DB-AT-028/029 without debug, expect both PASS
8. **Update findings.md**: Mark DIAG-OVERSAMPLE-001 as RESOLVED with fix details
9. **Tag environment**: Create environment_tag.txt
10. **Write summary.md**: Document loop outcome and unblocked initiatives

### Expected timeline:
- Edit + rebuild: ~5 minutes
- Test run with debug: ~40 seconds
- Debug analysis: ~10 minutes
- Clean up + final patch: ~5 minutes
- Final validation: ~80 seconds (2 tests)
- Docs update + summary: ~10 minutes
- **Total: ~30-35 minutes**

### Key environment variables:
- `DBEX_SMOKE_SIGMA_SOURCE=metadata` — Use external_lookup sigma source (required for DB-AT-028/029)
- `DBEX_SMOKE_DETECTOR_SIZE=full` — Full 2527×2463 detector
- `NANOBRAGG_DISABLE_COMPILE=1` — Disable torch.compile for reproducible output
- `KMP_DUPLICATE_LIB_OK=TRUE` — Suppress OpenMP duplicate library warnings

## Pitfalls To Avoid

1. **Do NOT forget to import deepcopy** — the fix requires both the import AND the usage.
2. **Do NOT use shallow copy (copy.copy)** — DetectorConfig contains nested objects that need deep copying.
3. **Do NOT skip the debug validation step (Task 3)** — we need to confirm oversample=3 is preserved before removing debug prints.
4. **Do NOT commit the debug instrumentation** — Task 5 must remove Phase A debug prints before creating final patch.
5. **Do NOT skip rebuild step** — changes to nanobrag_torch require reinstall before they take effect.
6. **Do NOT proceed if debug logs still show oversample=-1** — the fix didn't work, escalate to Galph.
7. **Do NOT skip Task 7 (final clean validation)** — we need both tests to PASS to confirm initiative complete.
8. **Environment Freeze compliance**: Document all steps (patch, rebuild, testing) per exception requirements.

## If Blocked

**If nanobrag_torch rebuild fails**:
1. Capture full error output in `nanobragg_rebuild.log`
2. Check for missing dependencies (e.g., torch version mismatches)
3. Document build failure in `summary.md`
4. Escalate to Galph with recommendation: resolve build dependencies or revert change

**If debug logs still show oversample=-1 after fix**:
1. Double-check that deep copy was applied correctly (inspect models/detector.py)
2. Verify rebuild completed successfully (check pip install output)
3. Confirm nanobrag_torch import is from the editable install (not system package)
4. Document in `debug_output_analysis.md` with full excerpt
5. Escalate to Galph: deep copy fix insufficient, may need frozen dataclass or different approach

**If tests still FAIL after fix**:
1. Check debug logs to confirm oversample=3 preserved (if not, see above)
2. If oversample=3 IS preserved but tests still fail:
   - Extract failure signature (chi²/pixel value, ROI correlation value)
   - Compare to Phase A baseline (chi²=1.084e+05, corr=-0.037)
   - If similar: oversample fix didn't resolve root cause, escalate
   - If different: new failure mode, escalate with new signature
3. Document in `summary.md` and escalate to Galph

**If final patch includes debug prints**:
1. Verify Task 5 was executed (debug prints removed from simulator.py)
2. Re-run `git diff` to confirm only detector.py changes present
3. Manually edit patch file to remove debug print hunks if needed
4. Document cleanup in `summary.md`

## Findings Applied

**From planning_notes.md (2025-12-03T044428Z)**:
- **Root cause mechanism**: `Detector.__init__()` line 30 stores reference, not copy
- **Fix strategy**: Deep copy chosen over frozen dataclass (preserves __post_init__ logic)
- **Validation approach**: Debug instrumentation first, clean validation second

**From root_cause_analysis.md (Phase A, 2025-12-03T043000Z)**:
- **Case A identification**: DetectorConfig.oversample mutates from 3 to -1
- **Pattern**: First run correct, all subsequent runs incorrect
- **Debug evidence**: 1,166 lines, 617 auto-selection messages

**From ARCH-SIM-CONSTRUCTION-001 lifecycle_decision.md (2025-12-03T021140Z)**:
- **Repeat-failure guard**: 4 consecutive loops with same signature triggered stuck status
- **Environment constraint**: Cannot modify nanobrag_torch without exception clause approval
- **Unblock requirement**: Fix must resolve ~23,317× magnitude discrepancy

## Pointers

**Spec / Architecture**:
- docs/spec-db-core.md §§20-40 (detector configuration, oversampling semantics)
- CLAUDE.md Environment Freeze exception clause (targeted bugfixes to locally available source)

**Implementation Files**:
- `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/models/detector.py:28-30` (mutation site, target for fix)
- `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/config.py:48` (DetectorConfig dataclass, oversample field default=-1)

**Test / Acceptance**:
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (DB-AT-028: chi²/pixel ≤1e2)
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity` (DB-AT-029: ROI corr ≥0.2)

**Prior Evidence**:
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/root_cause_analysis.md` (Phase A diagnosis)
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/pytest_db_at_028_debug.log` (Phase A debug capture)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/summary.md` (blocked status, ~23,317× magnitude error)

**Initiative Plan**:
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md` (Phase A/B plan, exit criteria)
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T044428Z/planning_notes.md` (Phase B strategy)

## Next Up

**If Phase B successful (tests PASS)**:
- Mark DIAG-NANOBRAGG-OVERSAMPLE-001 as done (all exit criteria satisfied)
- Unblock ARCH-SIM-CONSTRUCTION-001 (resume Phase C.5)
- Unblock ARCH-REFACTOR-001 Phase D.3 (DB-AT-028/029 gates now passing)
- Update docs/fix_plan.md with completion entry

**If Phase B requires iteration**:
- Create Phase B.2 planning loop with alternative fix strategy
- Consider frozen dataclass or mutation site removal approaches
- Escalate to user if complexity exceeds diagnostics initiative scope

## Doc Sync Plan

**Not applicable** — no tests added/renamed this loop.

Existing tests `test_db_at_028_loss_scale_sanity` and `test_db_at_029_structure_parity` reused for validation only.

## Mapped Tests Guardrail

**Collect-only verification**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
```

**Expected**: 2 tests collected

**Status**: Existing tests, no changes to collection expected.

## Normative Math/Physics

Not applicable — this is a bugfix to prevent config mutation, not a change to physics/math equations. Oversample parameter semantics are normative per docs/spec-db-core.md §§20-40, and this fix ensures those semantics are honored (explicit oversample=3 stays 3, doesn't mutate to -1).
