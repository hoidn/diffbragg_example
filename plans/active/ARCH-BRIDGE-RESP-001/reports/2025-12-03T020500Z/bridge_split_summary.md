# Bridge Split Summary — ARCH-BRIDGE-RESP-001 Phase C

**Date**: 2025-12-03T020500Z
**Loop**: Ralph implementation loop for ARCH-BRIDGE-RESP-001 Phase C

## Responsibility Map: Before / After

### Before (Single `dbex/nanobrag_bridge.py`)

All functionality in one 2117-line module:
- **RefinementInputs dataclass** (lines 52-79)
- **prepare_refinement_inputs()** (lines 81-277) — background subtraction, masking, sigma broadcast, ADU↔photon
- **create_detector_config()** (lines 283-462) — DIALS Euler extraction, ROI cropping, trusted mask tensor coercion
- **create_beam_config()** (lines 465-515) — wavelength, polarization, calibration metadata
- **create_crystal_config()** (lines 518-631) — unit cell, MOSFLM A* injection, N_cells guard
- Plus: structure factor grid builders, calibration loaders, orientation helpers, etc.

### After (Modular Structure)

**New Modules**:
1. **`dbex/refinement/inputs.py`** (~280 lines)
   - RefinementInputs dataclass
   - prepare_refinement_inputs() — all guards (square pixel, sentinel, mask polarity, sigma broadcast)
   - Responsibilities: refinement data preparation, background subtraction, photon conversion

2. **`dbex/refinement/config_factories.py`** (~420 lines)
   - create_detector_config() — geometry mapping, Euler angles, ROI cropping, mask tensor coercion
   - create_beam_config() — wavelength, polarization, calibration plumbing
   - create_crystal_config() — unit cell, MOSFLM A*, N_cells guard, crystal overrides for gradient flow
   - Responsibilities: dxtbx → nanobrag_torch config hydration per docs/config_crosswalk.md

**Bridge Module** (`dbex/nanobrag_bridge.py` — now ~1400 lines):
- Re-exports from inputs + config_factories (with TODO deprecation notes)
- Retains: structure factor grids, calibration metadata loading, orientation helpers (recover_cell_from_a_star, derive_b_ideal, quaternion transforms, etc.)
- Role: orchestration glue + bridge-level helpers not suitable for refinement package

## Behavioral Guarantees (Phase C.2)

All existing contracts preserved byte-for-byte:
- **GEOMETRY-001/002/003**: Detector/beam/crystal mapping rules from docs/config_crosswalk.md unchanged
- **CONFIG-001**: [panel, slow, fast] ordering, mask polarity, ADU↔photon policy intact
- **DIAGNOSTICS-001 & PHYSICS-LOSS-001/002/003**: Variance-weighted loss inputs, sigma provenance unchanged
- **Square pixel guard** (spec-db-core.md:40)
- **Sentinel guards** (simtbx_api.md:14)
- **Mask polarity** (spec-db-core.md:29)
- **ROI cropping with beam center adjustment**
- **Distance override tensors for Stage C** (TORCH-REFINE-003)

## Import Migration

### Internal `dbex/` Modules (Updated to New Paths)

- `dbex/physics/forward.py` — now imports config factories from `dbex.refinement.config_factories`
- `dbex/refine_one.py` — now imports prepare_refinement_inputs from `dbex.refinement.inputs`, config factories from `dbex.refinement.config_factories`
- `dbex/nanobrag_refinement.py` — config factories from new module
- `dbex/refinement/stage_a_impl.py` — config factories from new module
- `dbex/refinement/stage_c_impl.py` — config factories from new module
- `dbex/refinement/stage_c.py` — config factories from new module
- `dbex/refinement/reconstruction.py` — create_beam_config from new module
- `dbex/vis/mapping.py` — RefinementInputs + prepare_refinement_inputs from new module
- `dbex/vis/stage_a.py` — RefinementInputs from new module

### Re-Export Layer (Temporary Compatibility)

`dbex/nanobrag_bridge.py` now contains:
```python
# TODO(ARCH-BRIDGE-RESP-001): Remove re-exports once downstream consumers migrate
from dbex.refinement.inputs import RefinementInputs, prepare_refinement_inputs
from dbex.refinement.config_factories import (
    create_detector_config,
    create_beam_config,
    create_crystal_config
)
```

This ensures that tests and external scripts still importing from `dbex.nanobrag_bridge` continue to work.

## Test Results (Phase C.3)

All mapped selectors **PASSED** with new module structure:
- `tests/dbex/test_nanobrag_bridge.py` — 5/5 passed (0.99s)
- `tests/dbex/test_nanobrag_bridge_configs.py` — 19 passed, 1 skipped (1.77s)
- `tests/dbex/test_refine_one_cli.py::{test_nanobrag_backend_runs_simulator, test_nanobrag_backend_applies_calibration, test_torch_diagnostics_metadata}` — 4/4 passed (1.02s)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — 1/1 passed (7.30s)

**Note on Test Patches**: Tests were updated to patch functions at their new defining module (e.g., `@patch('dbex.refinement.config_factories.create_detector_config')`) since they're now imported lazily within functions rather than at module scope.

## Static Analysis

Compilation checks passed for all new and modified modules:
```bash
python -m compileall dbex/refinement/inputs.py dbex/refinement/config_factories.py dbex/nanobrag_bridge.py
# All files compiled successfully
```

## Next Steps (Phase C.4+)

1. **Remove re-export layer**: Once all external consumers (scripts, notebooks) are updated to import from `dbex.refinement.inputs` and `dbex.refinement.config_factories`, remove the TODO-marked re-exports from `dbex/nanobrag_bridge.py`
2. **Docs registry update**: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` if test selectors changed (none did in this loop)
3. **Trim bridge module**: Consider whether remaining bridge helpers (structure factor grids, etc.) belong in more specific modules (e.g., `dbex/physics/` or `dbex/io/`)

## Artifacts

- Pytest logs: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/pytest_*.log`
- This summary: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/bridge_split_summary.md`
