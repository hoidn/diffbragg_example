# TORCH-API-ALIGN-001 Phase A Test Stubs Summary

## Overview
Authored 4 xfail-guarded test stubs encoding acceptance criteria for TDD (Tests First) approach per TORCH-API-ALIGN-001 Phase A.

## Test Stubs Created

### A1: DIALS Mapping Parity
- **File**: `tests/dbex/test_bridge_mapping.py`
- **Test**: `test_dials_mapping_parity`
- **Acceptance Criteria**:
  - Beam-center swap: (fast, slow) → (s, f)
  - Euler angle extraction from panel rotation axes
  - custom_beam_vector ignored under DIALS (documented behavior)
- **Fixture**: `warm_cache_off` (forces `NANOBRAGG_DISABLE_COMPILE=1` + `enable_stage_a_warm_cache=False`)
- **Status**: xfail until Phase B wiring (B1/B2)
- **Findings Applied**: GEOMETRY-001/002, CONFIG-001/002

### A2: Unified Simulator Factory
- **File**: `tests/dbex/test_sim_factory.py`
- **Tests**:
  1. `test_panel_and_stitched_shapes` (one-panel + multi-panel stitched)
  2. `test_factory_cuda` (CUDA device validation, skipif not available)
- **Acceptance Criteria**:
  - Factory validates shape/dtype/device
  - One-panel and multi-panel stitched outputs
  - spot_scale_override handling (sqrt post-run)
  - Calibration metadata (beam_config, N_cells) preserved
  - Mask array normalized on device/dtype
- **Fixture**: `warm_cache_off` (per above)
- **Status**: xfail until Phase B wiring (B1/B2)
- **Findings Applied**: SCALE-004, PERF-WARM-001

### A3: ExperimentModel Parity
- **File**: `tests/dbex/test_experiment_parity.py`
- **Test**: `test_parity_small_fixture`
- **Acceptance Criteria**:
  - ExperimentModel(param_init="frozen") outputs match legacy within 1e-6
  - ROI cropping parity (cropped DetectorConfig + beam center shift)
  - Per-panel and stitched output consistency
  - Structure factor attachment via experiment.set_structure_factors
- **Fixture**: `warm_cache_off` (per above)
- **Status**: xfail until Phase B wiring (B3)
- **Findings Applied**: ARCH-ENGINE-002, PERF-WARM-001

### A4: CUSTOM Override (Optional)
- **File**: `tests/dbex/test_bridge_custom_override.py`
- **Test**: `test_custom_override_exploratory`
- **Acceptance Criteria**:
  - CUSTOM DetectorConfig with custom basis from panel axes
  - custom_beam_vector=normalize(-s0) explicit injection
  - Parity deltas vs DIALS measured on fixtures
  - Acceptance thresholds/use-cases documented
- **Status**: xfail until Phase C (C1/C2), optional path (default OFF)
- **Findings Applied**: CONFIG-001, GEOMETRY-001

## Collection Validation
- **Command**: `pytest --collect-only tests/dbex/test_bridge_mapping.py tests/dbex/test_sim_factory.py tests/dbex/test_experiment_parity.py tests/dbex/test_bridge_custom_override.py`
- **Result**: ✓ 5 tests collected (A1=1, A2=2, A3=1, A4=1)
- **Log**: `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/pytest_collect_phase_a.log`

## xfail Rationale
All tests marked with `@pytest.mark.xfail(reason="TORCH-API-ALIGN-001 Phase B wiring not yet implemented")` to prevent CI failures while encoding acceptance criteria. Tests also contain `pytest.skip("Phase B/C wiring pending")` as immediate guard.

## warm_cache_off Fixture
All tests use a common fixture to ensure deterministic behavior:
- Sets `NANOBRAGG_DISABLE_COMPILE=1` environment variable
- Yields `{"enable_stage_a_warm_cache": False}` config dict
- Restores environment on teardown

## Registry Updates
- **TESTING_GUIDE.md §2**: Added 4 rows after Runtime vectorization entry
  - DB-API-A1: DIALS Mapping Parity
  - DB-API-A2: Unified Factory
  - DB-API-A3: ExperimentModel Parity
  - DB-API-A4: CUSTOM Override
- **TEST_SUITE_INDEX.md**: Added 4 rows with full test specifications

## Next Steps (Phase B)
1. Implement unified simulator factory (B1)
2. Replace duplicate wiring with factory calls (B2)
3. Implement ExperimentModel adapter (B3)
4. Remove xfail markers once tests PASS
5. Update registry Status from "Active (xfail)" to "Active"

## Spec Citations
- **implementation.md:42-44** (A1 DIALS mapping)
- **implementation.md:46-49** (A2 factory shape/dtype)
- **implementation.md:50-54** (A3 ExperimentModel parity)
- **implementation.md:55-57** (A4 CUSTOM override)
- **docs/nanobrag_api.md:44-47** (DIALS convention)
- **docs/config_crosswalk.md:29** (beam-center swap)
