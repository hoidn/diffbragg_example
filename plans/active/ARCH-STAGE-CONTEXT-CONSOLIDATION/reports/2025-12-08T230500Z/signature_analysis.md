# ARCH-STAGE-CONTEXT-CONSOLIDATION Phase A: Signature Analysis

**Date:** 2025-12-08T230500Z
**Loop:** i=251
**Phase:** A (Analysis)

## Current Signatures

### Stage A: `_build_stage_a_params` (13 parameters)
```python
def _build_stage_a_params(
    self,
    crystal,           # DIALS crystal
    detector,          # DIALS detector
    inputs,            # DataLoad inputs
    config,            # RefinementConfig (already typed)
    device,            # torch.device
    dtype,             # torch.dtype
    hkl_grid,          # torch.Tensor
    hkl_metadata,      # Dict
    sigma_floor_sq_cache,  # Dict[device, Tensor]
    baseline_crystal,  # DIALS crystal (for reference)
    baseline_detector, # DIALS detector (for reference)
    beam               # DIALS beam
)
```

### Stage B: `_build_stage_b_params` (15 parameters)
```python
def _build_stage_b_params(
    self,
    device,
    dtype,
    stage_a_ctx,       # Optional[Dict] or StageAContext
    canonical_baseline,# Dict[str, Any]
    n_panels,
    sampled_panel_ids, # List[int]
    sigma_floor_sq_cache,
    use_stage_a_roi_mode,
    crystal,
    hkl_metadata,
    hkl_grid,
    detector,
    beam,
    inputs,
    panel_slices,      # List[Tuple[slice, slice]]
    context,           # Optional RefinementContext
)
```

### Stage C: `_build_stage_c_params` (to verify)
Similar pattern with 10+ parameters.

## Analysis

### Parameters Already in StageAContext
- device ✓
- dtype ✓
- hkl_grid ✓
- hkl_metadata ✓
- beam_config (equivalent to beam) ✓
- detector_configs (can derive detector) ✓

### Parameters NOT in StageAContext (need consolidation)
- crystal (DIALS crystal object)
- inputs (DataLoad object)
- sigma_floor_sq_cache (memoization dict)
- baseline_crystal (reference crystal for comparison)
- baseline_detector (reference detector)

### Proposed New Input Context

```python
@dataclass
class StageAInputContext:
    """Input parameters for Stage A LBFGS setup."""
    crystal: Any  # DIALS crystal
    detector: Any  # DIALS detector
    beam: Any  # DIALS beam
    inputs: Any  # DataLoad
    baseline_crystal: Any  # Reference crystal
    baseline_detector: Any  # Reference detector
    hkl_grid: torch.Tensor
    hkl_metadata: Dict[str, Any]
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor]
    device: torch.device
    dtype: torch.dtype
```

This would reduce Stage A signature from 13 params to 3: `self, config, input_ctx`

## Recommendation

**Phase B Scope:**
1. Create `StageAInputContext`, `StageBInputContext`, `StageCInputContext` dataclasses
2. Populate them in `StageA.run()` before calling `_build_stage_a_params()`
3. Update signature to `_build_stage_a_params(self, config, input_ctx)`
4. Repeat for Stage B/C

**Estimated Effort:** Medium (3-4 loops for full implementation)
**Risk:** Low (signature change is mechanical, tests provide safety net)
