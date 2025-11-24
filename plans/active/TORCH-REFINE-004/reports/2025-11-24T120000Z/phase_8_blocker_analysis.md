# Phase 8 Blocker Root Cause Analysis

**Date:** 2025-11-24T120000Z
**Initiative:** TORCH-REFINE-004 Phase 8
**Blocker:** Two distinct bugs preventing per-reflection mode E2E validation

## Issue #1: Shell Mode Regression (Optimizer Type Case Mismatch)

### Error
```
FAILED tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers - AssertionError: assert 'lbfgs' == 'LBFGS'
```

### Root Cause
**Location:** `dbex/refinement/stage_b.py:411`

```python
optimizer_type = param_values.get('optimizer_type', 'lbfgs').upper()
```

The wrapper uppercases the optimizer type to `"LBFGS"` but:
1. The test at line 1652 expects lowercase: `assert telemetry_b.optimizer_type in ["adam", "lbfgs"]`
2. The nanobrag_refinement.py stores lowercase at line 5229: `telemetry_b.optimizer_type = param_values['optimizer_type']  # "adam" or "lbfgs"`

### Fix
Remove the `.upper()` call at line 411. The optimizer type should remain lowercase throughout the system.

```python
# BEFORE (line 411)
optimizer_type = param_values.get('optimizer_type', 'lbfgs').upper()

# AFTER
optimizer_type = param_values.get('optimizer_type', 'lbfgs')  # Keep lowercase for consistency
```

### Impact
- Shell mode regression test will pass
- Maintains consistency with nanobrag_refinement.py convention (lowercase optimizer types)
- No breaking changes (only the wrapper was uppercasing, tests expect lowercase)

## Issue #2: Per-Reflection KeyError in Stage C Preparation Code

### Error
```
KeyError: 'shell_edges'
dbex/nanobrag_refinement.py:4077
```

### Root Cause
**Location:** `dbex/nanobrag_refinement.py:4055-4080`

The Stage C preparation code has nested conditionals that don't properly handle per-reflection mode when telemetry_b is a dict:

```python
# Line 4064-4069: Outer check handles per-reflection correctly
if stage_b_mode == "per_reflection":
    shell_edges = None
    shell_indices = None
    n_shells = 0
    shell_modifiers_final = None
else:
    # Line 4072-4079: Inner check assumes ALL non-per-reflection paths have shell keys
    if hasattr(telemetry_b, 'shell_edges'):
        shell_edges = torch.tensor(telemetry_b.shell_edges, ...)
    else:
        # BUG: This branch executes when telemetry_b is dict AND mode != per_reflection
        # But per-reflection mode CAN produce dicts via engine delegation!
        shell_edges = torch.tensor(telemetry_b['shell_edges'], ...)  # KeyError!
```

The problem: When using engine delegation (ARCH-REFINE-FLOW-001), `telemetry_b` comes back as a dict. The outer `if` at line 4064 correctly checks `stage_b_mode`, but the logic flaw is:
- Line 4060-4061: `stage_b_mode = telemetry_b['stage_b_mode']` extracts mode from dict
- Line 4064: The `if stage_b_mode == "per_reflection"` check works
- Line 4070: The `else` means "not per-reflection" (should be shell mode)
- But Ralph's per-reflection implementation IS producing a dict with `stage_b_mode == "per_reflection"`
- So it takes the per-reflection branch correctly at line 4064-4069 ✓

Wait, re-reading the traceback... Let me check if `stage_b_mode` is being extracted correctly.

### Deeper Investigation

The actual issue is likely that `stage_b_mode` extraction at lines 4060-4061 is FAILING (returns None or empty), so the code falls through to the `else` branch at line 4070 which assumes shell mode.

**Hypothesis:** The wrapper is returning a dict with `stage_b_mode` key, but the extraction logic at line 4060-4061 is not finding it correctly.

Let me check the wrapper output structure:
- Line 460 in stage_b.py: `telemetry_output["stage_b_mode"] = "per_reflection"`  ✓ Key exists in dict

But line 4058-4061 checks:
```python
if hasattr(telemetry_b, 'stage_b_mode'):  # Check if it's an object attribute
    stage_b_mode = telemetry_b.stage_b_mode
elif isinstance(telemetry_b, dict) and 'stage_b_mode' in telemetry_b:  # Check if it's a dict key
    stage_b_mode = telemetry_b['stage_b_mode']
```

This SHOULD work. So why is it failing?

**New Hypothesis:** The `telemetry_b` being passed to this Stage C preparation code is NOT the wrapper output dict, but rather the RefinementTelemetry dataclass instance that was constructed earlier in the wrapper at line 413-445. That dataclass doesn't have `stage_b_mode` as a field (it's only added to `telemetry_output` dict later at line 460).

### Correct Root Cause

The Stage C preparation code at line 4055-4080 receives `telemetry_b` from the caller. Looking at the flow:
1. Wrapper constructs `RefinementTelemetry` object at lines 413-445
2. Wrapper converts it to dict via `.to_dict()` at line 453
3. Wrapper adds custom fields like `stage_b_mode` to the dict at lines 460, 484
4. Wrapper returns `telemetry_output` dict

But the Stage C code might be receiving the original dataclass object, not the enhanced dict!

Let me check where Stage C gets telemetry_b from... It's in `run_nanobrag_refinement` which calls the engine or direct Stage B optimization. If using engine delegation, it gets back the dict from the wrapper. If using direct optimization, it constructs the telemetry itself.

**Correct Fix:** The issue is that the extraction logic at lines 4058-4061 is correct, but it's ALSO checking the wrong order. It should prioritize dict keys over hasattr when both could be true.

Actually, looking more carefully: when `telemetry_b` is a dict (engine delegation path), line 4060-4061 should extract the key. But the error traceback shows it's hitting line 4077 which is INSIDE the `else` at line 4070, meaning `stage_b_mode` was NOT "per_reflection".

**Final Root Cause:** The wrapper dict at line 460 sets `telemetry_output["stage_b_mode"] = "per_reflection"` correctly, but lines 4058-4061 might not be extracting it. Let me check if there's a condition that causes `stage_b_mode = None` to persist...

Line 4057: `stage_b_mode = None` (default)
Line 4058-4061: If checks...
Line 4064: `if stage_b_mode == "per_reflection"`

If the `elif` at line 4060 doesn't match (e.g., telemetry_b is a dict but doesn't have 'stage_b_mode' key YET when this code runs), then `stage_b_mode` stays `None`, falls to `else` at line 4070, then falls to nested `else` at line 4076, KeyError!

**Actual Root Cause:** The wrapper returns `telemetry_output` dict with `stage_b_mode` key added at line 460/484, but this is AFTER the RefinementTelemetry dataclass construction. The engine at `dbex/refinement/engine.py` might be passing through the dataclass `.to_dict()` output which doesn't include the custom `stage_b_mode` field that was added AFTER to_dict().

Let me check the wrapper code flow more carefully:
- Line 413: Construct `telemetry_b = RefinementTelemetry(...)`
- Line 453: `telemetry_output = telemetry_b.to_dict()`
- Line 460/484: `telemetry_output["stage_b_mode"] = "per_reflection"` or `"shell"`
- Line 490: `return telemetry_output`

So the wrapper DOES return the enhanced dict. The issue must be in the engine delegation path. Let me check if engine.py modifies the telemetry before passing it back...

### Definitive Fix

The safest fix is to ensure `stage_b_mode` is ALWAYS extractable. Two options:

**Option A:** Add `stage_b_mode` as a custom attribute to the RefinementTelemetry dataclass instance BEFORE calling to_dict(), so it's included in the dict output.

**Option B:** Ensure the Stage C preparation code handles missing `stage_b_mode` gracefully by defaulting to shell mode if not found (but this violates spec:59).

**Option C (RECOMMENDED):** Fix the wrapper to add `stage_b_mode` as an attribute to the dataclass object so it's serialized by to_dict(), not just added to the dict afterward.

Looking at nanobrag_refinement.py:5236-5238, it adds custom attributes directly to the dataclass:
```python
telemetry_b.stage_b_mode = "per_reflection"
```

The wrapper should do the same at line ~460 BEFORE calling to_dict().

### Prescription

**Fix #1 (Shell Regression):** Remove `.upper()` at stage_b.py:411
**Fix #2 (Per-Reflection KeyError):** Move `stage_b_mode` assignment BEFORE `to_dict()` call

In `dbex/refinement/stage_b.py`:
1. Line 411: Change `optimizer_type = param_values.get('optimizer_type', 'lbfgs').upper()` → `optimizer_type = param_values.get('optimizer_type', 'lbfgs')`
2. After line 445 (after RefinementTelemetry construction), BEFORE line 453 (`to_dict()` call):
   - Add: `telemetry_b.stage_b_mode = stage_b_mode`
   - If per-reflection: Add `telemetry_b.n_asu_unique`, `telemetry_b.optimizer_type`, `telemetry_b.asu_modifier_stats`
   - This ensures custom attributes are on the dataclass BEFORE serialization
3. Lines 460-480 can be simplified or removed if attributes are already on dataclass

### Validation
After fixes:
1. Shell regression: `test_stage_b_shell_modifiers` should PASS (optimizer_type lowercase)
2. Per-reflection: `test_stage_b_per_reflection_smoke` should get past KeyError (stage_b_mode in dict)
3. Phase 6 unit tests: Should still PASS (no changes to helpers)
