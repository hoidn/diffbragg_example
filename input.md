# ARCH-REFACTOR-001 Phase B: Telemetry Standardization (Dataclass + Dynamic HDF5 I/O)

## Summary
Convert RefinementTelemetry to dataclass with to_dict() method and refactor _write_torch_outputs to use dynamic iteration, eliminating ~60 lines of manual field mapping.

## Mode
none (code refactor + validation)

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase B: Telemetry Standardization)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Primary validation: telemetry instantiation + HDF5 I/O)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (Regression guard: mapping parity unchanged)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/`
- `phase_b_planning_analysis.md` (planning document, already exists)
- `pytest_stage_a_smoke.log` (test_stage_a_expansion after Phase B changes)
- `pytest_db_at_024.log` (regression guard)
- `phase_b_decision.md` (Path A/B/C/D verdict with confidence assessment)
- `summary.md` (Turn Summary block)

## Do Now

Ralph, execute ARCH-REFACTOR-001 Phase B implementation (telemetry standardization):

**Context:** Phase A successfully extracted core physics functions (derive_u_matrix, variance_weighted_loss) to leaf-node modules with all tests passing. Phase B modernizes RefinementTelemetry and HDF5 I/O to reduce boilerplate and prepare for robust logging.

**Objective:** Convert RefinementTelemetry to dataclass with dynamic serialization, eliminating ~60 lines of manual field mapping in _write_torch_outputs.

### Implementation Steps (9-Step Protocol)

1. **Read planning analysis:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/phase_b_planning_analysis.md`

2. **Implement Phase B1: Convert RefinementTelemetry to dataclass** (dbex/nanobrag_refinement.py:394-445)
   - Add import: `from dataclasses import dataclass, field, asdict`
   - Add `@dataclass` decorator before class
   - Convert all mutable defaults to `field(default_factory=...)`: lists → `field(default_factory=list)`, dicts → `field(default_factory=dict)`
   - Add `telemetry_version: str = "1.0"` field
   - Add `to_dict()` method: `return asdict(self)`

3. **Implement Phase B2: Refactor _write_torch_outputs** (dbex/refine_one.py:674-785)
   - Preserve HDF5 schema (same attr/dataset names)
   - Replace manual field mapping with dynamic iteration over `stage_telem.to_dict().items()`
   - Add `_coerce_scalar(value)` helper for numpy/torch type coercion
   - Handle nested structures: lists → datasets, dicts → flatten or JSON, tuples → split attrs

4. **Validation: Run Stage A smoke test**
   - Env: `DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - Command: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -xvs --tb=short`
   - Capture: `pytest_stage_a_smoke.log`

5. **Validation: Run regression guard**
   - Env: `DBAT024_ARTIFACT_DIR=plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - Command: `pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke -xvs --tb=short`
   - Capture: `pytest_db_at_024.log`

6. **Decision synthesis** → `phase_b_decision.md` (Path A/B/C/D verdict)

7. **Update implementation.md** Phase B checklist (mark B1, B2, B3 complete)

8. **Write summary.md** with Turn Summary block

9. **Commit:** `git commit -m "ARCH-REFACTOR-001 Phase B: Telemetry standardization (dataclass + dynamic HDF5 I/O) — tests: run"` and push

## How-To Map

### Test Commands
```bash
# Stage A smoke (primary validation)
DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -xvs --tb=short 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/pytest_stage_a_smoke.log

# DB-AT-024 regression guard
DBAT024_ARTIFACT_DIR=plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke -xvs --tb=short 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/pytest_db_at_024.log
```

### Code Locations
- **RefinementTelemetry:** dbex/nanobrag_refinement.py:394-445
- **_write_torch_outputs:** dbex/refine_one.py:569-785

## Pitfalls To Avoid

1. **DO NOT** change field types/names (backward compatibility)
2. **DO NOT** add non-stdlib imports (Environment Freeze)
3. **DO NOT** modify HDF5 attr/dataset names (preserve schema)
4. **DO** use `field(default_factory=list)` for mutable defaults
5. **DO** handle Optional fields with `if value is not None`
6. **DO** coerce numpy/torch types to Python scalars
7. **DO** preserve param_deltas schema: flatten dict to `refine_param_deltas_{param_name}`
8. **DO** run BOTH tests before committing

## Findings Applied (Mandatory)

- **POLICY-001** (Environment Freeze): stdlib dataclasses only ✓
- **PHYSICS-LOSS-001** (Dual Loss Metrics): chi_squared + masked_mse preserved ✓
- **REFINE-007-EXT** (Stage Telemetry Schema): stage_type/mode preserved ✓
- **ARCH-ENGINE-002** (Lazy Imports): no new top-level imports ✓

## Pointers

- Planning: plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/phase_b_planning_analysis.md
- Implementation Plan: plans/active/ARCH-REFACTOR-001/implementation.md:118-132
- Spec (core): docs/spec-db-core.md:57-80
- Fix Plan: docs/fix_plan.md ARCH-REFACTOR-001 entry
- Phase A: plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/
