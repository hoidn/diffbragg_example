# Input for Ralph: ARCH-REFACTOR-001 Phase D.3 Batch 2 Corrective Fix (Crystal Initialization Bug)

## Summary
Fix Crystal initialization bug in Stage A reconstruction helper: pass `beam_config` to constructor instead of post-hoc assignment.

## Mode
none (targeted bugfix)

## InitiativeType
bugfix

## Focus
[ARCH-REFACTOR-001] — Refinement Engine Modularization & Physics Separation (Phase D.3 Batch 2 corrective fix)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity`
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/`

## Do Now

### Context
Tests `test_db_at_028` and `test_db_at_029` FAIL with `bragg_after` near-zero (7.59e-14 mean) when it should contain refined Bragg pattern (~1.86 mean). Root cause analysis (see `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/root_cause_analysis.md`) identified a bug in `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry`:

The function constructs `Crystal(..., beam_config=None, ...)` (line 148-153), then assigns `crystal_model.beam_config = stage_a_ctx.beam_config` post-hoc (line 165). This is wrong - Crystal needs `beam_config` at construction time to initialize internal matrices. All other Crystal constructions in the codebase pass `beam_config` directly.

### Implementation Target
**File**: `dbex/refinement/reconstruction.py`
**Function**: `build_final_bragg_from_stage_a_telemetry` (lines 148-167, warm cache path)

### Tasks
1. **Refactor Crystal construction in warm cache path** (lines 148-167):
   - Move the Crystal construction INSIDE the `if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):` block (after line 160)
   - Pass `beam_config=stage_a_ctx.beam_config` to Crystal constructor directly (not `beam_config=None`)
   - Remove the post-hoc assignment `crystal_model.beam_config = stage_a_ctx.beam_config` (line 165)
   - Keep `crystal_model.hkl_data` and `crystal_model.hkl_metadata` assignments in place
   - Keep the `_retarget_stage_a_simulators` call and `simulators = stage_a_ctx.simulators` assignment

2. **Handle cold path**: Cold path (lines 168-190) already constructs `beam_config` from dxtbx `beam` and passes it to `create_unified_simulator`. No changes needed.

3. **Validate**:
   - Run: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -xvs tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/pytest_parity_batch2_fixed.log`
   - Expected: 2/2 PASSED, `bragg_after_mean` ≈ O(1), ROI correlation median > -0.1

## How-To Map

### Crystal Construction Pattern (Reference)
Other Crystal constructions in the codebase (correct pattern):
- `reconstruction.py::build_final_bragg_from_stage_b_telemetry` line 400: `Crystal(..., beam_config=stage_a_ctx.beam_config, ...)`
- `stage_a_utils.py` line 497: `Crystal(..., beam_config=beam_config_for_run, ...)`
- `stage_a.py` line 1219: `Crystal(..., beam_config=beam_config_for_run, ...)`

### Expected Code Change
**Before** (lines 148-167):
```python
crystal_model = Crystal(
    crystal_config,
    beam_config=None,  # WRONG
    device=device,
    dtype=dtype,
)
crystal_model.interpolate = config.enable_hkl_interpolation
crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
crystal_model.hkl_metadata = hkl_metadata

if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
    from dbex.refinement.stage_a_utils import _retarget_stage_a_simulators
    crystal_model.beam_config = stage_a_ctx.beam_config  # Too late!
    _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
    simulators = stage_a_ctx.simulators
else:
    # cold path...
```

**After** (warm/cold paths):
```python
if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
    # Warm cache path: construct Crystal with beam_config from context
    crystal_model = Crystal(
        crystal_config,
        beam_config=stage_a_ctx.beam_config,  # FIXED
        device=device,
        dtype=dtype,
    )
    crystal_model.interpolate = config.enable_hkl_interpolation
    crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
    crystal_model.hkl_metadata = hkl_metadata

    from dbex.refinement.stage_a_utils import _retarget_stage_a_simulators
    _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
    simulators = stage_a_ctx.simulators
else:
    # Cold path: build simulators via unified factory (beam_config created below)
    from dbex.refinement.config_factories import create_beam_config
    from dbex.refinement.helpers import create_unified_simulator
    beam_config = create_beam_config(beam)
    simulators = []
    for pid in sampled_panel_ids:
        detector_config = create_detector_config(detector[pid], beam=beam)
        simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(
            detector_config=detector_config,
            crystal_config=crystal_config,
            beam_config=beam_config,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            mask_array=None,
            spot_scale_override=None,
            device=device,
            dtype=dtype,
            calibration_metadata=getattr(config, 'calibration_metadata', None),
        )
        simulator.interpolate = config.enable_hkl_interpolation
        simulators.append(simulator)
```

### Test Execution
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/pytest_parity_batch2_fixed.log
```

## Pitfalls To Avoid
1. **Do not remove `hkl_data` / `hkl_metadata` assignments** - Crystal needs these attached before retargeting
2. **Do not modify cold path** - it already constructs `beam_config` and passes to factory correctly
3. **Respect device/dtype neutrality** - use `device` and `dtype` parameters consistently
4. **Environment Freeze** - no package installs; if import fails, escalate
5. **Initiative Type Boundary** - this is a `bugfix` (implementation defect), not `architecture` or `harness`

## If Blocked
If tests still fail with near-zero `bragg_after`:
1. Capture `bragg_after_mean`, `bragg_after_std`, `bragg_after_max` from test output
2. Check if simulators are being retargeted (add debug print in `_retarget_stage_a_simulators`)
3. Verify `crystal_model.hkl_data` is not None/empty after construction
4. Update Attempts History in `docs/fix_plan.md` with failure signature
5. Mark as blocked if Crystal constructor itself is broken (upstream nanobrag_torch bug)

## Findings Applied
- **GRADIENT-004**: Warm cache retargeting requires Crystal with valid beam_config at construction time
- **ARCH-STAGE-CONTEXT-001 Phase D**: Terminal stage artifact reconstruction must use properly initialized Crystal
- **ARCH-FACTORY-001**: Unified factory pattern already handles beam_config correctly (cold path reference)

## Pointers
- Root cause analysis: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/root_cause_analysis.md`
- Reconstruction helper: `dbex/refinement/reconstruction.py:28-201` (function `build_final_bragg_from_stage_a_telemetry`)
- Test file: `tests/dbex/test_stage_a_smoke_parity.py:58-283` (functions `stage_a_smoke_fixture`, `test_db_at_028`, `test_db_at_029`)
- Previous attempt: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/summary.md`
- Fix plan: `docs/fix_plan.md` (search for `[ARCH-REFACTOR-001]`)
- Crystal reference: `stage_a_utils.py:497-502`, `stage_a.py:1219-1224`, `reconstruction.py:400-405`

## Next Up
None - this is a targeted bugfix. If tests pass, Phase D.3 Batch 2 is complete and D.3 Batch 3 (test_db_at_029 structure parity validation) can proceed.

## Doc Sync Plan
Not applicable - no test changes this loop.
