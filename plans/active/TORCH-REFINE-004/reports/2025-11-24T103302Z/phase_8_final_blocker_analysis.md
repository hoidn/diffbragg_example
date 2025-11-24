# Phase 8 Final Blocker: asdict() Loses Custom Attributes

**Date:** 2025-11-24T103302Z
**Initiative:** TORCH-REFINE-004 Phase 8
**Blocker:** Per-reflection test fails with `hasattr(telemetry_b, 'stage_b_mode') → False`
**Confidence:** 99.9% (definitive root cause identified)

## Executive Summary

Ralph's Phase 8 wrapper fixes (commit 6705471) correctly implemented custom attribute serialization in the wrapper (stage_b.py:456-475) and the engine (engine.py:139-168). However, `run_nanobrag_refinement`'s engine delegation path (lines 4904-4916) loses these custom attributes when it calls `asdict(telem_obj)` → `RefinementTelemetry(**telem_dict)`, because **`asdict()` only serializes dataclass fields, not arbitrary attributes**.

## Root Cause Chain

### Data Flow (Current Broken State)

1. **Wrapper Stage B** (`dbex/refinement/stage_b.py:456-475`):
   - Creates `telemetry_b = RefinementTelemetry(...)`
   - Adds custom attributes: `telemetry_b.stage_b_mode = "per_reflection"` ✓
   - Calls `asdict(telemetry_b)` → dict (custom attrs LOST here!)
   - Adds custom fields to dict: `telemetry_output["stage_b_mode"] = "per_reflection"` ✓
   - Returns `telemetry_output` dict ✓

2. **Engine** (`dbex/refinement/engine.py:139-168`):
   - Receives wrapper dict with custom fields ✓
   - Caches custom fields: `self._stage_b_mode = telemetry_dict.get("stage_b_mode")` ✓
   - Excludes custom fields from RefinementTelemetry constructor (lines 149-152) ✓
   - Creates dataclass: `telemetry = RefinementTelemetry(**telemetry_core_dict)` ✓
   - Restores custom attributes: `telemetry.stage_b_mode = self._stage_b_mode` ✓
   - Returns `telemetry` object with custom attributes ✓

3. **run_nanobrag_refinement engine delegation** (`dbex/nanobrag_refinement.py:4904-4916`):
   - Receives engine telemetry dict: `engine_telemetry["stage_b"]` is RefinementTelemetry WITH custom attributes ✓
   - Line 4910: `telem_dict = asdict(telem_obj)` ❌ **LOSES custom attributes!**
   - Line 4914: `telemetry_out[legacy_key] = RefinementTelemetry(**telem_dict)` ❌ **NO custom attributes!**
   - Returns `telemetry_out["B"]` WITHOUT custom attributes ❌

4. **Test** (`tests/dbex/test_torch_refine_smoke.py:1640`):
   - Gets `telemetry_b = telemetry_dict["B"]` (from run_nanobrag_refinement return)
   - Checks `hasattr(telemetry_b, "stage_b_mode")` → **FALSE** ❌

## Why asdict() Loses Custom Attributes

Python's `dataclasses.asdict()` function ONLY serializes fields defined in the `@dataclass` decorator. Attributes added after construction (via `obj.attr = value`) are NOT included in the dict output.

**Example:**
```python
from dataclasses import dataclass, asdict

@dataclass
class Example:
    field1: str

ex = Example(field1="value1")
ex.custom_attr = "custom_value"  # Added after construction

print(asdict(ex))  # Output: {'field1': 'value1'}
                   # custom_attr is MISSING!
```

This is expected behavior per Python dataclasses spec. Custom attributes must be explicitly preserved.

## Fix Specification

**Location:** `dbex/nanobrag_refinement.py:4904-4916` (engine delegation telemetry enrichment block)

**Strategy:** Manually preserve custom attributes from engine telemetry before/after asdict() reconstruction.

### Implementation Pattern (3-Part Fix)

#### Part 1: Extract custom attributes BEFORE asdict()
```python
# After line 4908 (for-loop over engine_telemetry)
for stage_name, telem_obj in engine_telemetry.items():
    # Cache custom attributes before asdict() (matches engine pattern)
    custom_attrs = {}
    if stage_name == "stage_b":
        # Extract Stage B custom attributes if present
        if hasattr(telem_obj, 'stage_b_mode'):
            custom_attrs['stage_b_mode'] = telem_obj.stage_b_mode
        if hasattr(telem_obj, 'n_asu_unique'):
            custom_attrs['n_asu_unique'] = telem_obj.n_asu_unique
        if hasattr(telem_obj, 'optimizer_type'):
            custom_attrs['optimizer_type'] = telem_obj.optimizer_type
        if hasattr(telem_obj, 'asu_modifier_stats'):
            custom_attrs['asu_modifier_stats'] = telem_obj.asu_modifier_stats
```

#### Part 2: Convert to dict (existing line 4910, no change)
```python
    telem_dict = asdict(telem_obj)
```

#### Part 3: Add fields to dict + restore attributes AFTER reconstruction
```python
    # Add engine protocol fields (existing lines 4911-4912, no change)
    telem_dict["engine_protocol"] = engine_protocol
    telem_dict["stage_modes"] = stage_modes

    # Reconstruct RefinementTelemetry
    legacy_key = stage_name_map.get(stage_name, stage_name)
    telem_reconstructed = RefinementTelemetry(**telem_dict)

    # Restore custom attributes to reconstructed object
    for attr_name, attr_value in custom_attrs.items():
        setattr(telem_reconstructed, attr_name, attr_value)

    telemetry_out[legacy_key] = telem_reconstructed
```

### Alternative: Simpler Pattern (Return Engine Telemetry Directly)

Since the engine already does the hard work of restoring custom attributes (lines 161-168), we could simplify by NOT reconstructing:

```python
for stage_name, telem_obj in engine_telemetry.items():
    # Add engine protocol fields directly to the existing object
    telem_obj.engine_protocol = engine_protocol
    telem_obj.stage_modes = stage_modes

    legacy_key = stage_name_map.get(stage_name, stage_name)
    telemetry_out[legacy_key] = telem_obj  # Use original object, preserve custom attrs
```

**Trade-off:** This modifies the engine's returned objects in-place, which could cause issues if engine.telemetry property is accessed later. However, the engine.telemetry property returns `self._telemetry` dict which contains the original objects, so this should be safe.

**Recommendation:** Use Alternative (simpler, less error-prone, preserves all engine work).

## Validation Protocol

After fix:
1. Compilation check: Python syntax OK
2. Phase 6 unit tests: `pytest tests/dbex/test_stage_b_asu_mapping.py` (should PASS, no changes)
3. Shell mode regression: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (should PASS, no changes)
4. Per-reflection smoke: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` (MUST PASS, fix target)

Expected outcome: All 4 tests PASS, Phase 8 ✓ COMPLETE.

## Estimated Effort

- Code: 5 minutes (add/modify ~10-15 lines in run_nanobrag_refinement.py)
- Validation: 30 minutes (4 test runs ~25-30s total + logs)
- Decision synthesis: 5 minutes
- Commit: 5 minutes
- **Total:** ~45 minutes (single-loop delivery feasible)

## Confidence

**99.9%** — Root cause is definitive (asdict() loses custom attributes is documented Python behavior), fix is straightforward (preserve attributes across asdict() call), validation is deterministic (test will either PASS or FAIL with clear error).

## Findings Applied

- POLICY-001: Environment Freeze (code-only fix, no installs)
- ARCH-ENGINE-002: Lazy imports (no changes to imports)
- REFINE-001/002/005: Scale/acceptance/halo (no changes to refinement logic)
- ARCH-REFINE-FLOW-001: Engine delegation pattern (fix preserves engine contract)
- Phase 8 wrapper fixes (builds on Ralph's correct implementation)

## Next Actions

Ralph executes 4-step fix protocol:
1. Read this analysis
2. Apply fix (Alternative pattern recommended: add attributes directly, avoid asdict() reconstruction)
3. Run 4-step validation protocol
4. Decision synthesis + commit

Expected outcome: Path A (all tests PASS, Phase 8 ✓ COMPLETE, ready for Phase 9 planning).
