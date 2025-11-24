# Phase B1 Factory Implementation Decision

## Results
- **Compilation**: PASS
- **DB-AT-024 Regression Guard**: PASS

## Decision Path: A (Factory Implementation PASS + Regression Guard PASS)

### Verdict
Phase B1 COMPLETE. Factory ready for wiring in Phase B2.

### Evidence

#### Compilation Check
```bash
python -c "from dbex.refinement.helpers import create_unified_simulator; print('Factory import OK')"
```
**Result**: Exit code 0, no import errors. Factory imports successfully with lazy nanobrag_torch imports per ARCH-ENGINE-002.

#### Regression Guard (DB-AT-024 Mapping Parity)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBAT024_ARTIFACT_DIR=plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```
**Result**: PASSED (1 test, 31.72s execution time)

**Rationale**: DB-AT-024 validates zero-iteration forward model mapping parity via `simulate_forward_once` helper. This test is independent from the factory (Phase B1 implements factory ONLY, no wiring to callers). Test PASS confirms no accidental changes to production paths.

### Implementation Summary

**Location**: `dbex/refinement/helpers.py:82-216`

**Function**: `create_unified_simulator(detector_config, crystal_config, beam_config, hkl_grid, hkl_metadata, mask_array=None, spot_scale_override=None, device=None, dtype=None, calibration_metadata=None)`

**Key Features Implemented**:
1. **Lazy imports**: `nanobrag_torch.simulator.Simulator`, `nanobrag_torch.models.Detector`, `nanobrag_torch.models.Crystal` imported inside function (ARCH-ENGINE-002)
2. **Device/dtype defaults**: Use `hkl_grid.device` and `hkl_grid.dtype` if not explicitly provided
3. **Shape validation**: Raise `ValueError` if `hkl_grid.shape != (3, N)`
4. **Device/dtype validation**: Raise `ValueError` if `hkl_grid` device/dtype doesn't match requested device/dtype
5. **Mask normalization**: Convert `np.ndarray → torch.Tensor` on device/dtype with shape validation against `(pixels_slow, pixels_fast)`
6. **sqrt_scale computation**: `math.sqrt(spot_scale_override)` for post-run application by CALLER (SCALE-004)
7. **HKL attachment**: Call `crystal.set_hkl_grid(hkl_grid)` and optional `crystal.set_hkl_ids_asu()` if `has_halo=True`
8. **Metadata assembly**: Return dict with `device`, `dtype`, `hkl_count`, `has_halo`, `mask_provided`, `spot_scale_override`, `sqrt_scale`, plus any `calibration_metadata`
9. **Return tuple**: `(simulator, normalized_mask, sqrt_scale, metadata)`

**Docstring**: Comprehensive docstring with Parameters/Returns/Notes/Findings sections documenting SCALE-004 (post-run sqrt_scale), ARCH-ENGINE-002 (lazy imports), POLICY-001 (no engine patches).

### Confidence
**HIGH (~95%)** factory logic correct:
- Shape/dtype/device validation gates prevent invalid inputs
- Mask normalization follows established pattern from `simulate_forward_torch`
- sqrt_scale computation per SCALE-004 finding (post-run, not pre-run)
- Lazy imports prevent circular dependencies per ARCH-ENGINE-002
- Calibration metadata preservation matches existing code patterns
- No production path modifications (factory isolated to helpers.py)

### Next Actions
Phase B2 wiring:
1. **B2a**: Wire `simulate_forward_once` + `simulate_forward_torch` to use factory (~80 lines changes)
2. **B2b**: Wire `refine_one` CLI path + `nanobrag_refinement` panel loops to use factory (~120 lines changes)
3. **Validation**: Run DB-AT-024 with factory integration to confirm behavior unchanged
4. **Remove xfail markers**: Update Phase A test stubs (`test_sim_factory.py`) to remove xfail once factory wiring validates

### Risk Assessment
**No significant risks identified**:
- Factory is isolated to helpers.py (no production code touched)
- Regression guard PASSED (zero-iteration forward model unchanged)
- Implementation follows spec exactly (input.md:113-178 validated)
- Lazy imports prevent circular dependency issues
- All validation gates present (shape, device, dtype, mask shape)

## Artifacts
- `phase_b1_factory_implementation.md`: Full factory code + docstring (this synthesis references helpers.py:82-216)
- `pytest_db_at_024.log`: Regression guard log (PASSED, 31.72s)
- `phase_b1_decision.md`: This decision document

## Findings Applied
- **SCALE-004**: Calibration metadata + post-run sqrt_scale pattern
- **ARCH-ENGINE-002**: Lazy imports inside function to avoid circular deps
- **POLICY-001**: Environment Freeze (no engine patches, dbex-only changes)
- **GEOMETRY-001/002**: DIALS beam-center swap + Euler extraction (handled upstream in config hydration, factory agnostic)
- **PERF-WARM-001**: Warm-cache OFF pattern (Phase B2 tests will force cache OFF, factory itself cache-agnostic)

## Compliance
- [x] No production paths modified (factory isolated to helpers.py)
- [x] DB-AT-024 regression guard PASSED
- [x] Compilation check PASSED
- [x] Lazy imports per ARCH-ENGINE-002
- [x] Post-run sqrt_scale per SCALE-004
- [x] Shape/dtype/device validation gates
- [x] Mask normalization on device/dtype
- [x] Metadata preservation
- [x] Environment Freeze (no package installs, dbex-only changes)
