### Turn Summary

Processed upstream response `inbox/nanobrag_torch_response_2025_12_08.md` which addresses gradient DETACHMENT (wavelength/distance) but NOT the magnitude mismatch. Re-ran DB-AT-010 gradcheck suite: 5/5 FAILED with Jacobian mismatch — confirming gradient flow IS connected now but magnitudes differ ~1000-40000×. The upstream fixes (`as_tensor_preserving_grad`, detector distance property) are confirmed in `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`. Crystal cell_a gradient magnitude escalation remains unaddressed pending upstream.

Next: Document this in fix_plan.md; upstream must address crystal/detector/beam gradient magnitude discrepancies before DB-AT-010 can pass.

Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T160000Z/ (pytest_db_at_010.log)

---

## Upstream Response Analysis (2025-12-08T160000Z, Loop i=189, Ralph)

### Response Received
- **File**: `inbox/nanobrag_torch_response_2025_12_08.md`
- **Date**: 2025-12-08
- **Topics Addressed**:
  1. Gradient detachment (wavelength, fluence, distance) — **FIXED**
  2. SQUARE lattice partiality — **Not a bug** (DBEX expectation incorrect)

### Verified Fixes in Runtime nanobrag_torch

The upstream fixes are confirmed present in `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`:

| Fix | Files | Status |
|-----|-------|--------|
| `as_tensor_preserving_grad()` | tensor_utils.py, simulator.py, detector.py | ✅ Present |
| `distance` as property | detector.py:191-192 | ✅ Present |

### DB-AT-010 Gradcheck Results

**Test Run**: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py -k "DB_AT_010" --smoke-detector-size=full`

**Results**: 5/5 FAILED

| Test | Numerical | Analytical | Magnitude Ratio |
|------|-----------|------------|-----------------|
| crystal_cell_a | 1.12e+11 | 6.97e+07 | ~1613× |
| crystal_cell_gamma | 2.52e+11 | 4.59e+07 | ~5490× |
| detector_distance | 4.36e+11 | 1.06e+07 | ~41000× |
| beam_wavelength | 1.62e+12 | -3.63e+09 | ~445× (sign flip) |

### Key Finding

**Gradient DETACHMENT is fixed; gradient MAGNITUDE mismatch persists.**

The previous failure signature was "disconnected autograd graph" (analytical gradients = 0/None). Now we observe:
- Analytical gradients ARE non-zero (graph is connected)
- Numerical gradients exist (finite difference sensitivity confirmed)
- Magnitude mismatch: ~1000-40000× difference
- Sign relationship: wavelength shows opposite sign

This confirms:
1. Upstream's detachment fixes (wavelength/fluence/distance) are effective at restoring graph connectivity
2. The escalation `inbox/to_nanobrag_gradient_magnitude_2025_12_07.md` correctly identifies a DIFFERENT blocker
3. DB-AT-010 remains blocked until upstream addresses gradient magnitude issues

### Upstream Response Gap

The response addresses issues from **earlier escalation** (gradient detachment), NOT the **current escalation** (gradient magnitude mismatch). The current blocker was sent AFTER the response was authored:

| Artifact | Timestamp | Issue |
|----------|-----------|-------|
| Response | 2025-12-07 18:38 | Detachment (wavelength/distance) |
| Escalation | 2025-12-07 21:27 | Magnitude mismatch (crystal cell_a) |

The magnitude escalation remains pending.

### Status

- **ARCH-GRADIENT-FLOW-001**: `blocked_pending_upstream`
- **Blocker**: Gradient magnitude mismatch in nanobrag_torch crystallographic/detector/beam gradient computation
- **Evidence**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T160000Z/pytest_db_at_010.log`
