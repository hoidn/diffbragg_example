# Input for Ralph (Loop 2025-12-03T043000Z)

## Summary
Add minimal debug instrumentation to nanobrag_torch to investigate why explicit `oversample=3` parameter doesn't prevent auto-selection, enabling root cause diagnosis for ARCH-SIM-CONSTRUCTION-001 reconstruction magnitude discrepancy.

## Mode
none (diagnostics: environment debugging per Environment Freeze exception clause)

## InitiativeType
diagnostics

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch oversample parameter investigation (Phase A: debug instrumentation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (will use to capture debug output)

## Artifacts
`plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/`
- `nanobrag_debug_instrumentation.patch` (patch file per Environment Freeze exception requirement)
- `nanobragg_build.log` (rebuild output documenting build process)
- `pytest_db_at_028_debug.log` (test run with `-s` flag capturing debug prints)
- `root_cause_analysis.md` (analysis of debug logs identifying Case A/B/C)
- `summary.md` (loop summary)

## Do Now

**Environment Freeze Exception Compliance**: This work is authorized per CLAUDE.md Environment Freeze exception clause for "targeted bugfixes to locally available source code... when blocking critical paths". All 5 requirements will be satisfied: (1) patch file saved, (2) rebuild documented, (3) testing confirms unblock, (4) findings.md updated, (5) environment tagged.

### Task 1: Add Debug Instrumentation to nanobrag_torch

**File**: `src/nanobrag-torch/src/nanobrag_torch/simulator.py`

**Location**: Lines ~769-803 (inside `Simulator.run()` method, at the oversample parameter handling section)

**Changes to add** (insert BEFORE existing logic, do not modify existing code):

```python
def run(self, oversample=None, ...):
    # ===== BEGIN DEBUG INSTRUMENTATION (DIAG-NANOBRAGG-OVERSAMPLE-001) =====
    print(f"[DIAG-OVERSAMPLE] simulator.run() called with oversample={oversample}")
    print(f"[DIAG-OVERSAMPLE] self.detector.config.oversample={self.detector.config.oversample}")
    # ===== END DEBUG INSTRUMENTATION =====

    if oversample is None:
        oversample = self.detector.config.oversample
        # ===== BEGIN DEBUG INSTRUMENTATION (DIAG-NANOBRAGG-OVERSAMPLE-001) =====
        print(f"[DIAG-OVERSAMPLE] oversample after config read: {oversample}")
        # ===== END DEBUG INSTRUMENTATION =====

    if oversample == -1:
        # ===== BEGIN DEBUG INSTRUMENTATION (DIAG-NANOBRAGG-OVERSAMPLE-001) =====
        print(f"[DIAG-OVERSAMPLE] Entering auto-selection branch (oversample == -1)")
        # ===== END DEBUG INSTRUMENTATION =====
        # ... existing auto-selection logic ...
```

**Expected debug output pattern** (will appear in pytest log when run with `-s` flag):
```
[DIAG-OVERSAMPLE] simulator.run() called with oversample=None
[DIAG-OVERSAMPLE] self.detector.config.oversample=3
[DIAG-OVERSAMPLE] oversample after config read: 3
```

**Root cause diagnosis from debug output**:
- **Case A** (DetectorConfig.oversample not preserved): `self.detector.config.oversample=-1` → fix dataclass
- **Case B** (caller passes override): `simulator.run() called with oversample=-1` → find caller
- **Case C** (auto-selection logic bug): Both show `=3` but "Entering auto-selection branch" still prints → simulator bug

### Task 2: Save Patch File

**Command**:
```bash
cd src/nanobrag-torch
git diff > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch
```

**Validation**: Patch file exists and contains the debug print additions.

### Task 3: Rebuild nanobrag_torch

**Commands** (document exact steps in `nanobragg_build.log`):
```bash
cd src/nanobrag-torch
pip install -e . > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/nanobragg_build.log 2>&1
```

**Validation**: Build succeeds, logs captured.

### Task 4: Rerun DB-AT-028 with Debug Output

**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv -s tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/pytest_db_at_028_debug.log 2>&1
```

**Note**: The `-s` flag is CRITICAL — it disables pytest output capture so debug prints are visible.

**Expected**: Test FAILS (same signature as before), but debug logs reveal oversample parameter flow.

### Task 5: Analyze Debug Logs and Identify Root Cause

**Steps**:
1. Search pytest_db_at_028_debug.log for all `[DIAG-OVERSAMPLE]` lines
2. Extract the first few occurrences (should be ~209 total based on prior logs)
3. Determine which Case (A/B/C) the evidence supports
4. Write `root_cause_analysis.md` with:
   - Debug output excerpt (first 10-20 lines)
   - Case identification (A/B/C) with justification
   - Recommended next step (Phase B fix or escalation)

**Example analysis template**:
```markdown
# Root Cause Analysis — DIAG-NANOBRAGG-OVERSAMPLE-001 Phase A

## Debug Output Excerpt
(paste first 20 [DIAG-OVERSAMPLE] lines from pytest log)

## Case Identification
**Case X**: (A/B/C)

**Evidence**:
- `self.detector.config.oversample = <value>`
- `simulator.run() called with oversample = <value>`
- Auto-selection branch: (entered / not entered)

**Conclusion**: (brief explanation matching one of the three cases)

## Recommended Next Step
- **If Case A**: Phase B fix DetectorConfig dataclass to preserve oversample field
- **If Case B**: Return to ARCH-SIM-CONSTRUCTION-001 to fix caller passing override
- **If Case C**: Phase B fix simulator auto-selection logic bug
- **If unclear**: Escalate to user/maintainers (cannot debug further)
```

### Task 6: Update docs/findings.md

**Action**: Add new finding entry under appropriate section (e.g., "## Diagnostics Findings" or "## Simulator Runtime"):

```markdown
### [DIAG-OVERSAMPLE-001] nanobrag_torch Oversample Parameter Handling Investigation

**Status**: In Progress (Phase A complete: root cause identified as Case X)

**Context**: ARCH-SIM-CONSTRUCTION-001 stuck due to suspected nanobrag_torch `oversample` parameter issue. Explicit `DetectorConfig(oversample=3)` setting doesn't prevent auto-selection code path, causing ~23,317× magnitude discrepancy in reconstruction helpers.

**Investigation**: Added debug instrumentation to nanobrag_torch/simulator.py per Environment Freeze exception clause. Patch file: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`.

**Root Cause**: (to be filled after log analysis: Case A/B/C with brief explanation)

**Resolution Path**: (to be filled: Phase B fix plan or escalation recommendation)

**References**:
- Initiative: DIAG-NANOBRAGG-OVERSAMPLE-001
- Artifacts: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/`
- Blocks: ARCH-SIM-CONSTRUCTION-001
```

### Task 7: Tag Environment State

**Command**:
```bash
echo "nanobragg-debug-oversample-2025-12-03" > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/environment_tag.txt
```

**Rationale**: Documents environment state per Environment Freeze exception requirement #5.

## How-To Map

### Step-by-step execution order:

1. **Edit nanobrag_torch simulator.py**: Add 6 debug print statements (3 insertion points) per Task 1
2. **Save patch**: `cd src/nanobrag-torch && git diff > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
3. **Rebuild nanobrag_torch**: `cd src/nanobrag-torch && pip install -e . > ../../plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/nanobragg_build.log 2>&1`
4. **Rerun DB-AT-028 with debug**: Use command from Task 4 (with `-s` flag)
5. **Analyze logs**: Extract [DIAG-OVERSAMPLE] lines, identify Case A/B/C, write `root_cause_analysis.md`
6. **Update findings**: Add DIAG-OVERSAMPLE-001 entry to `docs/findings.md`
7. **Tag environment**: Create `environment_tag.txt` per Task 7
8. **Write summary.md**: Document loop outcome and next action

### Expected timeline:
- Edit + patch + rebuild: ~5 minutes
- Test run: ~40 seconds (DB-AT-028 typical duration)
- Log analysis + findings: ~10 minutes
- **Total: ~15-20 minutes**

### Key environment variables:
- `DBEX_SMOKE_SIGMA_SOURCE=metadata` — Use external_lookup sigma source (required for DB-AT-028)
- `DBEX_SMOKE_DETECTOR_SIZE=full` — Full 2527×2463 detector
- `NANOBRAGG_DISABLE_COMPILE=1` — Disable torch.compile for reproducible debug output
- `KMP_DUPLICATE_LIB_OK=TRUE` — Suppress OpenMP duplicate library warnings

## Pitfalls To Avoid

1. **Do NOT modify existing logic in simulator.py** — only ADD debug print statements. Existing code flow must remain unchanged.
2. **Do NOT forget `-s` flag in pytest** — without it, debug prints won't appear in logs.
3. **Do NOT skip patch file creation** — required by Environment Freeze exception clause for rollback/documentation.
4. **Do NOT skip rebuild step** — changes to nanobrag_torch require reinstall before they take effect.
5. **Do NOT analyze without extracting ALL [DIAG-OVERSAMPLE] lines** — pattern may vary across 209 simulator runs.
6. **Do NOT modify DBEX production code** — this initiative is diagnostics only, all changes are in nanobrag_torch.
7. **Do NOT proceed to Phase B fix** — this loop is Phase A (diagnosis only); Phase B (fix) will be separate loop if needed.
8. **Environment Freeze compliance**: Document all steps (patch, rebuild, testing) per exception requirements.

## If Blocked

**If nanobrag_torch rebuild fails**:
1. Capture full error output in `nanobragg_build.log`
2. Check for missing dependencies (e.g., cuda, torch version mismatches)
3. Document build failure in `summary.md`
4. Escalate to Galph with recommendation: either resolve build dependencies or switch to Option B (maintainer investigation)

**If debug output doesn't appear in logs**:
1. Verify pytest was run with `-s` flag
2. Check simulator.py edit was applied (cat the file, look for [DIAG-OVERSAMPLE] strings)
3. Verify rebuild completed successfully (check pip install output)
4. Re-run pytest with explicit `--capture=no` instead of `-s`

**If root cause unclear from logs**:
1. Document the ambiguity in `root_cause_analysis.md`
2. Include full debug output excerpt (all [DIAG-OVERSAMPLE] lines from first ~20 runs)
3. Recommend escalation to user/maintainers in summary.md
4. Do NOT attempt Phase B fix if diagnosis is inconclusive

## Findings Applied

**From problems_ledger_service.md (2025-12-02T194500Z)**:
- **ARCH-SIM-CONSTRUCTION-001 stuck status**: Confirmed 4 implementation loops exhausted, Environment Freeze blocks further debugging without exception clause
- **Unblock path assessment**: Option A (local patch) chosen over Option B (maintainer) for faster resolution
- **Environment Freeze exception requirements**: All 5 requirements documented in implementation.md and enforced in this Do Now

**From ARCH-SIM-CONSTRUCTION-001 lifecycle_decision.md (2025-12-03T021140Z)**:
- **Repeat-failure guard**: 4 consecutive loops with same signature triggered stuck status
- **Environment constraint**: Cannot modify nanobrag_torch without exception clause approval
- **Suspected root cause**: nanobrag_torch `oversample` parameter implementation issue (version/upstream bug)

**From ARCH-SIM-CONSTRUCTION-001 Phase C.4 summary.md (2025-12-04T235959Z)**:
- **Implementation correctness**: explicit `oversample=3` parameter added correctly per spec
- **Empirical contradiction**: Test logs show "auto-selected 3-fold oversampling" 209 times despite explicit setting
- **Static inspection**: simulator.py:770 SHOULD honor `self.detector.config.oversample` when `oversample` parameter is None

## Pointers

**Spec / Architecture**:
- docs/spec-db-core.md §§20-40 (detector configuration, oversampling semantics)
- docs/architecture/calibration_scaling.md (calibration threading requirements)
- CLAUDE.md Environment Freeze exception clause (targeted bugfixes to locally available source)

**Implementation Files**:
- `src/nanobrag-torch/src/nanobrag_torch/simulator.py:769-803` (oversample parameter handling, target for debug instrumentation)
- `dbex/refinement/config_factories.py:48-80, 230` (DBEX DetectorConfig construction, passes `oversample=3`)
- `dbex/nanobrag_bridge.py:1410` (simulate_forward_once caller, passes `oversample=3`)
- `dbex/refinement/reconstruction.py:190-194` (reconstruction cold path, passes `oversample=3`)

**Test / Acceptance**:
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (mapped test for debug output capture)
- DB-AT-028 acceptance criteria: `chi²/pixel initial ≤ 1e2` (currently fails: 1.084e+05)

**Prior Evidence**:
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/summary.md` (Phase C.4 implementation and failure analysis)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T021140Z/lifecycle_decision.md` (stuck status rationale)
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-02T194500Z/problems_ledger_service.md` (unblock path assessment)

**Initiative Plan**:
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md` (Phase A/B plan, exit criteria, risks)

## Next Up

**If Phase A successful (root cause identified)**:
- Create input.md for Phase B (targeted fix based on Case A/B/C)
- Fix implementation will be separate loop with own Do Now

**If Phase A inconclusive**:
- Escalate to user/maintainers per problems.md
- Consider Option B (maintainer investigation) or environment upgrade

**After DIAG-NANOBRAGG-OVERSAMPLE-001 complete**:
- Unblock ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)
- Unblock ARCH-REFACTOR-001 Phase D.3 (reconstruction baseline logic)
- Complete Tier 0 architectural spine

## Doc Sync Plan

**Not applicable** — no tests added/renamed this loop.

Existing test `test_db_at_028_loss_scale_sanity` reused for debug output capture only.

## Mapped Tests Guardrail

**Collect-only verification**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
```

**Expected**: 1 test collected

**Status**: Existing test, no changes to collection expected.
