# Option C Implementation Summary — Loop i=140

**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration)
**Timestamp**: 2025-12-07T230000Z
**Actor**: Ralph
**Branch**: integration

---

## Modules Touched

### 1. `dbex/refinement/config_factories.py`
**Lines removed**: 21
**Changes**:
- Removed `wavelength_override` parameter from `create_beam_config` signature (line 234)
- Removed wavelength override docstring and conditional logic (lines 249-250, 257-260)
- Removed `distance_mm_override` parameter from `create_detector_config` signature (line 52)
- Removed distance override docstring and conditional logic (lines 74-75, 114-120)

**Pattern**: Restored scalar-only factory contract (ARCH-ENGINE-002)

### 2. `dbex/physics/forward.py`
**Lines added**: 37
**Lines removed**: 17
**Net**: +20 lines
**Changes**:
- Removed pre-creation beam override extraction logic (lines 184-188)
- Added post-creation beam override logic after `create_beam_config` call (lines 186-189)
- Removed pre-creation detector override extraction logic (lines 232-236, 242 param)
- Added post-creation detector override logic after `create_detector_config` call (lines 239-242)
- Updated docstring for detector/beam_overrides parameters to clarify "Applied AFTER config creation" (lines 109-121)

**Pattern**: Symmetrical with crystal_overrides post-creation pattern (lines 194-221)

---

## LOC Metrics

- **config_factories.py**: -21 lines (removed override parameters and conditional logic)
- **forward.py**: +20 lines (refactored from pre-creation extraction to post-creation assignment)
- **Total net**: -1 line (code simplification, better separation of concerns)

---

## Git Diff Snippets

### config_factories.py — Beam Config Signature
```diff
-def create_beam_config(beam, flux=None, beamsize_mm=None, exposure=None, wavelength_override: Optional['torch.Tensor'] = None) -> BeamConfig:
+def create_beam_config(beam, flux=None, beamsize_mm=None, exposure=None) -> BeamConfig:
```

### config_factories.py — Wavelength Extraction
```diff
-    # Wavelength (config_crosswalk.md:46)
-    # Allow gradcheck to override wavelength with differentiable tensor (GRADIENT-001)
-    if wavelength_override is not None:
-        wavelength_A = wavelength_override
-    else:
-        wavelength_A = beam.get_wavelength()
+    # Wavelength (config_crosswalk.md:46)
+    wavelength_A = beam.get_wavelength()
```

### config_factories.py — Detector Config Signature
```diff
 def create_detector_config(
     panel,
     beam,
     trusted_mask: Optional[np.ndarray] = None,
-    distance_mm_override: Optional['torch.Tensor'] = None,
     roi_bbox: Optional[Tuple[int, int, int, int]] = None,
     oversample: int = -1,
 ) -> DetectorConfig:
```

### config_factories.py — Distance Extraction
```diff
-    # Distance (config_crosswalk.md:28)
-    # Allow Stage C to override distance with differentiable tensor (TORCH-REFINE-003)
-    if distance_mm_override is not None:
-        # distance_mm_override is a torch.Tensor; extract scalar value or use directly
-        # DetectorConfig expects a Python float, so we need to handle tensor→scalar conversion
-        distance_mm = distance_mm_override
-    else:
-        distance_mm = panel.get_directed_distance()
+    # Distance (config_crosswalk.md:28)
+    distance_mm = panel.get_directed_distance()
```

### forward.py — Beam Override Refactor
```diff
-    # Prepare configs (shared across panels where applicable)
-    # Extract beam_overrides for wavelength tensor support (GRADIENT-001)
-    wavelength_override = None
-    if beam_overrides is not None and 'wavelength_A' in beam_overrides:
-        wavelength_override = beam_overrides['wavelength_A']
-    beam_config = create_beam_config(beam, wavelength_override=wavelength_override)
+    # Prepare configs (shared across panels where applicable)
+    beam_config = create_beam_config(beam)
+
+    # Apply beam overrides (post-creation pattern matching crystal_overrides)
+    # This preserves gradient flow by assigning tensor values AFTER config creation
+    if beam_overrides is not None and 'wavelength_A' in beam_overrides:
+        beam_config.wavelength_A = beam_overrides['wavelength_A']
```

### forward.py — Detector Override Refactor
```diff
     for panel_id in range(n_panels):
         panel = detector[panel_id]

-        # Extract detector_overrides for distance tensor support (GRADIENT-001)
-        distance_override = None
-        if detector_overrides is not None and 'distance_mm' in detector_overrides:
-            distance_override = detector_overrides['distance_mm']
-
         # Create detector config for this panel
         detector_config = create_detector_config(
             panel=panel,
             beam=beam,
-            trusted_mask=inputs.trusted_mask[panel_id],
-            distance_mm_override=distance_override
+            trusted_mask=inputs.trusted_mask[panel_id]
         )
+
+        # Apply detector overrides (post-creation pattern matching crystal_overrides)
+        # This preserves gradient flow by assigning tensor values AFTER config creation
+        if detector_overrides is not None and 'distance_mm' in detector_overrides:
+            detector_config.distance_mm = detector_overrides['distance_mm']
```

---

## Pattern Comparison: Pre-creation (i=139) vs Post-creation (i=140)

### i=139 Pattern (REJECTED)
1. **Extract** override value from dict into local variable
2. **Pass** local variable as factory parameter
3. **Conditional** inside factory assigns override OR dxtbx scalar
4. **Config created** with final value

**Issue**: Factory signature pollution with test-specific parameters; violates ARCH-ENGINE-002 scalar extraction contract

### i=140 Pattern (IMPLEMENTED, matches crystal_overrides)
1. **Create** config with dxtbx scalars only (factory remains clean)
2. **Assign** tensor value directly to config object field AFTER creation
3. **Gradient graph** preserved by post-creation assignment (no intermediate conversions)

**Alignment**: Matches crystal_overrides lines 194-221 (reference implementation)

---

## Test Results

### Detector Distance Gradcheck
**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_detector_distance \
  --smoke-detector-size=full
```

**Result**: **FAILED**
**Signature**: Jacobian mismatch
- Numerical gradient: `2.3861e+12`
- Analytical gradient: `1.1066e+08`
- Ratio: ~21,556× mismatch

**Comparison to i=139**:
- i=139 numerical: `2.2893e+12`
- i=139 analytical: `1.1066e+08`
- i=140 numerical: `2.3861e+12`
- i=140 analytical: `1.1066e+08` (IDENTICAL)

**Conclusion**: Post-creation pattern did NOT resolve Jacobian mismatch. Failure signature unchanged.

### Beam Wavelength Gradcheck
**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_beam_wavelength \
  --smoke-detector-size=full
```

**Result**: **FAILED** (EXPECTED)
**Signature**: "Numerical gradient for function expected to be zero"
**Root cause**: External blocker at `nanobrag_torch.simulator.py:761`
```python
self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```
**Issue**: `torch.tensor()` detaches gradient graph (should use `.clone()` for tensor inputs)

**Status**: Out of scope for this initiative (environment freeze, nanobrag_torch external dependency)

---

## Hypothesis Evaluation

### Initial Hypothesis (Galph i=139 analysis)
**Claim**: Pre-creation pattern causes gradient detachment because factory parameter conversions strip `requires_grad`

**Test**: Implement post-creation pattern (Option C) symmetrical to crystal_overrides

**Result**: **HYPOTHESIS REJECTED**
- Detector gradient flow still broken (same Jacobian mismatch magnitude)
- Pattern change from pre-creation to post-creation had NO effect on gradcheck outcome

### New Hypothesis (Ralph i=140)
**Claim**: Detector distance gradient issue is NOT in the override mechanism but in nanobrag_torch DetectorConfig field handling OR simulator distance sensitivity calculation

**Evidence**:
1. Analytical gradient is STABLE across i=139 and i=140 (1.1066e+08) — autograd graph IS connected
2. Numerical gradient changes slightly (2.29e+12 → 2.39e+12) — finite difference computation is stable
3. Ratio ~10^4 mismatch suggests **gradient magnitude error**, not disconnection
4. Crystal overrides work (tests pass per input.md) — same post-creation pattern, different config field

**Next debug path** (if unblocked):
- Investigate DetectorConfig.distance_mm field assignment behavior in nanobrag_torch
- Check if distance_mm participates in simulator physics calculations with correct derivative chain
- Compare with crystal cell parameter gradient flow (working reference)

---

## Architecture Conformance

### ARCH-ENGINE-002 (Config Factory Scalar Extraction)
**Status**: ✅ RESTORED
**Evidence**: Factory signatures reverted to pre-i=139 state; no tensor parameters remain

### GRADIENT-001 (Gradient Test Tensor Override Pattern)
**Status**: ⚠️ IMPLEMENTED BUT NOT VALIDATED
**Evidence**: Post-creation override pattern matches crystal_overrides structure; detector test still fails (unrelated root cause)

---

## Artifacts

- `pytest_detector_distance_option_c.log` — Full gradcheck failure output
- `pytest_beam_wavelength_option_c.log` — External blocker confirmation
- `option_c_implementation_summary.md` — This document

---

## Recommendation

**Mark ARCH-GRADIENT-FLOW-001 as `blocked_pending_environment`**

**Rationale**:
1. Option C refactor (post-creation pattern) implemented correctly but did NOT resolve detector gradient issue
2. Failure signature identical to i=139 (hypothesis invalidated)
3. Issue likely in nanobrag_torch DetectorConfig/simulator distance gradient handling (external dependency)
4. Beam wavelength blocker confirmed external (nanobrag_torch.simulator.py:761)
5. Both geometry parameter gradients fail; crystal parameters work (suggests nanobrag_torch-specific issue)

**Deliverables for escalation** (per input.md "If Blocked" section):
1. Minimal reproducer for nanobrag_torch maintainer ✅ (test harness already minimal)
2. Document issues in `docs/findings.md` (GRADIENT-003 detector, GRADIENT-004 beam)
3. Update `docs/fix_plan.md` ARCH-GRADIENT-FLOW-001 status: blocked_pending_environment
4. Update galph_memory.md with escalation rationale

**Alternative**: If environment unfreeze permitted, patch nanobrag_torch.simulator.py:761 to use `.clone()` instead of `torch.tensor()` for beam wavelength (targeted bugfix exception per CLAUDE.md)
