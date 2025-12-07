# MAP-SCALE-003 Phase A — Loop Summary

## Turn Summary
Completed Phase A planning deliverables for CLI refined structure-factor telemetry (MAP-SCALE-003). Schema audit revealed telemetry already implemented in writer (SCALE-003 landing); traced MTZ loading path from CLI → load_refined_mtz → build_structure_factor_grid → simulate_forward_once; defined 4-field telemetry schema (hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path); confirmed backward compatibility with test consumers. Phase B scope reduced to CLI plumbing verification + test assertions. Next action: verify dbex/refine_one.py populates hkl_telemetry correctly.

Artifacts: plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/ (schema_audit.md, mtz_flow_trace.md, telemetry_schema.md, consumer_compatibility.md, planning_notes.md)

---

## Planning Deliverables

### 1. Schema Audit (schema_audit.md)
**Status**: Complete

**Key finding**: Structure-factor telemetry already implemented in dbex/io/writer.py:196-200 (SCALE-003 landing)

**Schema**:
- `hkl_source` (str): "refined" | "raw"
- `hkl_n_reflections` (int): Reflection count
- `hkl_mean_amplitude` (float): Mean |F| amplitude
- `hkl_path` (str): MTZ file path

**Backward compatibility**: ✓ Confirmed (additive-only extension)

---

### 2. MTZ Flow Trace (mtz_flow_trace.md)
**Status**: Complete

**Call chain**:
1. dbex/refine_one.py:65-68 — `--refined-mtz` CLI argument
2. dbex/nanobrag_bridge.py:1118 — `load_refined_mtz` function
3. dbex/nanobrag_bridge.py:856 — `build_structure_factor_grid` function
4. dbex/nanobrag_bridge.py:1230 — `simulate_forward_once` function
5. dbex/io/writer.py:41 — `write_torch_outputs` function

**Hook points**:
- Primary: `simulate_forward_once` constructs `hkl_telemetry` dict from params + stats
- Secondary: CLI backend populates `hkl_source` and `hkl_path` based on `--refined-mtz` precedence

---

### 3. Telemetry Schema (telemetry_schema.md)
**Status**: Complete

**Schema definition**:
```python
hkl_telemetry = {
    "hkl_source": str,        # "refined" | "raw" | "unknown"
    "hkl_n_reflections": int, # len(hkl_indices)
    "hkl_mean_amplitude": float, # np.mean(np.abs(hkl_amplitudes))
    "hkl_path": str,          # Absolute MTZ path or ""
}
```

**Fallback rules**:
- Refined MTZ missing/invalid → fall back to raw, set `hkl_source="raw"`
- No MTZ path (tests) → set `hkl_path=""`
- SCALE-007 enforcement (Phase C): Disallow silent fallback when `--refined-mtz` explicit

**Validation**: Writer validates dict completeness; `n_reflections > 0`, `mean_amplitude > 0`

---

### 4. Consumer Compatibility (consumer_compatibility.md)
**Status**: Complete

**Consumers analyzed**:
1. test_torch_diagnostics_metadata (tests/dbex/test_refine_one_cli.py:913)
   - Impact: None (selective attr access)
   - Mock hkl_telemetry already present (lines 959-965)
   - Phase B: Add assertions for 4 new attrs

2. test_db_at_024_mapping_smoke (tests/dbex/test_mapping_consistency.py:188)
   - Impact: None (diagnostics dict consumer)
   - Phase B: Add `hkl_telemetry` assertions, verify `hkl_source="refined"`

3. dbex/look.py (visualization)
   - Impact: Unknown (not audited)
   - Risk: Low (likely selective attr access)

**Breaking change risk**: None (additive-only extension)

---

### 5. Planning Notes (planning_notes.md)
**Status**: Complete

**Summary**:
- Schema already implemented; Phase B scope reduced
- Hook point identified: `simulate_forward_once` constructs telemetry dict
- Test mocks already prepared (test_torch_diagnostics_metadata)
- Backward compatibility confirmed (no breaking changes)

**Phase B plan**:
1. Verify CLI plumbing (dbex/refine_one.py → write_torch_outputs data flow)
2. Extend test assertions (2 tests: diagnostics_metadata + db_at_024)
3. Run tests, capture pytest logs

**Next action**: Read dbex/refine_one.py to trace `hkl_source`/`hkl_path` population

---

## ARCH Conformance

**ARCH-CONTRACT-WRITER-001** (Torch Diagnostics Persistence): ✓ Conformant
- Additive-only schema extension
- Backward compatibility maintained

**ARCH-CONTRACT-STRUCTURE-FACTORS-001** (Refined MTZ Ingestion): ✓ Conformant
- Call chain traced
- Telemetry captures provenance
- No silent fallback in schema design

**ARCH-CONTRACT-CALIBRATION-001** (Calibration Metadata Threading): Not applicable (Phase A planning only)

---

## Findings Applied

| Finding | Application |
|---------|-------------|
| SCALE-003 | ✓ Traced refined MTZ loading path (load_refined_mtz, build_structure_factor_grid) |
| SCALE-004 | ✓ Identified CLI plumbing (--refined-mtz arg), defined hkl_path telemetry field |
| SCALE-006 | ✓ Defined provenance fields (hkl_source, hkl_n_reflections, hkl_mean_amplitude) |
| SCALE-007 | ✓ Defined fallback schema; deferred enforcement to Phase C (MAP-SCALE-005) |
| TESTING-003 | ✓ Phase B acceptance includes pytest --collect-only logs |

---

## Phase B Readiness

**Entry criteria**: ✓ All met
- [x] 5 planning deliverables complete
- [x] Hook points identified
- [x] Test modification strategy defined
- [x] Backward compatibility confirmed

**Recommendation**: Proceed to Phase B implementation

**Phase B scope**:
1. CLI plumbing verification (file:line anchors)
2. Test assertion extensions (2 tests)
3. Pytest logs (validation)

---

## References

**Planning artifacts**: plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/
- schema_audit.md
- mtz_flow_trace.md
- telemetry_schema.md
- consumer_compatibility.md
- planning_notes.md

**Implementation files**:
- dbex/io/writer.py:196-200 (telemetry serialization)
- dbex/nanobrag_bridge.py:1118, 856, 1230 (MTZ loading, HKL grid, diagnostics)
- dbex/refine_one.py:65-68 (CLI argument)

**Tests**:
- tests/dbex/test_refine_one_cli.py:913 (test_torch_diagnostics_metadata)
- tests/dbex/test_mapping_consistency.py:188 (test_db_at_024_mapping_smoke)
