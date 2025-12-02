# Root Cause Analysis: bragg_after Near-Zero Bug

## Initiative
ARCH-REFACTOR-001 Phase D.3 Batch 2

## Symptom
Tests `test_db_at_028_loss_scale_sanity` and `test_db_at_029_structure_parity` FAIL with:
- `bragg_after_mean = 7.59e-14` (essentially zero) when it should contain refined Bragg pattern (~1.86 mean per `bragg_before`)
- `bragg_before_mean = 1.86` (reasonable, computed correctly from perturbed geometry)
- This causes ROI correlation and chi² metrics to fail validation

## Root Cause
**Bug in `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` lines 148-165**

The function constructs a Crystal model with `beam_config=None` (line 150):

```python
crystal_model = Crystal(
    crystal_config,
    beam_config=None,  # WRONG! Crystal needs beam_config at construction time
    device=device,
    dtype=dtype,
)
crystal_model.interpolate = config.enable_hkl_interpolation
crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
crystal_model.hkl_metadata = hkl_metadata

# ... later (line 165)
if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
    crystal_model.beam_config = stage_a_ctx.beam_config  # Too late!
    _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
    simulators = stage_a_ctx.simulators
```

**Post-hoc `beam_config` assignment (line 165) is too late**. The `nanobrag_torch.models.crystal.Crystal` constructor likely initializes internal matrices/grids that depend on `beam_config`. Setting it as an attribute after construction leaves the Crystal in an inconsistent state, causing `simulator.run()` to return near-zero arrays.

## Evidence
1. **Pattern Inconsistency**: All other Crystal constructions in the codebase pass `beam_config` directly to the constructor:
   - `reconstruction.py::build_final_bragg_from_stage_b_telemetry` line 400-405: `Crystal(..., beam_config=stage_a_ctx.beam_config, ...)`
   - `stage_a_utils.py` line 497-502: `Crystal(..., beam_config=beam_config_for_run, ...)`
   - `stage_a.py` line 1219-1224: `Crystal(..., beam_config=beam_config_for_run, ...)`

2. **Test Metrics**: `bragg_after` is 10 orders of magnitude smaller than expected, while `bragg_before` (computed with proper Crystal construction) is correct.

3. **Repeat Failure**: Same failure signature across two consecutive loops despite correcting `bragg_before` computation.

## Initiative Type Classification
This is a **bugfix** issue (implementation defect in reconstruction helper), NOT a **harness** or **architecture** issue. The reconstruction helper has broken initialization logic that violates `nanobrag_torch` API contracts.

## Fix Strategy
Update `build_final_bragg_from_stage_a_telemetry` to pass `beam_config` to Crystal constructor:

**Warm cache path** (lines 160-167):
```python
if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
    crystal_model = Crystal(
        crystal_config,
        beam_config=stage_a_ctx.beam_config,  # FIX: pass at construction time
        device=device,
        dtype=dtype,
    )
    # ... set hkl_data/metadata ...
    _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
    simulators = stage_a_ctx.simulators
```

**Cold path** (lines 168-190):
Already correct - constructs `beam_config` from dxtbx `beam` object and passes to `create_unified_simulator`.

## Validation
Run `test_db_at_028_loss_scale_sanity` and `test_db_at_029_structure_parity`. Expected:
- `bragg_after_mean` ≈ O(1) (not O(1e-14))
- ROI correlation `median(corrs_after) > -0.1` (currently failing with near-zero Bragg)
- Chi²/pixel metrics improve from initial to final

## Artifacts
- Metrics: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/db_at_028_metrics.json`
- Analysis: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T234500Z/root_cause_analysis.md`

## References
- ARCH-REFACTOR-001 Phase D.3 Batch 2 (CLI → Engine migration)
- ARCH-STAGE-CONTEXT-001 Phase D (terminal stage artifact reconstruction)
- GRADIENT-004 (Crystal warm cache retargeting)
