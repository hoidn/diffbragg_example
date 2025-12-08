# ARCH-GRADIENT-FLOW-001 Loop i=153 Summary

## Turn Summary

Applied upstream nanobrag_torch gradient fixes from inbox/from_nanobragg.md: (1) created `as_tensor_preserving_grad` utility, (2) updated Simulator to use gradient-preserving patterns for wavelength/fluence/kahn_factor, (3) converted Detector.distance/pixel_size/close_distance to properties enabling post-creation override pattern.
Authored enforcement tests in `tests/architecture/test_gradient_contracts.py` (5 tests, all PASS) validating gradient flow through nanobrag_torch Simulator and Detector.
DB-AT-010 shows partial progress: beam_wavelength analytical gradient now non-zero (-4.13e10), but full gradcheck still fails due to DBEX-layer detachments in crystal_overrides/detector_overrides paths.
Next step: DBEX-layer gradient fixes to thread tensor values through simulate_forward_torch → create_unified_simulator → Crystal/Detector construction (separate initiative scope).

Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z/gradcheck_verification_post_fix.log`, `tests/architecture/test_gradient_contracts.py`

## Problem & SPEC/ARCH Alignment

- **Problem:** DB-AT-010 gradcheck tests failing because gradient flow broken at torch.tensor() calls
- **SPEC alignment:** inbox/from_nanobragg.md (DBEX-GRADIENT-001) prescribes `as_tensor_preserving_grad` pattern
- **Initiative type:** architecture (arch_conformance)
- **ActionType:** implementation_ready per input.md

## Search & Existing Implementation Summary

- inbox/from_nanobragg.md describes upstream fix with 4 patterns
- nanobrag_torch.utils.tensor_utils.py did not exist (created)
- Simulator.__init__ used torch.tensor() for wavelength/fluence/kahn_factor (fixed)
- Detector stored distance/pixel_size as instance variables in __init__ (converted to properties)

## Code Analysis Performed

- simulator.py:761-777 — wavelength/fluence/kahn_factor tensor creation
- detector.py:61-69 — distance/pixel_size/close_distance instance variable assignments
- DBEX forward.py:186-245 — detector_overrides/beam_overrides/crystal_overrides wiring

## Changes Made

1. **New file:** `src/nanobrag-torch/src/nanobrag_torch/utils/tensor_utils.py`
   - `as_tensor_preserving_grad(x, device, dtype)` function
   - Uses `.to()` for tensors to preserve grad, `torch.tensor()` for scalars

2. **Modified:** `src/nanobrag-torch/src/nanobrag_torch/utils/__init__.py`
   - Added import and export for `as_tensor_preserving_grad`

3. **Modified:** `src/nanobrag-torch/src/nanobrag_torch/simulator.py`
   - Line 17: Import `as_tensor_preserving_grad`
   - Line 762-763: wavelength uses gradient-preserving pattern
   - Line 771-772: fluence uses gradient-preserving pattern
   - Line 775-777: kahn_factor uses gradient-preserving pattern

4. **Modified:** `src/nanobrag-torch/src/nanobrag_torch/models/detector.py`
   - Line 15: Import `as_tensor_preserving_grad`
   - Lines 58-71: Removed instance variable assignments, added _close_distance_cached
   - Lines 990-1049: Added property definitions for distance, pixel_size, close_distance

5. **New file:** `tests/architecture/test_gradient_contracts.py`
   - 5 enforcement tests validating gradient flow contracts

6. **Modified:** `pyproject.toml`
   - Registered `architecture` pytest mark

## Tests and Static Checks

```
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/architecture/test_gradient_contracts.py
# 5 passed

KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k DB_AT_010
# 5 failed (expected — DBEX-layer work remains)
```

## Docs & Ledgers Updates

- **docs/findings.md:** Added GRADIENT-002 entry documenting upstream fix integration
- **docs/development/TEST_SUITE_INDEX.md:** Added ARCH-GRADIENT-FLOW-001 test entry
- **docs/fix_plan.md:** Updated initiative status to "partial"

## Next Step

DBEX-layer gradient fixes: Thread tensor values through `simulate_forward_torch` → `create_unified_simulator` → `Crystal`/`Detector` construction, ensuring `crystal_overrides` and `detector_overrides` maintain gradient graphs through the entire forward path.
