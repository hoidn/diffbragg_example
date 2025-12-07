# Phase B.1 Analysis — Gradient Override Implementation & Test Results

**Loop**: Ralph i=139 (ARCH-GRADIENT-FLOW-001 Phase B.1)
**Date**: 2025-12-07T220000Z
**Objective**: Implement tensor-valued override mechanisms for detector distance and beam wavelength; validate with DB-AT-010 gradcheck tests.

---

## Executive Summary

**Implementation Status**: PARTIALLY COMPLETE
**Test Results**: 0/2 PASS (detector FAIL Jacobian mismatch, beam FAIL gradient break)
**Critical Blocker Found**: `nanobrag_torch.simulator.py:761` breaks beam wavelength gradient via `torch.tensor()` detachment
**Next Action**: BLOCKED — requires nanobrag_torch patch or escalation to blocked_pending_environment

---

## Implementation Summary

### Modules Touched (4 files, 85 LOC changed)

1. **dbex/physics/forward.py** (35 LOC)
   - Added `detector_overrides` and `beam_overrides` parameters to `simulate_forward_torch` signature (lines 85-86)
   - Updated docstring to document new override parameters (lines 113-118)
   - Implemented detector override extraction and propagation (lines 231-241)
   - Implemented beam override extraction and propagation (lines 184-188)

2. **dbex/refinement/config_factories.py** (10 LOC)
   - Added `wavelength_override` parameter to `create_beam_config` signature (line 234)
   - Updated docstring to document wavelength override (lines 249-250)
   - Implemented conditional logic to use wavelength override if provided (lines 257-260)
   - Note: `distance_mm_override` parameter already existed (line 52) but was incomplete

3. **tests/dbex/test_gradients.py** (40 LOC)
   - **test_db_at_010_gradcheck_detector_distance** (lines 379-401):
     - Removed manual `DxtbxDetector` construction (deleted 32 lines)
     - Added `detector_overrides` dict pattern (3 lines)
     - Updated `simulate_forward_torch` call with detector_overrides parameter
   - **test_db_at_010_gradcheck_beam_wavelength** (lines 467-489):
     - Removed manual `DxtbxBeam` construction (deleted 6 lines)
     - Added `beam_overrides` dict pattern (3 lines)
     - Updated `simulate_forward_torch` call with beam_overrides parameter

---

## Test Results

### Test 1: Detector Distance (test_db_at_010_gradcheck_detector_distance)

**Status**: FAILED (Jacobian mismatch)
**Runtime**: 48.20s
**Error Type**: `torch.autograd.gradcheck.GradcheckError`

**Error Signature**:
```
Jacobian mismatch for output 0 with respect to input 0,
numerical:tensor([[5.2385e+11]], dtype=torch.float64)
analytical:tensor([[1.1410e+08]], dtype=torch.float64)
```

**Analysis**:
- **Gradient flow RESTORED**: Analytical gradient is non-zero (1.14e8), confirming autograd graph connection
- **Magnitude error**: Analytical gradient is ~4590× smaller than numerical gradient
- **Hypothesis**: Possible unit conversion issue or tensor type coercion stripping gradient magnitude
- **Next Step**: Investigate `DetectorConfig` and `nanobrag_torch.simulator` for tensor handling

**Log**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_detector_distance_post_fix.log`

---

### Test 2: Beam Wavelength (test_db_at_010_gradcheck_beam_wavelength)

**Status**: FAILED (Gradient break)
**Runtime**: 28.52s
**Error Type**: `torch.autograd.gradcheck.GradcheckError`

**Error Signature**:
```
Numerical gradient for function expected to be zero
```

**Root Cause** (CONFIRMED):
```python
# nanobrag_torch/simulator.py:761
self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```

**Analysis**:
- **Gradient flow BROKEN**: `torch.tensor()` creates a new tensor, detaching from autograd graph
- **External dependency**: nanobrag_torch.simulator is NOT in dbex codebase (src/nanobrag-torch submodule)
- **Blocker classification**: blocked_pending_environment per input.md lines 186-188
- **Warning captured**: pytest logged `UserWarning: To copy construct from a tensor, it is recommended to use sourceTensor.clone().detach() or sourceTensor.clone().detach().requires_grad_(True), rather than torch.tensor(sourceTensor).`

**Recommended Fix** (for nanobrag_torch maintainer):
```python
# Replace line 761 with:
if isinstance(self.beam_config.wavelength_A, torch.Tensor):
    self.wavelength = self.beam_config.wavelength_A.to(device=self.device, dtype=self.dtype)
else:
    self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```

**Log**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_beam_wavelength_post_fix.log`

---

## Full DB-AT-010 Suite (Deferred)

**Status**: NOT RUN
**Rationale**: Per input.md lines 108-116, full suite regression check requires detector + beam tests passing. Since both detector and beam tests failed (different failure modes), running full suite would not provide actionable data at this time.

**Next Loop Decision**:
- IF detector Jacobian issue resolved → run full suite
- IF beam wavelength blocker persists → escalate to blocked_pending_environment

---

## Architectural Observations

### Pattern Consistency

**Crystal overrides** (existing, working):
- Implemented in `simulate_forward_torch` (lines 194-208)
- Uses direct field assignment: `crystal_config.cell_a = override_tensor`
- CrystalConfig accepts tensors directly ✓

**Detector/Beam overrides** (new, partially working):
- Implemented at config factory level (before config object creation)
- `create_detector_config` receives `distance_mm_override`, assigns to `distance_mm`
- `create_beam_config` receives `wavelength_override`, assigns to `wavelength_A`
- **Issue**: Downstream consumers (DetectorConfig, BeamConfig, simulator) may not handle tensors correctly

### Design Mismatch Hypothesis

**Crystal pattern** (post-creation override):
```python
crystal_config, _ = create_crystal_config(crystal, experiment)  # Create with scalars
if crystal_overrides:
    crystal_config.cell_a = crystal_overrides['cell_a']  # Override AFTER creation
```

**Detector/Beam pattern** (pre-creation override):
```python
# Override BEFORE config creation
if detector_overrides and 'distance_mm' in detector_overrides:
    distance_override = detector_overrides['distance_mm']
detector_config = create_detector_config(..., distance_mm_override=distance_override)
```

**Potential issue**: Config factories may perform type conversions or validations that strip gradients AFTER we pass the tensor.

**Recommendation for next loop**: If detector issue persists, consider switching to post-creation override pattern (matching crystal):
```python
detector_config = create_detector_config(panel, beam, trusted_mask)
if detector_overrides and 'distance_mm' in detector_overrides:
    detector_config.distance_mm = detector_overrides['distance_mm']
```

---

## LOC Metrics

| Module | Lines Added | Lines Removed | Net Change |
|--------|-------------|---------------|------------|
| dbex/physics/forward.py | 40 | 5 | +35 |
| dbex/refinement/config_factories.py | 10 | 0 | +10 |
| tests/dbex/test_gradients.py | 15 | 55 | -40 |
| **Total** | **65** | **60** | **+5** |

**Implementation complexity**: LOW (5 net LOC, mostly refactoring test harness)
**Test harness cleanup**: 55 LOC removed (manual geometry construction eliminated)

---

## Next Action Recommendation

**Option A** (Detector-only fix path):
1. Investigate DetectorConfig and simulator for tensor type coercion
2. If fixable within dbex scope → implement fix, re-run detector test
3. Mark beam wavelength as xfail with nanobrag_torch blocker documented
4. Deliverables: 1/2 tests PASS (detector), beam deferred to nanobrag_torch patch

**Option B** (Escalation path):
1. Mark ARCH-GRADIENT-FLOW-001 as `blocked_pending_environment`
2. Create minimal reproducer for nanobrag_torch maintainer (wavelength gradient break)
3. Document detector Jacobian issue as separate hypothesis requiring investigation
4. Deliverables: Blocker report + reproducer script

**Option C** (Alternative implementation):
1. Switch detector/beam overrides to post-creation pattern (match crystal pattern)
2. Assign tensor values AFTER config object creation (avoid factory type conversions)
3. Re-run both tests
4. Deliverables: Test if pattern alignment resolves both issues

**Recommended**: **Option C** (1 loop effort, highest probability of unblocking detector test; beam still blocked but approach aligns with working crystal pattern)

---

## References

- **Input spec**: `input.md` lines 66-90 (Do Now tasks)
- **Test logs**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_*.log`
- **Suspect audit**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/suspect_audit.md`
- **GRADIENT-001 finding**: `docs/findings.md` (tensor override pattern)
- **nanobrag_torch source**: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:761`

---

**Analysis authored**: 2025-12-07T220000Z (Loop i=139, Ralph)
**Phase**: ARCH-GRADIENT-FLOW-001 Phase B.1
**Status**: Implementation complete, tests FAIL with distinct failure modes (detector=Jacobian mismatch, beam=external gradient break)
