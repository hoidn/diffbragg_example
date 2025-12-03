# Input for Ralph — ARCH-ENGINE-ARTIFACTS-001 Phase B.2 (Parity Test Bugfix)

## Summary
Fix Stage B parity test baseline_crystal parameter mismatch causing 1e+12 rel error.

## Mode
TDD

## InitiativeType
architecture

## Focus
ARCH-ENGINE-ARTIFACTS-001 — RefinementEngine artifact channel & final-Bragg unification

## Branch
integration

## Mapped tests
```bash
pytest -vv tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode
```

## Artifacts
`plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/`

## Do Now

**Context:** Phase B.2 parity tests were created, but Stage B test FAILED with max_rel=1.474e+12 (line 37 of pytest_parity_stage_b.log). Root cause: test passes `baseline_crystal=None` to reconstruction helper (line 148) but passes `baseline_crystal=crystal` to context (line 104), causing parameter mismatch between artifact path and helper path.

**Your task:** Fix the baseline_crystal mismatch in the Stage B parity test.

### Step 1: Fix test_stage_b_artifact_matches_helper_shell_mode

Open `tests/dbex/test_artifact_parity.py` and locate line ~326 (or search for `baseline_crystal=None` in the `build_final_bragg_from_stage_b_telemetry` call inside `test_stage_b_artifact_matches_helper_shell_mode`).

**Current (incorrect):**
```python
helper_bragg = build_final_bragg_from_stage_b_telemetry(
    telemetry_a=telemetry_a,
    telemetry_b=reconstruction_payload,
    detector=detector,
    beam=beam,
    crystal=crystal,
    baseline_crystal=None,  # ← WRONG: should match context
    inputs=refinement_inputs,
    ...
)
```

**Fixed:**
```python
helper_bragg = build_final_bragg_from_stage_b_telemetry(
    telemetry_a=telemetry_a,
    telemetry_b=reconstruction_payload,
    detector=detector,
    beam=beam,
    crystal=crystal,
    baseline_crystal=crystal,  # Match context: Stage B requires baseline for cell delta reconstruction
    inputs=refinement_inputs,
    ...
)
```

Use the Edit tool with the exact old_string/new_string from the reconstruction helper call (lines ~320-336 in the test file).

### Step 2: Re-run Stage B parity test

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
pytest -vv tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode -s \
  > plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/pytest_stage_b_fixed.log 2>&1
```

Expected outcome: TEST PASSED with max_rel ≤ 1e-6 (should be ~0.000e+00 like Stage A test).

### Step 3: Update summary.md

Create `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/summary.md`:

If PASSED:
```markdown
### Turn Summary
Fixed Stage B parity test baseline_crystal mismatch (was None, should be crystal).
Test now PASSES: Stage B shell mode parity (max_rel=X.XXe-Y ≤ 1e-6).
Phase B.2 complete, artifact emission validated, ready for Phase C orchestrator cleanup.
Artifacts: plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/ (pytest_stage_b_fixed.log)
```

If still FAILED:
```markdown
### Turn Summary
Fixed baseline_crystal mismatch but test still FAILS: max_rel=X.XXe-Y.
Captured debug diagnostics; may indicate deeper artifact/helper divergence beyond baseline parameter.
Requires supervisor root-cause analysis.
Artifacts: plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/ (pytest_stage_b_fixed.log, debug output)
```

## How-To Map

### Finding the bug
The Stage B parity test calls the reconstruction helper with `baseline_crystal=None` (line ~326) but builds the context with `baseline_crystal=crystal` (line ~282). The artifact path (via StageB.run → artifact emission) uses `ctx.baseline_crystal` (which is `crystal`), while the test's direct helper call uses `None`, causing cell parameter reconstruction divergence.

### Why this matters
Stage B requires `baseline_crystal` to reconstruct cell parameters because Stage A telemetry stores cell deltas relative to the baseline (not absolute values). When `baseline_crystal=None`, the reconstruction helper cannot compute correct cell parameters, producing garbage outputs (~2× error in this case: artifact mean ~123, helper mean ~47).

### The fix
Pass the same `baseline_crystal` value to both:
1. Context builder (line ~282): `baseline_crystal=crystal` ✓ (already correct)
2. Helper call (line ~326): `baseline_crystal=crystal` (needs fix)

## Pitfalls To Avoid

1. **Don't change context builder**: Line ~282 is already correct (`baseline_crystal=crystal`)
2. **Only fix helper call**: Line ~326 is the bug (`baseline_crystal=None` → `baseline_crystal=crystal`)
3. **Match the artifact path**: Stage B's artifact emission (stage_b.py:1719) passes `baseline_crystal=baseline_crystal` from context, so test must do the same
4. **Check line numbers**: The test file may have shifted since the original input.md; search for `baseline_crystal=None` in the `build_final_bragg_from_stage_b_telemetry` call
5. **Verify one test**: Only run `test_stage_b_artifact_matches_helper_shell_mode`, not the full parity suite

## If Blocked

**If test still fails after fix:**
- Capture max_abs, max_rel, rms_rel from pytest output
- Print sample values at argmax divergence point
- Check if shapes/dtypes match (should be identical)
- Check if artifact_bragg and helper_bragg are both non-None
- Create `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/debug_parity_failure.md` with:
  - Max absolute and relative errors
  - Argmax location (np.unravel_index(abs_diff.argmax(), abs_diff.shape))
  - Sample pixel values from both arrays at divergence point
  - Device/dtype of both outputs

**If you can't find the line:**
- Search for `def test_stage_b_artifact_matches_helper_shell_mode` in tests/dbex/test_artifact_parity.py
- Find the `build_final_bragg_from_stage_b_telemetry` call inside that function
- The `baseline_crystal` parameter is in that call (should be ~10-15 lines after the call starts)

## Findings Applied (Mandatory)

- ARCH-ENGINE-ARTIFACTS-001 Phase B.2: Parity tests validate artifact emission matches reconstruction helpers
- ARCH-STAGE-CONTEXT-001 Phase D: Stage B conditionally populates bragg_full when terminal
- REFINE-FLOW-001: Stage B baseline parity gates require baseline_crystal for cell delta reconstruction
- Previous parity test logs showing Stage A PASSED (max_rel=0.000e+00) proves methodology correct

## Pointers

**Test file:**
- `tests/dbex/test_artifact_parity.py:320-336` (approximate, search for the helper call in test_stage_b_artifact_matches_helper_shell_mode)

**Artifact emission reference (correct pattern):**
- `dbex/refinement/stage_b.py:1713-1728` (Stage B artifact emission passes baseline_crystal from context)

**Reconstruction helper:**
- `dbex/refinement/reconstruction.py:269-284` (signature shows baseline_crystal is required parameter)

**Parity failure log:**
- `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/pytest_parity_stage_b.log:37` (max_rel=1.474e+12)
- Line 148 of that log shows `baseline_crystal=None` (the bug)

## Next Up (optional)

If you finish early and the test passes:
- Update the test docstring to clarify that baseline_crystal must match between context and helper call
- Add a comment at line ~326 explaining why baseline_crystal=crystal is required (cell delta reconstruction)

## Doc Sync Plan

Not needed for Phase B.2 (test bugfix only, no production code changes).
