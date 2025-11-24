# ARCH-REFACTOR-001 Phase B Planning Analysis

**Date:** 2025-11-24T085000Z
**Loop:** Galph planning (i=254)
**Phase:** B — Telemetry Standardization
**Status:** Planning Complete → Ready for Implementation

## Executive Summary

Phase A successfully extracted core physics functions to leaf-node modules (derive_u_matrix, variance_weighted_loss). Phase B will modernize the RefinementTelemetry structure and HDF5 I/O to reduce boilerplate and prepare for robust logging.

**Objective:** Convert RefinementTelemetry to a dataclass with dynamic serialization, eliminating ~60 lines of manual field mapping in `_write_torch_outputs`.

**Decision:** APPROVE Phase B ready_for_implementation (single loop, ~3-4 hours estimated).

## Scope Analysis

### Current State Assessment

**RefinementTelemetry Class (dbex/nanobrag_refinement.py:394-445):**
- Plain class with 30+ fields (no @dataclass decorator)
- Field types: str, int, float, List, Dict, Tuple, Optional
- No `to_dict()` method — callers must manually access fields

**HDF5 I/O (dbex/refine_one.py:674-785):**
- Manual field mapping: 60+ lines of `stage_group.attrs["field_name"] = stage_telem.field_name`
- Brittle: Adding new telemetry field requires updating BOTH RefinementTelemetry AND _write_torch_outputs
- Inconsistent: Some fields are attrs, some are datasets (loss traces), no systematic schema

**Pain Points:**
1. **Boilerplate:** Adding a new telemetry field requires 3 changes (class field, HDF5 attr write, HDF5 attr read in analysis scripts)
2. **Type Safety:** No validation that HDF5 attrs match field types
3. **Backward Compatibility Risk:** Refactoring may break existing analysis scripts that read HDF5 attrs

### Target Architecture

**RefinementTelemetry (Modernized):**
```python
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any

@dataclass
class RefinementTelemetry:
    """Telemetry captured during refinement.

    For multi-stage refinement (Stage A + Stage C), this structure represents
    a single stage. The calling code aggregates multiple telemetry objects into
    a Dict[str, RefinementTelemetry] keyed by stage label ("A", "C").

    PHYSICS-LOSS-001: Tracks both chi_squared (variance-weighted loss, the optimization objective)
    and masked_mse (legacy metric for comparison). All stages minimize chi_squared per spec-db-core.md:57-68.

    ARCH-REFACTOR-001 Phase B: Dataclass with to_dict() for HDF5 serialization.
    """
    optimizer: str
    stage: str
    history_size: int
    max_iter: int
    tolerance_grad: float
    tolerance_change: float
    roi_sample_fraction: float
    roi_count_sampled: int
    roi_count_total: int
    loss_trace_sample: List[float] = field(default_factory=list)  # Deprecated
    loss_trace_full: List[Tuple[int, float]] = field(default_factory=list)  # Deprecated
    best_loss_full: Tuple[float, int] = (0.0, 0)  # Deprecated
    param_deltas: Dict[str, float] = field(default_factory=dict)
    status: str = "ok"
    message: str = ""
    perf_counters: Optional[Dict[str, Any]] = None
    # ... (30+ fields)
    telemetry_version: str = "1.0"  # Schema versioning for future compatibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert telemetry to dict for HDF5 serialization.

        Returns:
            Dict with scalar attrs (int/float/str/bool) and nested structures
            (lists, dicts, tuples). Caller handles HDF5 attr vs dataset decision.
        """
        return asdict(self)
```

**_write_torch_outputs (Refactored):**
```python
# Dynamic iteration over telemetry.to_dict().items()
for stage_label, stage_telem in telemetry_dict.items():
    stage_group = diag.create_group(f"stage_{stage_label}")

    telemetry_dict = stage_telem.to_dict()
    for key, value in telemetry_dict.items():
        # Handle nested structures
        if isinstance(value, (list, tuple)) and len(value) > 0:
            # Store as dataset (arrays)
            if isinstance(value[0], tuple):
                # Structured array for [(iter, value), ...]
                stage_group.create_dataset(key, data=value, ...)
            else:
                stage_group.create_dataset(key, data=value)
        elif isinstance(value, dict):
            # Nested dict: store as JSON attr or sub-group
            stage_group.attrs[key] = json.dumps(value)
        elif value is not None:
            # Scalar: store as HDF5 attr
            stage_group.attrs[key] = _coerce_scalar(value)
```

### Checklist (implementation.md:119-128)

- **B1:** Convert `RefinementTelemetry` to dataclass
  - Add `@dataclass` decorator
  - Convert field definitions to dataclass syntax with `field()` for mutable defaults
  - Implement `to_dict()` method using `asdict()`
  - Add `telemetry_version: str = "1.0"` field
- **B2:** Refactor `_write_torch_outputs` in `refine_one.py`
  - Replace manual field mapping (lines 690-785) with dynamic iteration over `telemetry.to_dict().items()`
  - Handle nested dicts, arrays, scalars per HDF5 compatibility rules
  - Preserve backward compatibility: keep same HDF5 attr/dataset names
- **B3:** Verify HDF5 output structure
  - Run `test_stage_a_expansion`, inspect output HDF5 file
  - Compare old vs new HDF5 structure (same attrs, same datasets)
  - Confirm existing analysis scripts can read new format

## Implementation Steps (9-Step Protocol)

1. **Read planning analysis** (this document) + implementation.md Phase B checklist
2. **Convert RefinementTelemetry to dataclass** (dbex/nanobrag_refinement.py:394-445)
   - Add `from dataclasses import dataclass, field, asdict` import
   - Add `@dataclass` decorator before class definition
   - Convert 30+ fields to dataclass syntax:
     - Immutable defaults (str/int/float/None) → `field_name: type = default_value`
     - Mutable defaults (list/dict) → `field_name: type = field(default_factory=factory)`
   - Add `telemetry_version: str = "1.0"` as last field
   - Implement `to_dict(self) -> Dict[str, Any]:` method using `return asdict(self)`
3. **Test dataclass conversion** (sanity check)
   - Run `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -xvs` (Stage A smoke test)
   - Confirm telemetry object instantiation works (no AttributeError, no TypeError)
4. **Refactor _write_torch_outputs** (dbex/refine_one.py:674-785)
   - Replace manual field mapping with dynamic iteration:
     ```python
     telemetry_dict_data = stage_telem.to_dict()
     for key, value in telemetry_dict_data.items():
         # Handle nested structures (list/dict/tuple)
         # Preserve HDF5 attr/dataset distinction
     ```
   - Special handling:
     - Lists of tuples (loss traces) → structured numpy array datasets
     - Dicts (perf_counters, param_deltas) → JSON string attrs
     - Optional[T] → skip if None
     - Tuples (best_loss_full) → extract components to separate attrs
5. **Run HDF5 output validation** (Phase B3 checklist)
   - Run `test_stage_a_expansion` with `NANOBRAGG_DISABLE_COMPILE=1`
   - Capture HDF5 output path (args.outFile)
   - Inspect HDF5 structure using `h5dump` or Python h5py
   - Verify attrs/datasets match baseline (before/after comparison)
6. **Decision synthesis** (4-path template)
   - **Path A:** All tests PASS, HDF5 structure matches baseline → Phase B COMPLETE
   - **Path B:** Tests PASS, HDF5 structure differs (minor) → Document differences, assess backward compatibility
   - **Path C:** Tests FAIL (telemetry error) → Debug dataclass conversion, fix field defaults
   - **Path D:** Tests FAIL (HDF5 I/O error) → Debug _write_torch_outputs dynamic iteration, fix type handling
7. **Update implementation.md** (Phase B checklist B1-B3 marked complete)
8. **Write summary.md** with Turn Summary block (Phase B complete, telemetry modernized, HDF5 I/O dynamic)
9. **Commit** all changes:
   - `git add dbex/nanobrag_refinement.py dbex/refine_one.py plans/active/ARCH-REFACTOR-001/`
   - `git commit -m "ARCH-REFACTOR-001 Phase B: Telemetry standardization (dataclass + dynamic HDF5 I/O) — tests: run"`
   - `git push`

## Risk Assessment

### R1: Dataclass Field Defaults (MEDIUM)
- **Risk:** Mutable defaults (list/dict) without `field(default_factory=...)` raise TypeError
- **Mitigation:** Phase B1 systematically converts all mutable defaults to `field(default_factory=...)`
- **Detection:** Immediate TypeError on first RefinementTelemetry() instantiation

### R2: HDF5 Type Coercion (LOW)
- **Risk:** Dynamic iteration may encounter numpy/torch types that h5py doesn't accept directly
- **Mitigation:** Add `_coerce_scalar(value)` helper to convert numpy.int64 → int, torch.Tensor → float
- **Detection:** Caught by test_stage_a_expansion HDF5 write step

### R3: Backward Compatibility (LOW)
- **Risk:** Refactored HDF5 structure may break existing analysis scripts
- **Mitigation:** Phase B3 validation ensures same attr/dataset names as before (only implementation changes, not schema)
- **Detection:** Manual h5dump comparison before/after

### R4: Nested Dict Serialization (MEDIUM)
- **Risk:** HDF5 attrs have string length limits (~64KB), large nested dicts may truncate
- **Mitigation:** perf_counters and param_deltas are small (~10 keys each), JSON string serialization sufficient
- **Detection:** Phase B3 HDF5 inspection confirms full dict content stored

## Decision Tree (4 Paths)

### Path A: All Tests PASS, HDF5 Structure Matches Baseline
- **Outcome:** Phase B COMPLETE (telemetry modernized, HDF5 I/O dynamic, backward compatible)
- **Next Action:** Mark Phase B checklist complete in implementation.md, proceed to Phase C planning next loop

### Path B: Tests PASS, HDF5 Structure Differs (Minor)
- **Outcome:** Phase B MOSTLY COMPLETE (telemetry modernized, minor HDF5 schema drift)
- **Assessment:** Document differences in phase_b_decision.md, assess impact on analysis scripts
- **Next Action:** If differences are benign (field order, attr name normalization), accept and proceed to Phase C

### Path C: Tests FAIL (Telemetry Instantiation Error)
- **Outcome:** Phase B BLOCKED (dataclass conversion incomplete)
- **Root Cause:** Missing `field(default_factory=...)` for mutable defaults, or incorrect type annotations
- **Next Action:** Fix dataclass field definitions, re-run tests

### Path D: Tests FAIL (HDF5 I/O Error)
- **Outcome:** Phase B BLOCKED (dynamic iteration incomplete)
- **Root Cause:** Unhandled type in `to_dict()` output (numpy/torch types), or missing None check
- **Next Action:** Add type coercion helper, handle edge cases, re-run tests

## Estimated Effort

**Phase B1 (Dataclass Conversion):** ~45 minutes
- Add decorator + imports: 5 min
- Convert 30+ fields to dataclass syntax: 30 min
- Implement `to_dict()` method: 5 min
- Test instantiation: 5 min

**Phase B2 (HDF5 I/O Refactor):** ~90 minutes
- Replace manual field mapping: 45 min
- Handle nested structures: 30 min
- Test HDF5 write: 15 min

**Phase B3 (Validation):** ~45 minutes
- Run smoke test: 15 min
- Inspect HDF5 output: 15 min
- Compare before/after: 15 min

**Total:** ~3 hours (single loop feasible)

## Confidence Assessment

**HIGH confidence** (~90%) Phase B will succeed based on:
1. **Dataclass is standard library:** No external dependencies, well-understood semantics
2. **asdict() handles nested types:** Automatically converts dataclass fields to dict, including Optional/List/Dict
3. **HDF5 schema preservation:** Phase B3 validation explicitly checks backward compatibility
4. **Clear validation path:** test_stage_a_expansion provides immediate feedback on telemetry + HDF5 I/O
5. **Low regression risk:** RefinementTelemetry usage is localized to refinement + HDF5 I/O, no cross-cutting concerns

## Findings Applied

- **POLICY-001:** Environment Freeze (no package installs, stdlib dataclasses only) ✓
- **PHYSICS-LOSS-001:** Telemetry schema preserves chi_squared + masked_mse dual metrics ✓
- **REFINE-007-EXT:** Telemetry schema includes stage_type/mode fields from Phase A4/E ✓
- **ARCH-ENGINE-002:** Lazy imports preserved (no new imports added to top-level modules) ✓

## References

- **Spec:** docs/spec-db-workflow.md (no telemetry spec, implementation detail)
- **Implementation Plan:** plans/active/ARCH-REFACTOR-001/implementation.md:118-132 (Phase B checklist)
- **Current Code:**
  - RefinementTelemetry: dbex/nanobrag_refinement.py:394-445
  - HDF5 I/O: dbex/refine_one.py:674-785
- **Test Harness:** tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion (Stage A smoke test)
- **Findings:** POLICY-001, PHYSICS-LOSS-001, REFINE-007-EXT, ARCH-ENGINE-002

## Artifacts

All artifacts will be saved to `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/`:
- `phase_b_planning_analysis.md` (this document)
- `pytest_stage_a_smoke.log` (test_stage_a_expansion after Phase B changes)
- `hdf5_structure_before.txt` (h5dump baseline before Phase B)
- `hdf5_structure_after.txt` (h5dump output after Phase B)
- `phase_b_decision.md` (Path A/B/C/D verdict)
- `summary.md` (Turn Summary block)
