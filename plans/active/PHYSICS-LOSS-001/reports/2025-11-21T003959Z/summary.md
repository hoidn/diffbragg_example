# PHYSICS-LOSS-001 Loop Summary (2025-11-21T003959Z)

## Problem Statement
Per spec-db-core.md:67, implement variance floor guard `V = max(I_model + sigma_readout^2, sigma_floor^2)` across Stage A/B/C to prevent infinite weights when I_model → 0 on GPU backends. Expose sigma_floor via CLI and emit telemetry covering floor value and clamp fraction.

## SPEC Lines Implemented
> spec-db-core.md:67: "A physical lower bound SHALL be enforced: V = max(I_model + sigma_readout^2, sigma_floor^2) where sigma_floor defaults to the instrument's published readout noise (≥ 1 photon or the ADU-equivalent) and is configurable via CLI. The clamp exists to prevent infinite weights when I_model → 0 on GPU backends; telemetry SHALL report sigma_floor and the fraction of pixels where the clamp engaged."

## Changes Delivered

### Core Logic (`dbex/nanobrag_refinement.py`)
1. **RefinementConfig** (lines 275-278): Added `sigma_floor_value: float = 1.0` field
2. **RefinementTelemetry** (lines 352-354): Added `variance_floor_value` and `variance_floor_clamp_fraction` fields
3. **Stage A loss** (lines 766-780): Replaced `torch.clamp(..., min=1.0)` with `torch.maximum(variance_raw, sigma_floor_sq)` + clamp pixel tracking
4. **Stage B loss** (lines 1327-1338): Applied same variance floor formula + clamp tracking
5. **Stage C loss** (lines 1733-1745): Applied same variance floor formula + clamp tracking
6. **Stage A telemetry** (lines 1123-1127): Populated `variance_floor_value` and `variance_floor_clamp_fraction`
7. **Stage B telemetry** (lines 1582-1586): Populated `variance_floor_value` and `variance_floor_clamp_fraction`
8. **Stage C telemetry** (lines 1970-1974): Populated `variance_floor_value` and `variance_floor_clamp_fraction`

### CLI Integration (`dbex/refine_one.py`)
1. **Argument parser** (lines 84-93): Added `--sigma-floor` flag (default 1.0, in target units)
2. **ADU→photon conversion** (lines 411-420): Divides sigma_floor by adu_per_photon when gain is active
3. **Config plumbing** (line 420): Passes `sigma_floor_value` to RefinementConfig

### HDF5 Schema (`dbex/refine_one.py`)
1. **Per-stage groups** (lines 634-638): Write `variance_floor_value` and `variance_floor_clamp_fraction` attrs to `/torch_diagnostics/stage_{A,B,C}`
2. **Legacy top-level** (lines 687-691): Write variance floor attrs to `/torch_diagnostics` for Stage A backward compatibility

## Test Results

**Passing (2/4):**
- ✅ `test_stage_a_expansion` (14.47s): Stage A smoke passed; variance floor telemetry correct
- ✅ `test_torch_diagnostics_metadata` (0.93s): HDF5 schema backward-compatible; new attrs present

**Failing (2/4):**
- ❌ `test_stage_b_shell_modifiers`: NaN/Inf gradient on iteration 0; chi2=2.47e11, clamp_fraction=0.0
- ❌ `test_stage_c_detector_microslip`: Stage C chi2 exploded to 3.02e8 (vs Stage A final 8.09e3); -3728434% "improvement"

## Root Cause Analysis (Failures)

The Stage B/C failures show numerically unstable chi-squared values. Per input.md, sigma-floor was meant to stabilize the GPU path, but the failures suggest either:
1. **Pre-existing GPU divergence**: Tests may have had latent instability that this change exposed
2. **torch.maximum vs torch.clamp semantics**: Subtle difference in gradient behavior or broadcasting
3. **Tensor creation inside gradient context**: `sigma_floor_sq = torch.tensor(config.sigma_floor_value**2, device, dtype)` created per-call may inadvertently track gradients

### Evidence
- Stage B error message: "NaN/Inf gradient detected in Stage B parameter tensor([-0.5000, ...], requires_grad=True)"
- `variance_floor_clamp_fraction=0.0` → floor not engaged, so massive loss isn't due to clamping; issue is upstream
- Stage A passes → Stage A's simpler tensor structure or lack of shell modifiers avoids the issue

## Next Actions (If Blocked)
1. Unit-test `torch.maximum(x, torch.tensor(1.0))` vs `torch.clamp(x, min=1.0)` equivalence
2. Pre-compute `sigma_floor_sq` as Python float outside closure: `sigma_floor_sq_val = config.sigma_floor_value ** 2.0`
3. Use scalar directly in `torch.maximum(variance_raw, sigma_floor_sq_val)` or create tensor once outside loop
4. Check git history: were Stage B/C tests previously marked xfail on CUDA?

## Artifacts
- pytest_stage_a.log (passed)
- pytest_stage_b.log (failed: NaN gradient)
- pytest_stage_c.log (failed: loss explosion)
- pytest_cli_diag.log (passed)

## Code Pointers
- Stage A variance guard: `dbex/nanobrag_refinement.py:766-772`
- Stage B variance guard: `dbex/nanobrag_refinement.py:1327-1331`
- Stage C variance guard: `dbex/nanobrag_refinement.py:1733-1738`
- CLI sigma-floor arg: `dbex/refine_one.py:84-93`
- HDF5 schema ext: `dbex/refine_one.py:634-638, 687-691`

