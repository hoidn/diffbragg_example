# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 Batch 2 (bragg_before computation bugfix)

## Summary
Fix test_stage_a_smoke_parity.py fixture to compute bragg_before via simulate_forward_once instead of non-existent mapping_context.bragg_zero_iter attribute.

## Mode
Parity

## InitiativeType
bugfix

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3 Batch 2 bugfix)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small
```
Expected: 2/2 tests PASSED

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z_bugfix/`
- `pytest_parity_batch2_fixed.log` — Full pytest output for both tests after bugfix
- `summary.md` — Turn summary (create new file)

---

## Do Now

**Context**: Phase D.3 Batch 2 migration (commit d696dd51) completed successfully BUT introduced a bug. The fixture tries to use `mapping_context.bragg_zero_iter` (line 174, line 301) which doesn't exist, causing AttributeError. Root cause: Ralph incorrectly assumed this attribute exists; the old facade version called `build_final_bragg_from_stage_a_telemetry` to reconstruct initial Bragg, but that function is now deleted. Solution: Call `simulate_forward_once` with initial (perturbed) geometry to compute bragg_before.

**Goal**: Fix bragg_before computation in stage_a_smoke_result fixture (lines 172-175) by calling simulate_forward_once, AND fix the emit_mapping_context_diagnostics call (line 301) to pass the computed bragg_before instead of non-existent attribute.

**Why**: This is a migration bug, not a pre-existing physics regression. The tests were passing before migration with facade; they should pass after migration with Engine. Current chi²/ROI correlation failures are caused by bragg_before being incorrectly sourced (attribute error would have occurred if test ran to that line).

---

### Step 1: Read Current File

Read `tests/dbex/test_stage_a_smoke_parity.py` fixture section to confirm current bug.

**Expected findings**:
- Line 174: `bragg_before = mapping_context.bragg_zero_iter  # Zero-iteration forward (initial geometry)`
- Line 301: `bragg_model=stage_a_smoke_result["mapping_context"].bragg_zero_iter,`

Both references are invalid (attribute doesn't exist on MappingContext).

---

### Step 2: Import simulate_forward_once

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Location**: Top of file, after other imports (around line 20)

**Add import**:
```python
from dbex.nanobrag_bridge import simulate_forward_once
```

**Rationale**: Need to call simulate_forward_once to compute initial Bragg forward model.

---

### Step 3: Fix bragg_before Computation in Fixture

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Old string** (lines 172-175):
```python
    device_obj = torch.device(config.device)
    # ARCH-REFACTOR-001 Phase D.3 Batch 2 bugfix: build_final_bragg_from_stage_a_telemetry
    # no longer has param_state parameter. Use mapping_context.bragg_zero_iter for "before" state.
    bragg_before = mapping_context.bragg_zero_iter  # Zero-iteration forward (initial geometry)
    bragg_after = bragg_final  # Engine-refined final Bragg
```

**New string**:
```python
    device_obj = torch.device(config.device)
    # ARCH-REFACTOR-001 Phase D.3 Batch 2 bugfix: Compute bragg_before via simulate_forward_once
    # with initial (perturbed) geometry, since build_final_bragg_from_stage_a_telemetry is deleted
    # and mapping_context.bragg_zero_iter doesn't exist.
    bragg_before = simulate_forward_once(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        experiment=mapping_context.experiment,
        device=device_obj,
    )
    bragg_after = bragg_final  # Engine-refined final Bragg
```

**Rationale**:
- `simulate_forward_once` computes forward model with given geometry (perturbed detector/beam/crystal)
- This matches the "before refinement" state that the old facade version was computing
- Uses same inputs/experiment/device as refinement run
- Returns numpy array matching bragg_after shape

---

### Step 4: Fix emit_mapping_context_diagnostics Call

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Old string** (lines 297-303, inside test_db_at_028_loss_scale_sanity function):
```python
    # Emit mapping context diagnostics BEFORE assertions (TOOLING-VIS-001)
    emit_mapping_context_diagnostics(
        mapping_context=stage_a_smoke_result["mapping_context"],
        dataload=stage_a_smoke_result["refgeom_dataload"],
        output_path=artifact_dir / "mapping_context_fixture.json",
        bragg_model=stage_a_smoke_result["mapping_context"].bragg_zero_iter,
        stage_name="fixture_db_at_028",
    )
```

**New string**:
```python
    # Emit mapping context diagnostics BEFORE assertions (TOOLING-VIS-001)
    emit_mapping_context_diagnostics(
        mapping_context=stage_a_smoke_result["mapping_context"],
        dataload=stage_a_smoke_result["refgeom_dataload"],
        output_path=artifact_dir / "mapping_context_fixture.json",
        bragg_model=stage_a_smoke_result["bragg_before"],  # Use computed bragg_before from fixture
        stage_name="fixture_db_at_028",
    )
```

**Rationale**:
- The fixture now computes bragg_before and stores it in stage_a_smoke_result dict
- Pass that computed value instead of trying to access non-existent mapping_context.bragg_zero_iter

---

### Step 5: Find and Fix Second emit_mapping_context_diagnostics Call

Search for second occurrence in test_db_at_029_structure_parity function and fix it too.

**Expected location**: Around line 380-390

Use same fix: replace `bragg_model=stage_a_smoke_result["mapping_context"].bragg_zero_iter,` with `bragg_model=stage_a_smoke_result["bragg_before"],`

---

### Step 6: Run Mapped Tests

Run both test functions:

```bash
mkdir -p plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z_bugfix
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small \
              2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z_bugfix/pytest_parity_batch2_fixed.log
```

**Expected outcome**: 2/2 tests PASSED

**Success criteria**:
- test_db_at_028 validates chi²/pixel initial < 1e2 (sanity check that bragg_before is reasonable)
- test_db_at_029 validates median ROI correlation before refinement >= 0.2 (sanity check that bragg_before correlates with target)
- No AttributeError on mapping_context.bragg_zero_iter
- No import errors for simulate_forward_once
- Chi² reduction and correlation improvement still validated (refinement works correctly)

**If tests still fail**:
- Check if simulate_forward_once signature matches expectations (might need additional params)
- Verify perturbed_detector/beam/crystal are correct objects (not None)
- Check if device_obj is correct (should be torch.device from config.device)
- Capture full traceback and failure signature in pytest log

---

### Step 7: Update Artifacts

Write Turn Summary to `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z_bugfix/summary.md`:

```markdown
### Turn Summary
Fixed ARCH-REFACTOR-001 Phase D.3 Batch 2 migration bug where fixture used non-existent mapping_context.bragg_zero_iter attribute.
Replaced with simulate_forward_once call using initial perturbed geometry; both DB-AT tests now pass with correct bragg_before computation.
Phase D.3 Batch 2 complete; facade usage reduced to 2 files (dead import in test_torch_refine_smoke.py, active call in dbex/tools/stage_a_adam.py).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z_bugfix/ (pytest_parity_batch2_fixed.log)
```

---

## How-To Map

All commands listed above. Key steps:

1. **Read file**: `tests/dbex/test_stage_a_smoke_parity.py` to confirm bug
2. **Add import**: Import simulate_forward_once from dbex.nanobrag_bridge
3. **Fix bragg_before computation** (lines 172-175): Replace mapping_context.bragg_zero_iter with simulate_forward_once call
4. **Fix emit call 1** (line 301): Replace bragg_model=mapping_context.bragg_zero_iter with bragg_model=stage_a_smoke_result["bragg_before"]
5. **Find and fix emit call 2**: Search for second occurrence in test_db_at_029 and apply same fix
6. **Run tests**: pytest command above (2 selectors)
7. **Write summary**: Create summary.md in bugfix artifacts dir

---

## Pitfalls To Avoid

1. **DO NOT** change test assertions or tolerances — this is a fixture bug, not a physics regression
2. **DO NOT** modify refinement logic or Engine pattern — migration is correct, only bragg_before computation is wrong
3. **DO NOT** change mapping_context construction — it's correct, it just never had bragg_zero_iter attribute
4. **DO NOT** forget to import simulate_forward_once at top of file
5. **DO NOT** forget to fix BOTH emit_mapping_context_diagnostics calls (in test_db_at_028 AND test_db_at_029)
6. **DO** use exact same inputs/detector/beam/crystal/experiment for simulate_forward_once as used for refinement
7. **DO** use device_obj from torch.device(config.device) for simulate_forward_once
8. **DO** verify bragg_before shape matches bragg_after shape (both should be [panel, slow, fast] numpy arrays)
9. **DO** use Edit tool (not Write) — this is an existing file
10. **DO** preserve all downstream logic (ROI correlations, chi² computation, etc.) — unchanged

**Environment Freeze Reminder**: Assume frozen runtime. If import errors occur, record signature in fix_plan.md and mark blocked; do not attempt pip installs or package upgrades.

---

## If Blocked

**Scenario 1: simulate_forward_once import fails**
- **Action**: Record error signature, mark blocked, update Attempts History with block reason
- **Do NOT**: Attempt environment changes or package installs

**Scenario 2: simulate_forward_once signature mismatch (wrong params)**
- **Action**: Read dbex/nanobrag_bridge.py to check function signature, adjust call as needed
- **If incompatible**: Mark blocked, document incompatibility in Attempts History
- **Do NOT**: Skip the fix or leave buggy code in place

**Scenario 3: Tests still fail after bugfix (chi² or correlation out of bounds)**
- **Action**: Verify simulate_forward_once produces reasonable bragg_before (check shape, mean, std in pytest output)
- **If bragg_before looks wrong**: Debug simulate_forward_once call params (detector/beam/crystal/experiment)
- **If bragg_before looks correct but tests fail**: This may be genuine physics regression, mark blocked and open separate initiative
- **Do NOT**: Weaken test assertions without confirming bragg_before is computed correctly

**Scenario 4: AttributeError persists on mapping_context.bragg_zero_iter**
- **Action**: Verify all occurrences replaced (use grep to search for "bragg_zero_iter" in file)
- **If missed occurrences**: Fix them all
- **Do NOT**: Add fake bragg_zero_iter attribute to MappingContext — fix the callers instead

---

## Findings Applied (Mandatory)

**Relevant findings from docs/findings.md**:

- **ARCH-REFACTOR-001 Phase D.2 CLI Blueprint** (2025-12-02T220000Z): Engine pattern is correct; bragg_final extraction from engine._artifacts["stage_a"].bragg_full is correct. Bug is only in bragg_before computation.
- **TOOLING-VIS-001**: emit_mapping_context_diagnostics requires bragg_model parameter (numpy array); passing non-existent attribute causes AttributeError.
- **CONFORMANCE-001**: Tests require KMP_DUPLICATE_LIB_OK=TRUE (handled by pytest fixtures).
- **RUNTIME-001**: Tests require NANOBRAGG_DISABLE_COMPILE=1 (handled by pytest fixtures).

No findings contradict this bugfix approach. simulate_forward_once is the standard way to compute forward model with given geometry.

---

## Pointers

- **Plan**: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase D checklist, D.3 description)
- **Original migration**: commit d696dd51 (introduced bug)
- **Previous attempt summary**: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/summary.md` (documents original migration + bugfixes)
- **simulate_forward_once signature**: `dbex/nanobrag_bridge.py:1230` (check params if needed)
- **Fixture source**: `tests/dbex/test_stage_a_smoke_parity.py:68-269` (stage_a_smoke_result fixture)
- **Test functions**:
  - `tests/dbex/test_stage_a_smoke_parity.py:296` (test_db_at_028_loss_scale_sanity)
  - `tests/dbex/test_stage_a_smoke_parity.py:376` (test_db_at_029_structure_parity)

---

## Next Up (optional)

**After 2/2 tests PASSED**:
1. **Recommended next step**: Remove dead facade import in test_torch_refine_smoke.py (quick cleanup before moving to Batch 3)
2. **Alternative**: Proceed directly to D.3 Batch 3 (dbex/tools/stage_a_adam.py migration)

**After all D.3 batches complete**: Proceed to D.5 (facade deletion) with comprehensive verification checklist.

---

## Doc Sync Plan (Conditional)

Not applicable this loop (bugfix only, no new tests, no test renames).

---

## Mapped Tests Guardrail

Both mapped selectors collect and should pass after bugfix:
- `test_db_at_028_loss_scale_sanity` — validates chi²/pixel initial < 1e2 and chi² reduction
- `test_db_at_029_structure_parity` — validates median ROI correlation before >= 0.2 and improvement after

No new tests created this loop.

---

## Hard Gate

N/A (no selector changes this loop; bugfix preserves existing test contract).

---

## Normative Math/Physics

N/A (no physics changes; bugfix restores correct "before" state computation per original facade behavior).

### Debugging Notes

If you need to verify simulate_forward_once is working correctly, add temporary diagnostic prints in the fixture (after line 175):

```python
print(f"DEBUG bragg_before: shape={bragg_before.shape}, mean={bragg_before.mean():.6f}, std={bragg_before.std():.6f}, max={bragg_before.max():.6f}")
print(f"DEBUG bragg_after: shape={bragg_after.shape}, mean={bragg_after.mean():.6f}, std={bragg_after.std():.6f}, max={bragg_after.max():.6f}")
```

Expected: Both should have same shape (e.g., [4, 2463, 2527]), bragg_before should have reasonable mean/std (not all zeros), and bragg_after should show different stats after refinement.
