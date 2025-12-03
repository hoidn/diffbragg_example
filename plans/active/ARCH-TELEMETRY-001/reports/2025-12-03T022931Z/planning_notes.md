# Phase C.4 Planning Notes — RefinementEngine Legacy Key Mapping Removal

**Date**: 2025-12-03T022931Z
**Focus**: ARCH-TELEMETRY-001 Phase C.4
**Galph Loop**: Planning → ready_for_implementation

---

## Context

Phase C.3.1 complete (2025-12-04T050000Z): Writer now consumes typed `StageResult` dataclasses via `stage_results` kwarg.

Phase C.3.2 complete (2025-12-03T021140Z): Removed `to_legacy_dict()` calls from Stage B/C production code; stages access telemetry/perf fields directly.

**Current blocker**: `RefinementEngine.run()` still maps internal `self._telemetry` keys ("stage_a", "stage_b", "stage_c") to legacy labels ("A", "B", "C") at lines 203-215 before returning. This was added during ARCH-REFACTOR-001 Phase D.3 for backward compatibility with test assertions.

**Phase C.4 goal**: Remove the legacy key mapping from `engine.py`, update test assertions to use internal stage names, and verify all mapped selectors pass.

---

## Scope

### Code Changes

1. **dbex/refinement/engine.py** (`RefinementEngine.run()`, lines 203-215)
   - **DELETE**: Legacy key mapping loop that converts "stage_a" → "A", "stage_b" → "B", "stage_c" → "C"
   - **KEEP**: Engine protocol and stage_modes population (lines 195-199)
   - **CHANGE**: Return `self._telemetry` directly instead of `legacy_telemetry_dict`

2. **Test Files** (update assertions to use internal stage names)

   **tests/dbex/test_torch_refine_smoke.py**:
   - All test functions that assert on `telemetry_dict["A"]`, `telemetry_dict["B"]`, `telemetry_dict["C"]`
   - Update to `telemetry_dict["stage_a"]`, `telemetry_dict["stage_b"]`, `telemetry_dict["stage_c"]`
   - Functions: `test_stage_a_expansion`, `test_stage_a_engine_delegation_telemetry`, `test_stage_b_shell_modifiers`, `test_stage_c_detector_microslip`, `test_stage_b_per_reflection_smoke`

   **tests/dbex/test_stage_a_smoke_parity.py**:
   - Fixture `mapping_context_fixture` likely extracts telemetry with legacy keys
   - Update any assertions/extractions to use internal stage names

### Validation Plan

**Mapped Tests** (all from ARCH-TELEMETRY-001 Phase C):
1. `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload` (Stage B guard)
2. `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (Stage B shell smoke)
3. `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (Stage C detector smoke)
4. `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Stage A smoke)
5. `tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry` (Stage A engine)

**Expected Result**: All 5 tests PASS with no behavioral changes after key name updates.

---

## Implementation Strategy

### Step 1: Engine Key Mapping Removal
**File**: `dbex/refinement/engine.py`

**Current code** (lines 201-215):
```python
# ARCH-REFACTOR-001 Phase D.3: Map stage names to legacy labels for backward compatibility
# Tests and downstream code expect "A"/"B"/"C" keys (not "stage_a"/"stage_b"/"stage_c")
legacy_telemetry_dict = {}
for stage_name, telem in self._telemetry.items():
    if stage_name == "stage_a":
        legacy_telemetry_dict["A"] = telem
    elif stage_name == "stage_b":
        legacy_telemetry_dict["B"] = telem
    elif stage_name == "stage_c":
        legacy_telemetry_dict["C"] = telem
    else:
        # Unknown stage name - pass through unchanged
        legacy_telemetry_dict[stage_name] = telem

return legacy_telemetry_dict
```

**New code**:
```python
# ARCH-TELEMETRY-001 Phase C.4: Return internal telemetry dict directly
# Tests updated to use internal stage names ("stage_a", "stage_b", "stage_c")
return self._telemetry
```

**Line change**: Delete lines 201-213, replace line 215 with `return self._telemetry`

---

### Step 2: Test Assertion Updates

#### tests/dbex/test_torch_refine_smoke.py

**Pattern**: Replace all `telemetry_dict["A"]`, `["B"]`, `["C"]` with `["stage_a"]`, `["stage_b"]`, `["stage_c"]`

**Use `replace_all=True` for batch updates**:
- `telemetry_dict["A"]` → `telemetry_dict["stage_a"]`
- `telemetry_dict["B"]` → `telemetry_dict["stage_b"]`
- `telemetry_dict["C"]` → `telemetry_dict["stage_c"]`
- `"A" in telemetry_dict` → `"stage_a" in telemetry_dict`
- `"B" in telemetry_dict` → `"stage_b" in telemetry_dict`
- `"C" in telemetry_dict` → `"stage_c" in telemetry_dict`

**Affected functions** (from grep):
- `test_stage_a_expansion` (~line 1000)
- `test_stage_a_engine_delegation_telemetry` (~line 1100)
- `test_stage_b_shell_modifiers` (~line 1200)
- `test_stage_c_detector_microslip` (~line 1300)
- `test_stage_b_per_reflection_smoke` (~line 1400)

#### tests/dbex/test_stage_a_smoke_parity.py

**Fixture**: `mapping_context_fixture` (likely around line 150-200)
- Update telemetry extraction if it uses legacy keys
- Check if `emit_mapping_context_diagnostics` helper uses legacy keys

---

## Risks & Mitigations

**Risk**: Missed assertion updates in test files
**Mitigation**: Use `replace_all=True` for systematic batch replacement; run full test suite to catch edge cases

**Risk**: External tools/scripts expect legacy keys
**Mitigation**: Scope limited to tests; CLI/writer already consume `StageResult` dataclasses (Phase C.3.1)

**Risk**: Performance counters wrapped in lists still referenced via legacy keys
**Mitigation**: Phase C.3.2 already removed `to_legacy_dict()` calls; perf counters accessed via typed fields

---

## Artifacts

**Directory**: `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T022931Z/`

**Expected**:
- `pytest_phase_c4.log` — All 5 mapped tests execution logs
- `summary.md` — Turn summary (this loop)
- `input.md` — Do Now for Ralph (generated by Galph)

---

## Next Actions

1. Ralph implements Step 1 (engine.py deletion)
2. Ralph implements Step 2 (test assertion updates with replace_all)
3. Ralph runs all 5 mapped selectors with canonical env flags
4. Ralph captures pytest logs under artifacts directory
5. Galph reviews results and marks Phase C.4 complete if all tests PASS

---

**Status**: Planning complete, ready for implementation
**Next state**: ready_for_implementation
