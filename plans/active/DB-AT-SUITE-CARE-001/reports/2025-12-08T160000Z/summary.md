### Turn Summary
Verified upstream nanobrag_torch response (`inbox/nanobrag_torch_response_2025_12_08.md`); fixes for wavelength/distance gradient flow are present in editable install.
Re-ran DB-AT-010 gradcheck suite: all 5/5 tests FAIL with Jacobian mismatches (~250×-120000× magnitude, sign flips) — upstream fixes resolved graph connectivity, but gradient correctness remains broken.
Next: Escalate gradient magnitude/sign issue to nanobrag_torch maintainers; ARCH-GRADIENT-FLOW-001 remains blocked.
Artifacts: plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T160000Z/ (summary.md)

---

# Loop i=189 Report — DB-AT-010 Gradient Verification

**Date:** 2025-12-08T160000Z
**Initiative:** ARCH-GRADIENT-FLOW-001, DB-AT-SUITE-CARE-001
**Focus:** Upstream response verification

## Upstream Response Received

File: `inbox/nanobrag_torch_response_2025_12_08.md`

### Issues Addressed by Upstream

1. **Wavelength gradient detachment** — FIXED (`as_tensor_preserving_grad()` helper)
2. **Detector distance gradient** — FIXED (converted to property)
3. **SQUARE lattice partiality** — Not a bug (DBEX expectation was wrong)

### Issues NOT Addressed

- **Crystal cell gradient magnitude mismatch** (~640× with sign flip) — NOT ADDRESSED
- The escalation in `inbox/to_nanobrag_gradient_magnitude_2025_12_07.md` was for crystal cell gradients, not wavelength/distance

## Verification Results

### Upstream Fixes Present in Editable Install

Confirmed present in `/home/ollie/Documents/nanoBragg/src/nanobrag_torch/`:
- `utils/tensor_utils.py` — `as_tensor_preserving_grad()` helper
- `models/detector.py:192` — `distance` property with DBEX-GRADIENT-001 comment

### DB-AT-010 Test Results

**Command:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k "DB_AT_010" --smoke-detector-size=full
```

**Results: 5/5 FAILED**

| Test | Numerical | Analytical | Ratio | Sign |
|------|-----------|------------|-------|------|
| crystal_cell_a | -2.04e+11 | 6.98e+07 | ~2900x | opposite |
| crystal_cell_gamma | 2.89e+11 | 4.64e+07 | ~6200x | opposite |
| detector_distance | -1.25e+12 | 1.04e+07 | ~120000x | opposite |
| beam_wavelength | 9.16e+11 | -3.62e+09 | ~250x | opposite |

### Analysis

1. **Graph connectivity: RESOLVED** — Gradients now exist (non-zero analytical values)
2. **Gradient correctness: BROKEN** — Analytical gradients don't match numerical
3. **Pattern:** All parameters show magnitude mismatch with sign flip

The upstream fixes addressed **tensor preservation** (no more disconnected graph error), but the **crystallographic/physics forward pass** produces incorrect analytical gradients.

## Status Updates

### ARCH-GRADIENT-FLOW-001

- **Status:** blocked_pending_upstream (unchanged)
- **Blocker:** Gradient magnitude/sign mismatch in crystallographic computations
- **Phase B.1:** Upstream integration confirmed; fixes are present
- **Phase B.2:** Gradcheck verification FAILED — deeper issue in physics computations

### DB-AT-SUITE-CARE-001

- **Status:** in_progress (maintenance mode)
- **D.1-D.4:** Complete
- **Gradient tests:** Still blocked

## Next Actions

1. **File follow-up escalation** to nanobrag_torch clarifying that the crystal cell gradient magnitude issue was NOT addressed
2. **Document** that wavelength/distance fixes didn't resolve the gradcheck failures
3. **ARCH-GRADIENT-FLOW-001** remains blocked until gradient correctness is fixed

## Artifacts

- This summary: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T160000Z/summary.md`
- Pytest output: captured in stdout (not persisted — test failed with detailed Jacobian mismatch)
