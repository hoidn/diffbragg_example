# Phase C2 Bugfix: Engine Delegation Path Errors (ARCH-REFINE-FLOW-001)

## Summary
Fix two critical bugs blocking Phase C2 engine delegation: (1) RefinementTelemetry dict conversion error at line 3089, (2) missing tensor initialization in `_build_final_bragg_from_stage_b_telemetry` helper.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2: Engine Delegation Bugfix)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (regression guard, small detector MUST PASS)
- `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (engine contract validation)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/`

## Do Now

**Objective:** Fix two critical bugs blocking Phase C2 engine delegation path (loop i=206 blocker resolution).

**Root Causes Identified:**
1. **Line 3089-3090** (`dbex/nanobrag_refinement.py`): Trying to call `.items()` on `RefinementTelemetry` dataclass instances (`telemetry_a_raw`, `telemetry_b_raw`) instead of converting them to dicts first.
2. **Line 2514** (`dbex/nanobrag_refinement.py`, inside `_build_final_bragg_from_stage_b_telemetry`): Trying to call `.to()` on `target_t` which is still a numpy array (never converted to tensor). Helper is missing the tensor initialization code present in inline path at line 3102.

**Implementation Steps:**

### Bug 1: Fix RefinementTelemetry dict conversion (line 3089-3090)

1. **Read current code** (dbex/nanobrag_refinement.py:3086-3092):
   ```python
   # Repackage telemetry with backward-compatible keys ("A", "B")
   # Filter out stage_type/mode fields to maintain RefinementTelemetry structure
   from dbex.nanobrag_refinement import RefinementTelemetry
   telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_raw.items() if k not in ['stage_type', 'mode', 'shell_edges', 'shell_indices', 'n_shells']})
   telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_raw.items() if k not in ['stage_type', 'mode', 'stage_a_ctx']})
   ```

2. **Replace with corrected code** (convert dataclass to dict first using `asdict()`):
   ```python
   # Repackage telemetry with backward-compatible keys ("A", "B")
   # Filter out stage_type/mode fields to maintain RefinementTelemetry structure
   from dataclasses import asdict
   from dbex.nanobrag_refinement import RefinementTelemetry

   # Convert RefinementTelemetry dataclass instances to dicts
   telemetry_a_dict = asdict(telemetry_a_raw) if hasattr(telemetry_a_raw, '__dataclass_fields__') else telemetry_a_raw
   telemetry_b_dict_filtered = asdict(telemetry_b_raw) if hasattr(telemetry_b_raw, '__dataclass_fields__') else telemetry_b_raw

   # Filter out extra fields not in RefinementTelemetry schema
   telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_dict_filtered.items() if k not in ['stage_type', 'mode', 'shell_edges', 'shell_indices', 'n_shells']})
   telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_dict.items() if k not in ['stage_type', 'mode', 'stage_a_ctx']})
   ```

### Bug 2: Add tensor initialization to `_build_final_bragg_from_stage_b_telemetry` helper

3. **Read current helper start** (dbex/nanobrag_refinement.py:2750-2792):
   - Lines 2750-2758: lazy imports
   - Lines 2760-2769: extract param_deltas from telemetry
   - Lines 2771-2792: extract Stage A frozen params + shell metadata
   - **MISSING**: tensor conversion for `inputs.target`, `inputs.loss_mask`, `inputs.sigma_readout`

4. **Insert tensor conversion code** (after line 2759, before param_deltas extraction):
   ```python
   # Convert numpy inputs to tensors (mirroring inline path line 3102-3104)
   # NOTE: These tensors are NOT used in final Bragg generation (cold/warm paths don't compute loss),
   # but they ARE used if Stage B inline code paths (compute_loss_stage_b) are invoked.
   # For Phase C2 engine delegation, we skip loss computation in the helper (only generate Bragg).
   # However, if future refactors move loss computation here, these will be needed.
   # For now, initialize them for consistency with inline path structure.
   target_t = torch.from_numpy(inputs.target).to(device=device, dtype=dtype)
   loss_mask_t = torch.from_numpy(inputs.loss_mask).to(device=device, dtype=torch.bool)
   sigma_readout_t = torch.from_numpy(inputs.sigma_readout).to(device=device, dtype=dtype)
   ```

   **WAIT!** Actually, re-reading the error at line 2514, the helper DOES NOT use these tensors anywhere in the cold/warm Bragg generation paths (lines 2875-2908). The error occurs in INLINE code at line 2514, which is INSIDE `_build_stage_b_lbfgs_closure` helper (the compute_loss_stage_b nested function), NOT inside `_build_final_bragg_from_stage_b_telemetry`.

   Let me re-check the error location...

5. **Re-analyze Bug 2**: The error at line 2514 is inside `_build_stage_b_lbfgs_closure` helper (compute_loss_stage_b nested function), not inside `_build_final_bragg_from_stage_b_telemetry`. This suggests the test is NOT hitting the engine delegation path at all, but instead hitting the INLINE path.

   **Hypothesis**: The test is configured to use the inline path (not engine delegation), so the engine delegation code at lines 3021-3092 is never executed. The KeyError at `inputs['stage_a_telemetry']` in StageB.run() confirms the engine IS being invoked, which contradicts the inline path hypothesis.

   **Re-check test configuration**: Let me verify which path the test takes...

6. **Root cause clarification needed**: Need to determine if:
   - Test is using engine delegation path (enable_stage_c=False AND enable_stage_b=True)?
   - OR test is using inline path (else branch at line 3094)?

7. **Check test configuration**:
   ```bash
   grep -A 20 "def test_stage_b_shell_modifiers" tests/dbex/test_torch_refine_smoke.py
   ```

8. **Depending on test configuration**:
   - **IF engine delegation**: Fix is in StageB.run() inputs propagation
   - **IF inline path**: Fix is in `_build_stage_b_lbfgs_closure` helper initialization

**REVISED APPROACH** (after error analysis):

The test failure shows TWO separate errors in the SAME test run:
1. **KeyError: 'stage_a_telemetry'** at `dbex/refinement/stage_b.py:113` — engine delegation path IS active
2. **AttributeError: 'numpy.ndarray' object has no attribute 'to'** at `dbex/nanobrag_refinement.py:2514` — inside `_build_stage_b_lbfgs_closure`

This means:
- Engine delegation path IS active (RefinementEngine([StageA(), StageB()]))
- StageB.run() IS being called, but fails at line 113 trying to extract `inputs['stage_a_telemetry']`
- The AttributeError at 2514 is a SEPARATE attempt after the KeyError (possibly a fallback or retry)

**Corrected Fix Plan:**

### Bug 1: RefinementEngine not passing stage_a_telemetry to StageB

The RefinementEngine code at line 111 tries to pass `stage_a_telemetry`, but the logic is ONLY triggered when `stage.name == "stage_b"`. Let me verify the stage name...

Actually, looking at line 107, the condition is correct. The issue is that `asdict(self._telemetry["stage_a"])` will fail because `self._telemetry["stage_a"]` is a RefinementTelemetry dataclass, but `asdict()` is not imported in the engine module!

**Fix**: Import `asdict` at the top of `dbex/refinement/engine.py` (it's already imported at line 109, so this is fine).

Actually, looking more carefully at line 109, `asdict` IS imported inside the if block. The real issue is that THIS CODE NEVER RUNS because the condition at line 107 checks `"stage_a" in self._telemetry`, but at the point when StageB.configure() is called (before run()), the telemetry dict is still empty!

**Root Cause**: The engine populates `self._telemetry["stage_a"]` AFTER StageA.run() completes (line 141), but the StageB input enrichment happens BEFORE StageB.run() is called (lines 105-115). So the condition `"stage_a" in self._telemetry` is TRUE when StageB runs (second iteration of the loop).

Wait, let me re-read the loop structure... The loop at line 100 iterates over `self.stages`, so for the [StageA(), StageB()] sequence:
- Iteration 0: stage = StageA(), stage_idx = 0
  - Line 105: `stage_idx > 0` is FALSE, skip enrichment
  - Line 118: StageA.run() executes
  - Line 141: `self._telemetry["stage_a"] = telemetry` (stored)
- Iteration 1: stage = StageB(), stage_idx = 1
  - Line 105: `stage_idx > 0` is TRUE
  - Line 107: `stage.name == "stage_b"` — what is the actual stage.name value?

Let me check the StageB class...

9. **Check StageB.name property**:
   ```bash
   grep -n "def name" dbex/refinement/stage_b.py
   grep -n "@property" dbex/refinement/stage_b.py | grep -A 2 "name"
   ```

10. **Implement Bug 1 Fix** (once stage.name is confirmed):
    - If `stage.name` returns `"stage_b"` correctly, the issue is that `asdict()` import or the dict conversion is failing
    - Otherwise, fix the stage.name property to return `"stage_b"` as expected

### Bug 2: Fix AttributeError in `_build_stage_b_lbfgs_closure`

The error at line 2514 suggests `target_t` is a numpy array. This is inside the `compute_loss_stage_b` nested function, which gets target_t from the closure's lexical scope. The variable `target_t` is supposed to be initialized in `_build_stage_b_params` at line 3102 (inline path), but StageB.run() does NOT call `_build_stage_b_params` directly to get these tensors — it expects them from `param_values` dict.

Looking at StageB.run() (dbex/refinement/stage_b.py), let me check how it calls the helpers...

**Simplified Fix Approach:**

Instead of trying to trace through all the complex data flows, let me:
1. Check if the test is ACTUALLY using engine delegation
2. If YES: Fix the engine→StageB input propagation
3. If NO: Fix the inline path initialization

Let me write a simpler, more direct Do Now that Ralph can execute:

## Simplified Do Now

**Step 1**: Verify which path the test uses
```bash
cd /home/ollie/Documents/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs 2>&1 | grep -E "stage_a_only_mode|stage_a_b_mode|=== INLINE PATH|=== ENGINE DELEGATION PATH" | head -5 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/path_detection.log
```

**Step 2**: Add debug logging to confirm which branch executes
```python
# Add at line 3015 (before stage detection logic)
print(f"DEBUG: enable_stage_c={config.enable_stage_c}, enable_stage_b={config.enable_stage_b}")
print(f"DEBUG: stage_a_only_mode = {not config.enable_stage_c and not config.enable_stage_b}")
print(f"DEBUG: stage_a_b_mode = {not config.enable_stage_c and config.enable_stage_b}")
```

**Step 3**: Fix Bug 1 (RefinementTelemetry dict conversion)
- Replace lines 3088-3091 with corrected code using `asdict()` (see above)

**Step 4**: Fix Bug 2 (check StageB.name property)
- Read `dbex/refinement/stage_b.py` to verify the `name` property returns `"stage_b"`
- If missing or incorrect, add/fix the property

**Step 5**: Regression guard (after fixes)
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/pytest_stage_b_after_bugfix.log
```

**Step 6**: Commit if tests pass
```bash
git add -A
git commit -m "$(cat <<'EOF'
RALPH: ARCH-REFINE-FLOW-001 Phase C2 bugfix — fix engine delegation telemetry conversion

Fixed two critical bugs in Phase C2 engine delegation path:
1. Line 3089-3090: Convert RefinementTelemetry dataclass to dict using asdict() before filtering
2. Verified StageB.name property returns "stage_b" for engine input enrichment

Tests:
- test_stage_b_shell_modifiers: [PASS/FAIL after bugfix]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push
```

## How-To Map

### Environment
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
cd /home/ollie/Documents/diffbragg_example
```

### Bug 1 Fix Location
**File**: `dbex/nanobrag_refinement.py`
**Lines**: 3088-3091
**Current code** (BROKEN):
```python
from dbex.nanobrag_refinement import RefinementTelemetry
telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_raw.items() if k not in ['stage_type', 'mode', 'shell_edges', 'shell_indices', 'n_shells']})
telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_raw.items() if k not in ['stage_type', 'mode', 'stage_a_ctx']})
```

**Replacement** (FIXED):
```python
from dataclasses import asdict
from dbex.nanobrag_refinement import RefinementTelemetry

# Convert RefinementTelemetry dataclass instances to dicts before filtering
telemetry_a_dict = asdict(telemetry_a_raw)
telemetry_b_dict = asdict(telemetry_b_raw)

# Filter out extra fields not in RefinementTelemetry schema
telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_dict.items() if k not in ['stage_type', 'mode', 'shell_edges', 'shell_indices', 'n_shells']})
telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_dict.items() if k not in ['stage_type', 'mode', 'stage_a_ctx']})
```

### Bug 2 Check Location
**File**: `dbex/refinement/stage_b.py`
**Check**: Verify `@property def name(self)` returns `"stage_b"` (should be around line 60-70 based on StageA pattern)

**If missing**, add after the `__init__` method:
```python
@property
def name(self) -> str:
    """Return stage identifier for telemetry keying."""
    return "stage_b"
```

### Validation
```bash
# Compilation check
python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/compilation_check.log

# Regression guard (MUST PASS)
KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/pytest_stage_b_after_bugfix.log

# Engine contract test
pytest tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage -xvs 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/pytest_engine_contract.log
```

## Pitfalls To Avoid

1. **asdict() import**: Must be imported from `dataclasses` module, NOT from `dbex.nanobrag_refinement`
2. **Dataclass detection**: Use `hasattr(obj, '__dataclass_fields__')` to check if object is a dataclass instance before calling `asdict()`
3. **StageB.name property**: Must return exactly `"stage_b"` (lowercase, underscore separator) to match engine telemetry keying
4. **Don't add tensor init to _build_final_bragg_from_stage_b_telemetry**: The helper does NOT use target_t/loss_mask_t/sigma_readout_t in its Bragg generation paths (only in loss computation, which is NOT called by the helper)
5. **Regression guard requirement**: test_stage_b_shell_modifiers MUST PASS before marking Phase C2 complete

## If Blocked

**Scenario 1: Bug 1 fix still fails with dict conversion error**
- Check if `telemetry_a_raw` and `telemetry_b_raw` are actually RefinementTelemetry instances (add `print(type(telemetry_a_raw))` before asdict() call)
- If they are already dicts, skip asdict() call
- Log type info + error signature in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/blocker.md`

**Scenario 2: StageB.name property missing or returns wrong value**
- Check if StageB inherits from a base class that defines `name` property
- If using RefinementStage protocol, verify the `name` property is correctly implemented
- Add property if missing, fix return value if incorrect
- Log class structure + error signature in blocker.md

**Scenario 3: Test still fails with KeyError: 'stage_a_telemetry'**
- The engine's input enrichment logic at line 107 is not running
- Debug by adding `print(f"DEBUG: stage_idx={stage_idx}, stage.name={stage.name}, telemetry_keys={list(self._telemetry.keys())}")` before line 107
- Verify `stage.name == "stage_b"` condition is TRUE
- Verify `"stage_a" in self._telemetry` condition is TRUE
- Log debug output in blocker.md

**Fallback**: If blocked after 2 attempts, write comprehensive blocker.md with error signatures, debug output, and proposed escalation path. Mark ARCH-REFINE-FLOW-001 Phase C2 blocked in galph_memory.md and docs/fix_plan.md Attempts History.

## Findings Applied (Mandatory)

**Relevant Finding IDs from docs/findings.md:**
- **POLICY-001** (Environment Freeze): No package installs/upgrades. Adherence: Bugfix uses only existing dependencies (dataclasses module is stdlib).
- **CONFIG-001** (Detector metadata contracts): Engine inputs dict propagation. Adherence: No changes to detector/beam/crystal configs.

No other findings directly relevant to Phase C2 bugfix.

## Pointers

### Spec/Arch/Testing Docs
- **Spec DB Workflow §7** (Refinement Protocol Architecture): `docs/spec-db-workflow.md:31-34`
- **ARCH-REFINE-FLOW-001 Plan**: `plans/active/ARCH-REFINE-FLOW-001/implementation.md` (Phase C checklist)
- **Testing Guide §2**: `docs/TESTING_GUIDE.md` (selector registry)

### Fix Plan Entries
- **ARCH-REFINE-FLOW-001**: `docs/fix_plan.md` (current status, dependencies)
- **Phase C2 Original Do Now**: `input.md` (from loop i=205, 2025-11-23T073209Z)
- **Ralph's Blocker Report**: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/summary.md`

### Code Anchors
- **Bug 1 location**: `dbex/nanobrag_refinement.py:3088-3091`
- **Bug 2 check location**: `dbex/refinement/stage_b.py` (name property)
- **Engine input enrichment**: `dbex/refinement/engine.py:105-115`
- **StageA name property example**: `dbex/refinement/stage_a.py:60-62` (for reference)

## Next Up (optional)

If bugfix completes early and all tests pass:
- Mark Phase C2 complete in implementation.md
- Proceed to Phase C3 planning (full Stage B smoke validation both detectors)

Do NOT proceed to Phase C3 without explicit Galph approval. Mark Phase C2 complete and commit artifacts.

## Doc Sync Plan (Conditional)

NOT REQUIRED for Phase C2 bugfix (no new tests authored, only fixing existing engine delegation path).

## Mapped Tests Guardrail

Both mapped selectors collect >0 tests (verified via `pytest --collect-only`):
- `test_stage_b_shell_modifiers`: 1 test (Active)
- `test_engine_executes_mock_stage`: 1 test (Active)

No downgrade required. Both selectors MUST PASS for Phase C2 completion.
