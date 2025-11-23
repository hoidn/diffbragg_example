### Turn Summary
Analyzed Phase C2 blocker (loop i=205 test failures) and identified two critical bugs in engine delegation path: RefinementTelemetry dict conversion error (line 3089-3090) and missing StageB.name property check.
Root causes: (1) calling `.items()` on dataclass instances instead of converting via `asdict()` first, (2) engine input enrichment requires StageB.name=="stage_b" property to propagate stage_a_telemetry.
Next: Ralph fixes both bugs per revised Do Now (asdict() conversion + StageB.name property verification), reruns regression guard.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/ (blocker analysis, corrected input.md)

## Blocker Analysis (Loop i=205 → i=206 Transition)

### Ralph's Phase C2 Implementation (Loop i=205)
**Commit**: 5f36df3 "RALPH: ARCH-REFINE-FLOW-001 Phase C2 (BLOCKED) — Stage B engine delegation implementation"
**Artifacts**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/

**Attempted Changes:**
1. ✓ Extracted `_build_final_bragg_from_stage_b_telemetry` helper (~198 lines)
2. ✓ Added shell metadata to StageB telemetry output (shell_edges, shell_indices, n_shells)
3. ✓ Implemented Stage A→B engine delegation branch (lines 3021-3092)
4. ✓ Enhanced RefinementEngine for telemetry propagation
5. ✓ Fixed StageB tensor conversion for numpy inputs
6. ✓ Added stage_a_ctx to StageA telemetry output

**Test Results:**
- Compilation check: PASSED
- test_stage_b_shell_modifiers: FAILED (2 distinct errors)
- Status: BLOCKED

### Error Signatures

#### Error 1: KeyError: 'stage_a_telemetry'
**Location**: `dbex/refinement/stage_b.py:113`
**Traceback**:
```python
stage_a_telemetry = inputs['stage_a_telemetry']
KeyError: 'stage_a_telemetry'
```

**Context**: StageB.run() expects `inputs['stage_a_telemetry']` but RefinementEngine is not passing it.

**Root Cause Hypothesis**:
1. RefinementEngine.run() has input enrichment logic at lines 105-115
2. Line 107 condition: `stage.name == "stage_b" and "stage_a" in self._telemetry`
3. If StageB.name property is missing or returns wrong value, enrichment logic won't run
4. Result: inputs dict missing 'stage_a_telemetry' key when StageB.run() is called

**Verification Needed**:
- Check if `dbex/refinement/stage_b.py` has `@property def name(self)` returning `"stage_b"`
- Compare with StageA pattern at `dbex/refinement/stage_a.py:60-62`

#### Error 2: AttributeError: 'RefinementTelemetry' object is not subscriptable
**Location**: `dbex/nanobrag_refinement.py:3089-3090` (engine delegation return statement)
**Code**:
```python
telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_raw.items() if k not in [...]})
telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_raw.items() if k not in [...]})
```

**Context**:
- `telemetry_a_raw` and `telemetry_b_raw` are RefinementTelemetry dataclass instances (from engine.run() at line 3043-3047)
- Calling `.items()` on a dataclass raises AttributeError (dataclasses are not subscriptable)
- Need to convert to dict first using `dataclasses.asdict()` before filtering

**Root Cause**: Missing `asdict()` conversion before dict comprehension

### Corrective Actions (Loop i=206)

#### Fix 1: Add asdict() conversion (Bug 1)
**File**: `dbex/nanobrag_refinement.py`
**Lines**: 3088-3091
**Change**:
```python
# Before (BROKEN):
from dbex.nanobrag_refinement import RefinementTelemetry
telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_raw.items() if k not in [...]})
telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_raw.items() if k not in [...]})

# After (FIXED):
from dataclasses import asdict
from dbex.nanobrag_refinement import RefinementTelemetry

telemetry_a_dict = asdict(telemetry_a_raw)
telemetry_b_dict = asdict(telemetry_b_raw)

telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_dict.items() if k not in [...]})
telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_dict.items() if k not in [...]})
```

#### Fix 2: Verify/Add StageB.name property
**File**: `dbex/refinement/stage_b.py`
**Check**: Verify `@property def name(self)` exists and returns `"stage_b"`
**If missing**, add after `__init__` method:
```python
@property
def name(self) -> str:
    """Return stage identifier for telemetry keying."""
    return "stage_b"
```

### Expected Outcome (Loop i=206)

**If both fixes applied correctly:**
1. StageB.name property returns `"stage_b"` → engine input enrichment condition passes
2. Engine adds `stage_a_telemetry` to inputs dict → KeyError resolved
3. asdict() converts RefinementTelemetry to dict → AttributeError resolved
4. test_stage_b_shell_modifiers PASSES
5. Phase C2 marked COMPLETE

**Validation Commands:**
```bash
# Compilation check
python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')"

# Regression guard (MUST PASS)
KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -xvs

# Engine contract test
pytest tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage -xvs
```

### Escalation Criteria

**If loop i=206 still FAILS after both fixes:**
- Document debug output (stage.name value, self._telemetry keys, telemetry types)
- Create detailed blocker.md with error signatures + attempted fixes
- Mark ARCH-REFINE-FLOW-001 Phase C2 blocked in galph_memory.md
- Switch focus per dwell enforcement (2 consecutive non-implementation loops)

### Notes

- Ralph correctly identified shell metadata propagation issue in his summary.md
- The actual blocker is simpler: missing dataclass→dict conversion + possible missing name property
- Helper extraction work (198 lines) is solid; only the delegation return statement needs fixing
- No changes to `_build_final_bragg_from_stage_b_telemetry` helper required (it doesn't use target_t)
- AttributeError at line 2514 is likely a secondary failure after KeyError triggers fallback path

### References

- **Loop i=205 artifacts**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/
- **Ralph's blocker report**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/summary.md
- **Test log**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T073209Z/pytest_stage_b_shell_modifiers.log
- **Engine code**: dbex/refinement/engine.py:105-115 (input enrichment logic)
- **StageA pattern**: dbex/refinement/stage_a.py:60-62 (name property)
