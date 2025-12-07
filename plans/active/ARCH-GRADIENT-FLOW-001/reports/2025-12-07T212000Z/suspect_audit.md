# Suspect Module Audit — Gradient Break Patterns

**Loop**: Ralph i=138 (ARCH-GRADIENT-FLOW-001 Phase A.2)
**Date**: 2025-12-07
**Objective**: Search high-risk gradient break patterns in 4 key production modules.

---

## Executive Summary

Audited 4 production modules (forward.py, crystallography.py, loss.py, inputs.py) for 6 gradient-breaking patterns. Found **0 UNSAFE patterns in production code**. All `.detach()` calls are intentional IRLS semantics or unused code paths. The **2 critical `.item()` gradient breaks are in the test harness** (test_gradients.py:383, :496). Crystal parameter tests may fail due to **external nanobrag_torch.models.Crystal constructor** breaking gradient (hypothesis).

---

## Summary Table

| Module | .item() | .detach() | .numpy() | inplace (*=, +=) | .cpu() | Total Unsafe |
|--------|---------|-----------|----------|------------------|--------|--------------|
| `dbex/physics/forward.py` | 0 | 0 | 0 | 0 | 0 | **0** |
| `dbex/geometry/crystallography.py` | 0 | 3 | 3 | 0 | 3 | **0** (unused code) |
| `dbex/physics/loss.py` | 2 | 2 | 0 | 0 | 0 | **0** (IRLS intentional) |
| `dbex/refinement/inputs.py` | 0 | 0 | 0 | 0 | 0 | **0** |
| **Production Total** | **2** | **5** | **3** | **0** | **3** | **0** |
| **Test Harness** | **2** | **0** | **0** | **0** | **0** | **2 UNSAFE** |

**Top Candidate**: Test harness `.item()` calls in detector_distance (line 383) and beam_wavelength (line 496) tests.

---

## Detailed Analysis

### Pattern 1: `.item()` Calls

#### Production Code Matches (2 total)

1. **dbex/physics/loss.py:51**
   ```python
   masked_pixels = int(mask_bool.sum().item())
   ```
   - **Context**: `_compute_variance_weighted_loss` internal function (lines 33-67)
   - **Classification**: **SAFE**
   - **Rationale**:
     - This function is NOT called by `compute_masked_mse_loss` (the function used by DB-AT-010 tests)
     - The `.item()` extracts a scalar count for telemetry, not a gradient-bearing tensor
     - Even if this path were active, masked_pixels is used for division (line 63) and doesn't flow backward through the computation graph

2. **dbex/physics/loss.py:52**
   ```python
   clamped_pixels = int(((variance_raw < sigma_floor_sq_tensor) & mask_bool).sum().item())
   ```
   - **Context**: Same as above, `_compute_variance_weighted_loss` internal function
   - **Classification**: **SAFE**
   - **Rationale**: Same as #1 (unused code path, telemetry extraction)

#### Test Harness Matches (2 total)

3. **tests/dbex/test_gradients.py:383**
   ```python
   def loss_fn(distance_tensor):
       new_distance = float(distance_tensor.item())
       distance_delta = new_distance - base_distance
       # ... build new_detector with scalar geometry ...
   ```
   - **Context**: `test_db_at_010_gradcheck_detector_distance` loss closure
   - **Classification**: **UNSAFE** — **CRITICAL GRADIENT BREAK**
   - **Hypothesis**: Test extracts scalar from tensor to construct non-differentiable dxtbx.model.Detector geometry object, severing autograd graph
   - **Fix**: Implement tensor-valued `distance_mm_override` mechanism in `create_detector_config` (similar to crystal_overrides pattern)

4. **tests/dbex/test_gradients.py:496**
   ```python
   def loss_fn(wavelength_tensor):
       new_wavelength = float(wavelength_tensor.item())
       # ... build new_beam with scalar wavelength ...
   ```
   - **Context**: `test_db_at_010_gradcheck_beam_wavelength` loss closure
   - **Classification**: **UNSAFE** — **CRITICAL GRADIENT BREAK**
   - **Hypothesis**: Test extracts scalar from tensor to construct non-differentiable dxtbx.model.Beam geometry object, severing autograd graph
   - **Fix**: Implement tensor-valued `wavelength_override` mechanism in `create_beam_config` (or modify test to use existing BeamConfig with tensor wavelength)

---

### Pattern 2: `.detach()` Calls

#### Production Code Matches (5 total, 2 in gradient path)

1-2. **dbex/physics/forward.py:92, :126**
   ```python
   # Line 92: docstring comment
   .detach().numpy() conversions. Designed for DB-AT-010 gradcheck acceptance

   # Line 126: docstring comment
   - Preserves gradient graph (no .detach() or .numpy() conversions)
   ```
   - **Classification**: **SAFE** (documentation text, not code)

3-5. **dbex/geometry/crystallography.py:122-124**
   ```python
   a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
   b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
   c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
   ```
   - **Context**: `compute_u_matrix` function (lines 56-138)
   - **Classification**: **SAFE**
   - **Rationale**:
     - `compute_u_matrix` is NOT called from any production code path (grep search returned 0 usages)
     - Function is utility code for U-matrix extraction (Stage A mapping), not used in gradient tests
     - Even if called, it's a geometry extraction utility that shouldn't be in the gradient path

6-7. **dbex/physics/loss.py:47, :147**
   ```python
   # Line 47 (_compute_variance_weighted_loss):
   variance_raw = bragg_tensor.detach() + sigma_tensor ** 2

   # Line 147 (compute_masked_mse_loss):
   variance = torch.clamp(prediction.detach() + sigma_readout**2, min=1e-12)
   ```
   - **Context**: Variance-weighted chi-squared loss computation
   - **Classification**: **SAFE** — **INTENTIONAL IRLS SEMANTICS**
   - **Rationale**:
     - Detaching the variance denominator is correct for IRLS (Iteratively Reweighted Least Squares)
     - Prevents "attraction to zero" numerical artifact per spec-db-core.md:82
     - Gradient still flows through the numerator: `d/dx[(x - target)^2 / variance.detach()] = 2*(x - target) / variance`
     - This is a standard technique in robust M-estimators and should NOT be changed

8-9. **dbex/physics/loss.py:82, :103, :145**
   ```python
   # Lines 82, 103, 145: docstring comments explaining detach semantics
   ```
   - **Classification**: **SAFE** (documentation text, not code)

---

### Pattern 3: `.numpy()` Calls

#### Production Code Matches (3 total, all in unused code)

1-3. **dbex/geometry/crystallography.py:122-124**
   ```python
   a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
   b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
   c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
   ```
   - **Classification**: **SAFE** (same as Pattern 2 #3-5, unused code path)

---

### Pattern 4: In-Place Multiplication `*=`

#### Production Code Matches (0 total)

Grep returned 1 line total (empty after headers), indicating no `*=` ops in audited modules.

---

### Pattern 5: In-Place Addition `+=`

#### Production Code Matches (0 total)

Grep returned 1 line total (empty after headers), indicating no `+=` ops in audited modules.

---

### Pattern 6: `.cpu()` Calls

#### Production Code Matches (3 total, all in unused code)

1-3. **dbex/geometry/crystallography.py:122-124**
   ```python
   a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
   b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
   c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
   ```
   - **Classification**: **SAFE** (same as Pattern 2 #3-5, unused code path)

---

## Additional Findings

### Suspected External Gradient Break

**Location**: `dbex/refinement/config_factories.py:413-415`
```python
if N_cells is None and ml_domain_size_ang is not None and ml_domain_size_ang > 0.0:
    # Extract scalar values from cell parameters (handle both float and tensor cases)
    a_val = float(a) if hasattr(a, 'item') else float(a)
    b_val = float(b) if hasattr(b, 'item') else float(b)
    c_val = float(c) if hasattr(c, 'item') else float(c)
```

- **Context**: `create_crystal_config` fallback N_cells computation
- **Classification**: **POTENTIALLY UNSAFE** (but gated)
- **Analysis**:
  - `float(a)` implicitly calls `a.item()` if `a` is a tensor, breaking gradient
  - However, this code path is only active when `N_cells is None AND ml_domain_size_ang is not None`
  - The test fixture (test_gradients.py:179) calls `create_crystal_config(crystal, experiment)` WITHOUT passing N_cells
  - forward.py:177-178 comment confirms "N_cells will be None anyway" for gradient testing
  - **Current Status**: Likely not the root cause, but should be guarded
  - **Recommendation**: Add guard to skip N_cells computation when cell parameters are tensors

### External Dependency Hypothesis

**Location**: `nanobrag_torch.models.crystal.Crystal.__init__`

- **Observation**: Crystal parameter tests (cell_a, cell_gamma) use the correct tensor-preserving `crystal_overrides` pattern, yet still fail gradcheck
- **Hypothesis**: The `nanobrag_torch.models.Crystal` constructor may internally call `.item()` on `CrystalConfig` cell parameter fields
- **Evidence**:
  - Test harness correctly passes tensor-valued `crystal_config.cell_a` to Crystal constructor (helpers.py:198)
  - No `.item()` calls in dbex code between test entry and Crystal instantiation
  - All 5 gradcheck tests fail with identical signature: "Numerical gradient for function expected to be zero"
  - This suggests the gradient graph is uniformly disconnected, not a partial break
- **Next Step**: Phase A.3 gradient probe to empirically test if Crystal.__init__ preserves gradient
- **Contingency**: If nanobrag_torch breaks gradient, mark ARCH-GRADIENT-FLOW-001 as `blocked_pending_environment` (per input.md Scenario 3)

---

## Top Candidate Root Cause

**Primary Fix** (Detector/Beam Tests):
- **File**: `tests/dbex/test_gradients.py`
- **Lines**: 383 (detector_distance), 496 (beam_wavelength)
- **Pattern**: `float(parameter_tensor.item())`
- **Hypothesis**: Test harness explicitly breaks gradient by extracting scalar from parameter tensor to construct non-differentiable dxtbx geometry objects
- **Fix Complexity**: **MEDIUM**
  - Option 1: Implement tensor-valued `distance_mm_override` in `create_detector_config` (20-30 LOC, follows existing crystal_overrides pattern)
  - Option 2: Modify test to use tensor-aware geometry construction (requires dxtbx API changes or wrapper)
- **Expected Impact**: Fixes 2/5 failing tests (detector_distance, beam_wavelength) immediately

**Secondary Investigation** (Crystal Tests):
- **File**: `nanobrag_torch/models/crystal.py` (external)
- **Hypothesis**: Crystal constructor may break gradient when hydrating cell parameters
- **Fix Complexity**: **BLOCKED** (external dependency, requires nanobrag_torch patch or workaround)
- **Expected Impact**: If confirmed, fixes remaining 3/5 failing tests (cell_a, cell_gamma, wrapper test)
- **Escalation**: If nanobrag_torch is root cause, escalate to maintainer or propose spec_change to relax gradcheck scope

---

## Validation Summary

✅ **Phase A.2 Deliverables Met**:
- 4 modules audited (forward.py, crystallography.py, loss.py, inputs.py)
- 6 grep patterns executed (item, detach, numpy, inplace_mul, inplace_add, cpu)
- 13 total grep matches analyzed (10 production + 3 test harness indirect via comments)
- SAFE vs UNSAFE classification complete
- Top candidate hypothesis identified (test harness .item() calls)

**Total Production Code UNSAFE Patterns**: **0**
**Total Test Harness UNSAFE Patterns**: **2** (both critical for detector/beam tests)

---

## Next Actions

1. **Phase B.1 Option A** (If detector/beam fixes are sufficient):
   - Implement tensor-valued `distance_mm_override` in `create_detector_config`
   - Implement tensor-valued `wavelength_override` in `create_beam_config` or test fixture
   - Fix test_gradients.py:383, :496 to use tensor overrides
   - Re-run DB-AT-010 gradcheck
   - If crystal tests still fail → proceed to Option B

2. **Phase A.3 Option B** (If crystal tests fail after harness fixes):
   - Write minimal gradient probe (<400 LOC) to test `nanobrag_torch.models.Crystal` constructor
   - Isolate whether cell_a tensor → Crystal.__init__ → simulator.run() preserves gradient
   - If gradient breaks in nanobrag_torch: mark blocked_pending_environment
   - If gradient preserved: investigate other potential breaks (misset_deg, mosflm_a_star hydration)

3. **Escalation Scenario**:
   - If both test harness AND nanobrag_torch break gradient: Fix test harness first (unblocks 2 tests), then escalate nanobrag_torch issue to maintainer with minimal reproducer from Phase A.3 probe

---

## References

- `dbex/physics/forward.py` — Forward simulation entry point
- `dbex/physics/loss.py` — Variance-weighted loss (IRLS semantics)
- `dbex/geometry/crystallography.py` — U-matrix utilities (unused in gradient path)
- `dbex/refinement/inputs.py` — Input preparation (numpy only, no torch)
- `dbex/refinement/config_factories.py` — Config hydration (potential N_cells break, gated)
- `tests/dbex/test_gradients.py` — DB-AT-010 gradcheck suite
- `docs/spec-db-runtime.md` §Gradient Hygiene
- `docs/findings.md::GRADIENT-001` — Tensor override pattern

---

**Prepared by**: Ralph (Loop i=138)
**Phase**: ARCH-GRADIENT-FLOW-001 Phase A.2
**Deliverable**: Grep audit with SAFE/UNSAFE classification and top candidate hypothesis
