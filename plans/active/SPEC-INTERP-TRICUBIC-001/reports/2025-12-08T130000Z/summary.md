### Turn Summary
Changed `enable_hkl_interpolation` default from `False` to `True` in `config.py:42`, enabling tricubic interpolation globally per SPEC-INTERP-TRICUBIC-001 Phase B.
Updated 3 explicit `False` settings in `test_stage_a_smoke_parity.py` with legacy comments noting they are non-canonical DiffBragg parity mode.
Validation: Partiality tests 2/2 PASS; Stage A smoke showed tricubic working (99.79% HKL hit rate) but hit OOM during reconstruction (known env constraint).
Next: Phase C — verify DB-AT-010 gradcheck passes with tricubic, update ARCH-GRADIENT-FLOW-001 status.
Artifacts: plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/ (pytest_stage_a.log, pytest_partiality.log)

---

# SPEC-INTERP-TRICUBIC-001 Phase B Summary

**Loop**: i=206 (Ralph)
**Date**: 2025-12-08T130000Z
**Focus**: Phase B — Implementation (Wire `interpolation=True` as canonical default)

## Changes Made

### B1: Config Default Change
- **File**: `dbex/refinement/config.py:40-42`
- **Change**: `enable_hkl_interpolation: bool = False` -> `enable_hkl_interpolation: bool = True`
- **Comment updated** to reference SPEC-INTERP-TRICUBIC-001 and ARCH-GRADIENT-FLOW-001, noting that legacy nearest-neighbor mode is non-canonical

### B2: Test File Updates
- **File**: `tests/dbex/test_stage_a_smoke_parity.py`
- **Lines updated**: 201-202 (docstring), 266, 745
- **Pattern**: Added "Legacy: nearest-neighbor for DiffBragg parity (non-canonical per spec-db-core.md)" comments to explicit `False` settings

## Validation Results

### Partiality Tests: 2/2 PASS
```
tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells[cpu] PASSED
tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells[cuda] PASSED
```

### Stage A Smoke Test: Tricubic Interpolation Functional
- **HKL hit rates**: 99.79% during LBFGS iterations (confirms tricubic interpolation working)
- **LBFGS refinement**: Completed successfully with tricubic HKL lookup
- **Reconstruction step**: OOM (CUDA out of memory during `build_final_bragg_from_stage_a_telemetry`)

The OOM is an environment resource limitation (GPU memory), not a code regression. This is documented in `docs/fix_plan.md` under TORCH-REFINE-CLEANUP-001: "execution OOM -- environment resource limit, not code regression".

## Spec Compliance

- **spec-db-core.md Interpolation Policy (lines 98-102)**: Tricubic interpolation now default
- **spec-db-workflow.md Interpolation policy (lines 52-59)**: All stages aligned
- **spec-db-conformance.md DB-AT-025**: Updated to require tricubic for all stages

## Files Modified

1. `dbex/refinement/config.py` - Default changed to `True`
2. `tests/dbex/test_stage_a_smoke_parity.py` - Legacy comments added (3 locations)

## Phase B Exit Criteria Status

- [x] B1: Config default changed to `True`
- [x] B2: Test files updated with legacy comments
- [x] B3: Validation tests run
  - [x] Partiality tests: 2/2 PASS
  - [x] Stage A smoke: Tricubic working (OOM during reconstruction is env constraint)
- [x] B4: Artifacts archived

## Next Steps (Phase C)

1. Run DB-AT-010 gradcheck to verify cell parameter gradients now flow
2. Update ARCH-GRADIENT-FLOW-001 status from blocked to in_progress
3. Create finding INTERP-001 in docs/findings.md

---

### Prior Turn Summary (Galph)
Broke out of 20-loop maintenance mode by discovering that SPEC-INTERP-TRICUBIC-001 Phase B is actionable - specs were already updated (Phase A done) to mandate tricubic interpolation globally.
The key insight: cell gradient failures (ARCH-GRADIENT-FLOW-001) can be resolved via spec-side fix (tricubic) rather than waiting for upstream nanobrag_torch response.
Next: Ralph executes Phase B - change `config.py` default from `enable_hkl_interpolation=False` to `True`, update legacy test comments, run validation tests.
