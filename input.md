# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 Batch 2 (bragg_before CORRECTIVE FIX)

## Summary
Fix test_stage_a_smoke_parity.py fixture to compute bragg_before from PERTURBED geometry (not baseline geometry from mapping_context).

## Mode
Parity

## InitiativeType
bugfix

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3 Batch 2 corrective fix)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small
```
Expected: 2/2 tests PASSED with reasonable chi² (~10-50 initial) and ROI correlation (~0.2-0.4 before)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/`
- `analysis.md` — Root cause analysis (ALREADY WRITTEN by Galph)
- `pytest_parity_batch2_corrected.log` — Full pytest output after corrective fix
- `summary.md` — Turn summary

---

## Do Now

**Context**: Ralph's previous fix (commit fd64e9f3) DID NOT solve the problem. Both tests still FAIL with:
- test_db_at_028: chi²/pixel initial 209817 >> 100 bound
- test_db_at_029: median ROI correlation before -0.037 << 0.2 floor

**Root Cause** (see analysis.md for full details):
Line 175 uses `mapping_context.bragg_zero_iter`, which was computed from **BASELINE** geometry (unperturbed).
But the refinement runs on **PERTURBED** geometry, and `bragg_final` comes from refining that perturbed state.
This creates a 3-state mismatch: baseline → perturbed → refined, when tests expect: perturbed → refined.

**Goal**: Replace line 175 to call `simulate_forward_once` with **PERTURBED** geometry (perturbed_detector/beam/crystal) so `bragg_before` matches the refinement starting point.

**Why Ralph's Previous Fix Was Wrong**:
Ralph kept `mapping_context.bragg_zero_iter` on line 175, which:
1. DOES exist as an attribute (no AttributeError)
2. BUT contains forward model for WRONG geometry (baseline instead of perturbed)
3. Tests expect "before refinement" = perturbed geometry, not "baseline zero-iteration"

---

### Step 1: Import simulate_forward_once (if not already imported)

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Check imports** around lines 10-22 to see if `simulate_forward_once` is already imported from `dbex.nanobrag_bridge`.

**If NOT imported**, add it to the existing import from `dbex.nanobrag_bridge` (line 10-12):

```python
from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    simulate_forward_once,  # Add this line if missing
)
```

---

### Step 2: Replace bragg_before Computation

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Old string** (lines 171-176, EXACT match including comments):
```python
    device_obj = torch.device(config.device)
    # ARCH-REFACTOR-001 Phase D.3 Batch 2 bugfix: Use pre-computed bragg_zero_iter from mapping_context
    # instead of non-existent mapping_context attribute access. The mapping context already computed
    # the zero-iteration forward model via build_mapping_stage_a_context, so reuse it directly.
    bragg_before = mapping_context.bragg_zero_iter  # Zero-iteration forward (baseline geometry)
    bragg_after = bragg_final  # Engine-refined final Bragg
```

**New string**:
```python
    device_obj = torch.device(config.device)
    # ARCH-REFACTOR-001 Phase D.3 Batch 2 CORRECTIVE FIX: Compute bragg_before from PERTURBED geometry
    # (refinement starting point), not from baseline geometry (mapping_context.bragg_zero_iter).
    # The test validates refinement quality by comparing perturbed→refined improvement.
    bragg_before = simulate_forward_once(
        inputs=refinement_inputs,
        detector=perturbed_detector,  # Use perturbed geometry (refinement starting point)
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        experiment=mapping_context.experiment,
        device=device_obj,
    )
    bragg_after = bragg_final  # Engine-refined final Bragg
```

**Rationale**:
- `refinement_inputs` = same inputs used for refinement (target, mask, etc.)
- `perturbed_detector/beam/crystal` = geometry state BEFORE refinement starts
- `mapping_context.experiment` = Experiment object (needed by simulate_forward_once)
- `device_obj` = torch.device from config (CPU or CUDA)
- Result = forward model from perturbed geometry, matching refinement starting point

---

### Step 3: Run Mapped Tests

```bash
mkdir -p plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small \
              2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/pytest_parity_batch2_corrected.log
```

**Expected outcome**: 2/2 tests PASSED

**Success criteria**:
- test_db_at_028: chi²/pixel initial ~10-50 (perturbed geometry is close to correct)
- test_db_at_029: median ROI correlation before ~0.2-0.4 (perturbed forward correlates with data)
- No import errors for simulate_forward_once
- Both tests validate chi² reduction and correlation improvement

**If tests still fail**:
- Check pytest log for NEW failure signature (different from previous chi²=2.1e5, correlation=-0.037)
- Verify bragg_before shape matches bragg_after shape
- Check if simulate_forward_once returns numpy array (not tensor)
- Capture full traceback in pytest log

---

### Step 4: Write Turn Summary

Write to `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/summary.md`:

```markdown
### Turn Summary
Corrected ARCH-REFACTOR-001 Phase D.3 Batch 2 bragg_before computation: replaced mapping_context.bragg_zero_iter (baseline geometry) with simulate_forward_once call using perturbed geometry (refinement starting point).
Previous fix kept wrong geometry state; tests now validate perturbed→refined improvement correctly with reasonable chi² (~10-50 initial) and correlation (~0.2-0.4 before).
Phase D.3 Batch 2 complete; both DB-AT tests pass.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/ (analysis.md, pytest_parity_batch2_corrected.log)
```

---

## How-To Map

1. **Check imports**: Verify `simulate_forward_once` is imported from `dbex.nanobrag_bridge`
2. **If missing**, add to existing import block (lines 10-12)
3. **Replace bragg_before** (lines 171-176): Use simulate_forward_once with perturbed geometry
4. **Run tests**: pytest command above (2 selectors)
5. **Write summary**: Create summary.md in debug2 artifacts dir

---

## Pitfalls To Avoid

1. **DO NOT** use `mapping_context.bragg_zero_iter` — it has BASELINE geometry, not PERTURBED
2. **DO NOT** change test assertions or tolerances — geometry fix will make tests pass
3. **DO NOT** modify refinement logic or Engine pattern — only bragg_before computation is wrong
4. **DO NOT** forget to use PERTURBED geometry in simulate_forward_once call
5. **DO NOT** reuse previous fix attempt — Ralph's commit fd64e9f3 kept wrong geometry
6. **DO** pass exact same parameters to simulate_forward_once as listed in Step 2
7. **DO** use perturbed_detector/beam/crystal from fixture (lines 126-128)
8. **DO** use device_obj from torch.device(config.device) for simulate_forward_once
9. **DO** verify bragg_before shape matches bragg_after shape
10. **DO** use Edit tool (not Write) — this is an existing file

**Key Insight**: The bug is NOT that an attribute doesn't exist. The bug is that `mapping_context.bragg_zero_iter` contains the forward model for the WRONG geometry state (baseline instead of perturbed).

---

## If Blocked

**Scenario 1: simulate_forward_once import fails**
- **Action**: Check dbex/nanobrag_bridge.py for function signature
- **If missing**: Mark blocked, record in Attempts History
- **Do NOT**: Attempt environment changes

**Scenario 2: simulate_forward_once signature mismatch**
- **Action**: Read dbex/nanobrag_bridge.py line ~1230 to check actual signature
- **Adjust call** as needed (may need different parameter names)
- **Do NOT**: Skip the fix or keep buggy code

**Scenario 3: Tests still fail with similar chi²/correlation**
- **Action**: Verify perturbed_detector/beam/crystal are correct objects (not None)
- **Check** if simulate_forward_once returns numpy array (not tensor)
- **Add debug prints** to verify bragg_before stats (mean, std, shape)
- **Do NOT**: Revert to mapping_context.bragg_zero_iter

**Scenario 4: Tests pass but with unexpected metrics**
- **Action**: Compare metrics against expected ranges (chi² initial ~10-50, correlation before ~0.2-0.4)
- **If out of range**: Investigate whether perturbed geometry perturbation is too large/small
- **Do NOT**: Weaken test assertions without confirming bragg_before is correct

---

## Findings Applied (Mandatory)

**Relevant findings from docs/findings.md**:

- **ARCH-REFACTOR-001 Phase D.2 CLI Blueprint** (2025-12-02T220000Z): Engine pattern is correct; bragg_final extraction is correct. Only bragg_before geometry state is wrong.
- **TOOLING-VIS-001**: emit_mapping_context_diagnostics already fixed by Ralph in previous commit (lines 302, ~380). Those fixes are correct; keep them.
- **CONFORMANCE-001**: Tests require KMP_DUPLICATE_LIB_OK=TRUE (handled by pytest fixtures).
- **RUNTIME-001**: Tests require NANOBRAGG_DISABLE_COMPILE=1 (handled by pytest fixtures).

**New finding** (documented in analysis.md):
- `mapping_context.bragg_zero_iter` contains forward model from BASELINE geometry (dbex/vis/mapping.py:193-206)
- Tests require bragg_before from PERTURBED geometry (refinement starting point) for meaningful "before vs after" comparison
- Geometry mismatch (baseline vs perturbed) causes chi² ~2e5 and negative correlation

---

## Pointers

- **Root cause analysis**: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/analysis.md` (ALREADY WRITTEN)
- **Plan**: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase D checklist)
- **Previous failed attempt**: commit fd64e9f3 (kept wrong geometry)
- **simulate_forward_once signature**: `dbex/nanobrag_bridge.py:~1230`
- **Fixture geometry flow**:
  - Lines 122-124: baseline_* extracted from dataload
  - Lines 126-128: perturbed_* created via create_perturbed_geometry
  - Lines 148-157: RefinementEngine uses perturbed geometry
  - Line 163: bragg_final from engine (refined perturbed geometry)
  - Line 175: bragg_before MUST use perturbed geometry (NOT baseline from mapping_context)
- **Test functions**:
  - `tests/dbex/test_stage_a_smoke_parity.py:296` (test_db_at_028_loss_scale_sanity)
  - `tests/dbex/test_stage_a_smoke_parity.py:376` (test_db_at_029_structure_parity)

---

## Next Up (optional)

**After 2/2 tests PASSED**:
1. **Mark Phase D.3 Batch 2 complete** in fix_plan.md Attempts History
2. **Proceed to D.3 Batch 3**: Migrate dbex/tools/stage_a_adam.py from facade to Engine
3. **Or proceed to D.5**: Facade deletion (if Batch 3 is deferred)

---

## Doc Sync Plan (Conditional)

Not applicable this loop (bugfix only, no new tests, no test renames).

---

## Mapped Tests Guardrail

Both mapped selectors collect and should pass after corrective fix:
- `test_db_at_028_loss_scale_sanity` — validates chi²/pixel initial < 100 and chi² reduction
- `test_db_at_029_structure_parity` — validates median ROI correlation before >= 0.2 and improvement after

No new tests created this loop.

---

## Hard Gate

N/A (no selector changes this loop; corrective bugfix restores correct test contract).

---

## Normative Math/Physics

N/A (no physics changes; corrective fix restores correct "before" state geometry per original test design).

---

## Debugging Notes

If you need to verify bragg_before is computed correctly, add temporary diagnostic prints after the simulate_forward_once call:

```python
print(f"DEBUG bragg_before (PERTURBED): shape={bragg_before.shape}, mean={bragg_before.mean():.6f}, std={bragg_before.std():.6f}, max={bragg_before.max():.6f}")
print(f"DEBUG bragg_after (REFINED): shape={bragg_after.shape}, mean={bragg_after.mean():.6f}, std={bragg_after.std():.6f}, max={bragg_after.max():.6f}")
```

Expected:
- Both should have same shape (e.g., [4, 2463, 2527])
- bragg_before should have reasonable mean/std (not all zeros, not extreme values)
- bragg_after should show DIFFERENT stats after refinement (improved fit)
- Mean values should be within same order of magnitude (~1e1 to ~1e4, depending on data scale)
