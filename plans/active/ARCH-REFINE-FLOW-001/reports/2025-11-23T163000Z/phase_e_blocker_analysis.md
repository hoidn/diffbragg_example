# Phase E Blocker Analysis — RefinementTelemetry Schema Mismatch

**Loop:** i=232 (2025-11-23T163000Z)
**Status:** BLOCKED (TypeError in engine telemetry aggregation)
**Root Cause:** Schema inconsistency between dataclass definition and runtime usage

## Problem Summary

Ralph's Phase E implementation (commit c2ec597) added engine delegation telemetry fields (`engine_protocol` and `stage_modes`) to telemetry dicts returned by the engine, but **forgot to add these fields to the RefinementTelemetry dataclass definition**.

## Error Details

**Test:** `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
**Result:** FAILED
**Error:**
```
dbex/refinement/engine.py:139: TypeError: __init__() got an unexpected keyword argument 'engine_protocol'
```

**Call Stack:**
1. `RefinementEngine.run()` at dbex/refinement/engine.py:139
2. Attempting: `telemetry = RefinementTelemetry(**telemetry_core_dict)`
3. telemetry_core_dict contains `engine_protocol` and `stage_modes` keys
4. RefinementTelemetry dataclass does not define these fields
5. Python dataclass __init__ rejects unexpected keyword arguments

## Code Analysis

### What Ralph Added (commit c2ec597)

**In dbex/nanobrag_refinement.py (lines ~3820-3840):**
```python
# Build engine protocol string for telemetry
stage_names = [s.name for s in stages]
engine_protocol = "→".join(stage_names)  # e.g., "A→B→C", "A", "A→B"

# Build stage_modes dict for telemetry
stage_modes = {}
for stage in stages:
    if hasattr(stage, 'mode') and stage.mode:
        stage_modes[stage.name] = stage.mode

# Add to each stage's telemetry dict
for stage_name, telem_obj in engine_telemetry.items():
    telem_dict = asdict(telem_obj)
    telem_dict["engine_protocol"] = engine_protocol
    telem_dict["stage_modes"] = stage_modes  # Dict[str, str]
    engine_telemetry[stage_name] = RefinementTelemetry(**telem_dict)  # ← FAILS HERE
```

**In dbex/refinement/stage.py (lines 155-157, CURRENT STATE):**
```python
# ARCH-REFINE-FLOW-001 Phase A4: Stage identification fields
stage_type: Optional[str] = None  # e.g., "stage_a", "stage_b", "stage_c", "mock_stage"
mode: Optional[str] = None  # e.g., "shell_modifiers", "parity", "incremental_ub"
# ← MISSING: engine_protocol and stage_modes fields
```

## Root Cause

Ralph correctly identified that Phase E telemetry should include:
- `engine_protocol: str` — stage execution sequence (e.g., "A→B→C", "A-only")
- `stage_modes: Dict[str, str]` — mode per stage (e.g., {"B": "shell", "C": "detector_offsets"})

However, he added these fields to the telemetry dict in `run_nanobrag_refinement` but forgot to add them to the **RefinementTelemetry dataclass definition** in `dbex/refinement/stage.py`.

## Fix Strategy

**One-line fix per field (2 fields total):**

Add two fields to RefinementTelemetry dataclass after line 157:

```python
# ARCH-REFINE-FLOW-001 Phase E: Engine delegation telemetry
engine_protocol: Optional[str] = None  # e.g., "A→B→C", "A-only", "A→B"
stage_modes: Optional[Dict[str, str]] = None  # e.g., {"B": "shell", "C": "detector_offsets"}
```

Also update `to_dict()` method to serialize these fields (after line 225):

```python
# Phase E extensions
if self.engine_protocol is not None:
    result["engine_protocol"] = self.engine_protocol
if self.stage_modes is not None:
    result["stage_modes"] = self.stage_modes
```

## Validation Protocol

1. **Compilation check:** `python -c "from dbex.refinement.stage import RefinementTelemetry"`
2. **Regression guard:** `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (MUST PASS)
3. **Telemetry inspection:** Verify telemetry dict includes `engine_protocol` and `stage_modes` keys

## Expected Outcome

After fix:
- RefinementTelemetry accepts `engine_protocol` and `stage_modes` kwargs
- Engine aggregation successfully reconstructs RefinementTelemetry objects with new fields
- test_stage_a_expansion PASSES (Stage A via engine delegation)
- Phase E can proceed to full validation suite (Stage A/B/C + DB-AT-024)

## Confidence

**99%** — This is a straightforward schema mismatch. The fields are already being populated correctly in the engine logic; they just need to be declared in the dataclass.

## Artifacts

- Error log: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_a_engine.log
- Ralph's commit: c2ec597 (2025-11-23T160000Z)
- This analysis: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T163000Z/phase_e_blocker_analysis.md
