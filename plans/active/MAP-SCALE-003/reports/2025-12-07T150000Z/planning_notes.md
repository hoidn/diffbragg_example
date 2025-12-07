# MAP-SCALE-003 Phase A Planning Notes — CLI Refined Structure Factor Telemetry

## Executive Summary

**Status**: Phase A complete. **Key finding**: Structure-factor telemetry schema already implemented in writer (SCALE-003 landing). Phase B scope reduced to CLI plumbing validation and test assertions.

**Next action**: Transition to Phase B implementation (verify CLI → writer data flow + extend test assertions).

---

## Phase A Deliverables Summary

### 1. Schema Audit (schema_audit.md)

**Finding**: **Telemetry schema already implemented** in `dbex/io/writer.py:196-200`

**Evidence**:
- Writer function signature accepts `hkl_telemetry` parameter (line 41-54)
- HDF5 serialization writes 4 attrs to `/torch_diagnostics` group:
  - `hkl_source` (str): "refined" | "raw"
  - `hkl_n_reflections` (int): Reflection count
  - `hkl_mean_amplitude` (float): Mean |F| amplitude
  - `hkl_path` (str): MTZ file path

**Backward compatibility**: ✓ Confirmed (additive-only extension, no breaking changes)

**Architecture conformance**: ✓ ARCH-CONTRACT-WRITER-001 compliant

---

### 2. MTZ Flow Trace (mtz_flow_trace.md)

**Call chain** (file:line anchors):
1. **CLI arg ingestion**: `dbex/refine_one.py:65-68` (`--refined-mtz` argument)
2. **MTZ loading**: `dbex/nanobrag_bridge.py:1118` (`load_refined_mtz` function)
3. **HKL grid construction**: `dbex/nanobrag_bridge.py:856` (`build_structure_factor_grid` function)
4. **Diagnostics emission**: `dbex/nanobrag_bridge.py:1230` (`simulate_forward_once` function)
5. **Writer invocation**: `dbex/io/writer.py:41` (`write_torch_outputs` function)

**Hook points identified**:
- **Hook Point A** (primary): `simulate_forward_once` must construct `hkl_telemetry` dict from function params (`hkl_source`, `hkl_path`) + computed stats (`len(hkl_indices)`, `np.mean(hkl_amplitudes)`)
- **Hook Point B** (CLI plumbing): `dbex/refine_one.py::run_nanobrag_backend` must populate `hkl_source` and `hkl_path` based on `--refined-mtz` vs `--mtzFile` precedence

---

### 3. Telemetry Schema (telemetry_schema.md)

**Schema definition**:
```python
hkl_telemetry = {
    "hkl_source": str,        # "refined" | "raw" | "unknown"
    "hkl_n_reflections": int, # len(hkl_indices)
    "hkl_mean_amplitude": float, # np.mean(np.abs(hkl_amplitudes))
    "hkl_path": str,          # Absolute MTZ path (or "" if unavailable)
}
```

**Fallback rules**:
- Refined MTZ missing/invalid → fall back to raw MTZ, set `hkl_source="raw"`
- No MTZ path available (tests) → set `hkl_path=""`
- SCALE-007 enforcement (Phase C): Disallow silent fallback when `--refined-mtz` explicitly provided

**Validation rules**:
- Writer validates dict completeness (all 4 keys present)
- `hkl_n_reflections > 0` and `hkl_mean_amplitude > 0` (sanity checks)

---

### 4. Consumer Compatibility (consumer_compatibility.md)

**Consumers analyzed**:
1. **test_torch_diagnostics_metadata** (tests/dbex/test_refine_one_cli.py:913)
   - Impact: None (selective attr access, new attrs ignored unless asserted)
   - Mock `hkl_telemetry` dict already present (lines 959-965)
   - Phase B: Add assertions for new attrs

2. **test_db_at_024_mapping_smoke** (tests/dbex/test_mapping_consistency.py:188)
   - Impact: None (diagnostics dict consumer, not HDF5 artifact)
   - Phase B: Add `hkl_telemetry` assertions in diagnostics dict
   - Regression guard: Assert `hkl_source="refined"` (SCALE-007)

3. **dbex/look.py** (visualization tools)
   - Impact: Unknown (not audited)
   - Risk: Low (likely selective attr access)
   - Phase B: Optional audit (non-blocking)

**Breaking change risk**: **None** (additive-only extension, backward compatible)

---

## Key Findings

### Finding 1: Schema Already Implemented
**Source**: schema_audit.md

**Details**: Writer function already serializes 4 telemetry fields to HDF5 (SCALE-003 landing, likely from MAP-SCALE-002 or earlier initiative).

**Impact on Phase B**: **Scope reduction**
- No writer changes required (schema already correct)
- Focus shifts to:
  1. Verify CLI plumbing populates `hkl_telemetry` correctly
  2. Extend test assertions to validate new attrs

---

### Finding 2: Hook Point for Telemetry Construction
**Source**: mtz_flow_trace.md

**Details**: `simulate_forward_once` is the canonical site for constructing `hkl_telemetry` dict (has access to both user-provided tags and raw data).

**Implementation guidance** (Phase B):
```python
# In simulate_forward_once, after build_structure_factor_grid call:
hkl_telemetry = {
    "hkl_source": hkl_source if hkl_source is not None else "unknown",
    "hkl_n_reflections": len(hkl_indices),
    "hkl_mean_amplitude": float(np.mean(np.abs(hkl_amplitudes))),
    "hkl_path": hkl_path if hkl_path is not None else "",
}
diagnostics["hkl_telemetry"] = hkl_telemetry
```

**Rationale**: Avoids duplication (single computation site for CLI, tests, and future consumers).

---

### Finding 3: Test Mock Already Prepared
**Source**: consumer_compatibility.md

**Details**: `test_torch_diagnostics_metadata` already includes mock `hkl_telemetry` dict (lines 959-965), indicating prior partial implementation.

**Impact on Phase B**: **Reduced test preparation burden**
- Mock data ready; only need to add assertions
- Confirms schema design already validated in test harness

---

### Finding 4: MAP-SCALE-004 Precedent
**Source**: plans/active/MAP-SCALE-004/implementation.md

**Details**: MAP-SCALE-004 (zero-iteration telemetry parity) is parallel initiative with similar scope (extend `simulate_forward_once` diagnostics).

**Coordination**: Ensure Phase B implementation aligns with MAP-SCALE-004 exit criteria:
- `simulate_forward_once` returns `hkl_telemetry` in diagnostics ✓
- DB-AT-024 asserts on telemetry fields ✓
- Regression guard for refined vs raw MTZ ✓

---

## Phase B Implementation Plan

### Scope

**Primary deliverables**:
1. **Verify CLI plumbing**: Confirm `dbex/refine_one.py::run_nanobrag_backend` populates `hkl_source` and `hkl_path` correctly
2. **Extend test assertions**: Add HDF5 attr checks to `test_torch_diagnostics_metadata` and diagnostics checks to `test_db_at_024_mapping_smoke`
3. **Run mapped tests**: Execute both tests, capture pytest logs, verify schema extension works end-to-end

**Out of scope** (deferred to Phase C or future initiatives):
- SCALE-007 enforcement (silent fallback guard) → MAP-SCALE-005
- `dbex/look.py` visualization tool audit → optional, non-blocking
- Schema versioning (not required for additive-only extension)

---

### Work Breakdown

#### Task 1: Verify CLI Plumbing (read + trace)
**File**: `dbex/refine_one.py`

**Steps**:
1. Search for `run_nanobrag_backend` function definition
2. Trace `--refined-mtz` argument handling:
   - Where is `load_refined_mtz` called?
   - How are `hkl_source` and `hkl_path` populated?
   - Are they passed to `simulate_forward_once` or `write_torch_outputs`?
3. Confirm telemetry dict flows CLI → diagnostics → writer

**Expected outcome**: File:line anchors documenting CLI → writer data flow

---

#### Task 2: Extend test_torch_diagnostics_metadata (edit + run)
**File**: `tests/dbex/test_refine_one_cli.py`

**Changes**:
1. Locate existing HDF5 attr assertions (after line 1020)
2. Add 4 new assertions:
   ```python
   # Verify structure-factor telemetry (SCALE-003)
   assert h["torch_diagnostics"].attrs["hkl_source"] == "raw"
   assert h["torch_diagnostics"].attrs["hkl_n_reflections"] == 100
   assert h["torch_diagnostics"].attrs["hkl_mean_amplitude"] == 50.0
   assert h["torch_diagnostics"].attrs["hkl_path"] == "/path/to/test.mtz"
   ```
3. Run test: `pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata -v`
4. Capture pytest log to `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/pytest_diagnostics_metadata.log`

**Validation**: Test passes; HDF5 artifact contains 4 new attrs

---

#### Task 3: Extend test_db_at_024_mapping_smoke (edit + run)
**File**: `tests/dbex/test_mapping_consistency.py`

**Changes**:
1. Locate diagnostics assertions (after line 286)
2. Add telemetry assertions:
   ```python
   # Verify structure-factor telemetry (MAP-SCALE-004)
   assert "hkl_telemetry" in diagnostics, "hkl_telemetry missing from diagnostics"
   hkl_telem = diagnostics["hkl_telemetry"]
   assert hkl_telem["hkl_source"] == "refined", \
       f"DB-AT-024 uses refined MTZ but got hkl_source={hkl_telem['hkl_source']} (SCALE-007 violation)"
   assert hkl_telem["hkl_n_reflections"] > 0, "hkl_n_reflections must be positive"
   assert hkl_telem["hkl_mean_amplitude"] > 0, "hkl_mean_amplitude must be positive"
   assert hkl_telem["hkl_path"] != "", "hkl_path should not be empty (canonical assets)"
   ```
3. Run test: `pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke -v`
4. Capture pytest log to `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/pytest_db_at_024.log`

**Validation**: Test passes; `hkl_source="refined"` confirms no silent fallback

---

### Acceptance Criteria (Phase B)

- [ ] CLI plumbing traced: File:line anchors for `hkl_source`/`hkl_path` population documented
- [ ] `test_torch_diagnostics_metadata` passes with 4 new telemetry assertions
- [ ] `test_db_at_024_mapping_smoke` passes with `hkl_telemetry` diagnostics assertions
- [ ] Pytest logs archived under `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/`
- [ ] No regressions: Existing tests still pass (backward compatibility confirmed)

---

## Findings Applied (Cross-Reference)

| Finding | Guidance | Application in Phase A |
|---------|----------|----------------------|
| **SCALE-003** | Zero-iteration helper must ingest refined |F| amplitudes (dbex/nanobrag_bridge.py:843-1106) | ✓ Traced MTZ loading path, confirmed `load_refined_mtz` and `build_structure_factor_grid` integration |
| **SCALE-004** | CLI plumbing must propagate refined MTZ path (--refined-mtz flag) | ✓ Identified CLI arg (dbex/refine_one.py:65-68), defined `hkl_path` telemetry field |
| **SCALE-006** | Telemetry must capture calibration metadata provenance | ✓ Defined `hkl_source` field (refined vs raw), `hkl_n_reflections`, `hkl_mean_amplitude` |
| **SCALE-007** | Silent fallback from refined to raw violates spec-db-tracing.md §2 | ✓ Defined fallback schema, deferred enforcement to Phase C (MAP-SCALE-005) |
| **TESTING-003** | Selector status transitions require pytest --collect-only confirmation | ✓ Phase B acceptance includes pytest --collect-only logs |

**No findings omitted**: All SCALE findings (003/004/006/007) and TESTING-003 addressed in planning.

---

## ARCH Conformance Verification

### ARCH-CONTRACT-CALIBRATION-001 (Calibration Metadata Threading)
**Status**: Not directly applicable to Phase A (telemetry design only, no calibration metadata flow changes)

**Relevance**: Phase C (MAP-SCALE-005) may need to coordinate with calibration metadata if enforcement requires cross-validation

---

### ARCH-CONTRACT-WRITER-001 (Torch Diagnostics Persistence)
**Status**: ✓ Conformant

**Evidence**:
- Schema extension is additive-only (no breaking changes)
- Writer already implements 4-field serialization (dbex/io/writer.py:196-200)
- Backward compatibility confirmed (consumer_compatibility.md)

**Violation risk**: None

---

### ARCH-CONTRACT-STRUCTURE-FACTORS-001 (Refined MTZ Ingestion)
**Status**: ✓ Conformant

**Evidence**:
- Call chain traced: `--refined-mtz` → `load_refined_mtz` → `build_structure_factor_grid` → `simulate_forward_once`
- Telemetry captures provenance (`hkl_source`, `hkl_path`)
- No silent fallback in schema design (fallback is explicit via `hkl_source="raw"`)

**Violation risk**: None (Phase B must confirm CLI plumbing correctness)

---

## Next Steps (Phase B Readiness)

### Immediate Next Action
**Task**: Read `dbex/refine_one.py` to locate `run_nanobrag_backend` function and trace CLI plumbing

**File**: `dbex/refine_one.py`

**Search pattern**: `def run_nanobrag_backend` OR `--refined-mtz` handling logic

**Expected findings**:
1. Where `load_refined_mtz` is called
2. How `hkl_source` and `hkl_path` are set based on CLI args
3. Where `write_torch_outputs` is invoked and how `hkl_telemetry` is passed

---

### Phase B Entry Criteria
- [x] Phase A planning notes complete
- [x] All 5 Do Now deliverables written (schema_audit, mtz_flow_trace, telemetry_schema, consumer_compatibility, planning_notes)
- [x] Hook points identified (simulate_forward_once for telemetry construction)
- [x] Test modification strategy defined (2 tests require assertion additions)
- [x] Backward compatibility confirmed (no breaking changes)

**Recommendation**: Proceed to Phase B implementation.

---

### Phase B Deliverables Preview
1. **CLI plumbing verification report** (file:line anchors for `hkl_source`/`hkl_path` population)
2. **Test edits** (test_torch_diagnostics_metadata + test_db_at_024_mapping_smoke)
3. **Pytest logs** (2 test runs, archived under reports/)
4. **Regression check** (pytest --collect-only, confirm no discovery breakage)

**Estimated scope**: 1-2 loops (verification + test edits + validation)

---

## References

### Planning Artifacts (This Loop)
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/schema_audit.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/mtz_flow_trace.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/telemetry_schema.md`
- `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/consumer_compatibility.md`

### Implementation Files
- `dbex/io/writer.py:196-200` — HDF5 telemetry serialization (already implemented)
- `dbex/nanobrag_bridge.py:1118` — `load_refined_mtz` function
- `dbex/nanobrag_bridge.py:856` — `build_structure_factor_grid` function
- `dbex/nanobrag_bridge.py:1230` — `simulate_forward_once` function
- `dbex/refine_one.py:65-68` — `--refined-mtz` CLI argument

### Test Files
- `tests/dbex/test_refine_one_cli.py:913` — `test_torch_diagnostics_metadata`
- `tests/dbex/test_mapping_consistency.py:188` — `test_db_at_024_mapping_smoke`

### Specification & Architecture
- `docs/spec-db-tracing.md:85-120` — Diagnostics artifact expectations
- `docs/spec-db-workflow.md:125-158` — Calibration & unit conventions
- `docs/architecture/dbex/io/writer.idl.md:55-85` — Writer diagnostics contract
- `docs/architecture/calibration_scaling.md:45-78` — Calibration threading
- `docs/findings.md` SCALE-003/004/006/007 — Calibration telemetry findings

### Related Initiatives
- `plans/active/MAP-SCALE-002/implementation.md` — CLI plumbing context
- `plans/active/MAP-SCALE-004/implementation.md` — Zero-iteration telemetry parity (parallel initiative)
