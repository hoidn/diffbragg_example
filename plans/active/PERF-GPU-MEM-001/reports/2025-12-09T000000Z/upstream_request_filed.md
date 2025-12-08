# Upstream Request Filed — PERF-GPU-MEM-001

**Date:** 2025-12-09
**Loop:** i=211
**Actor:** Galph

## Request Details

**File:** `~/Documents/nanoBragg/inbox/chunked_interpolation_request_2025_12_09.md`
**Priority:** MEDIUM
**Blocks:** PERF-GPU-MEM-001 Phase C (Optimization)

## Summary

Requested chunked tricubic interpolation from nanobrag_torch maintainers to address OOM during Stage A reconstruction.

### Key Points

1. **Root Cause:** `Crystal._tricubic_interpolation()` batches ALL query points (B=9.4M for small detector), creating 2.4 GB sub_Fhkl tensor + ~10 GB autograd overhead = ~23 GB peak

2. **Proposed Fix:** Process query points in chunks of ~100K instead of all at once

3. **Expected Impact:** 94× peak memory reduction (from 2.4 GB to ~25 MB per chunk)

## Next Steps

Await upstream response. When response received:
- If fix provided: Unblock PERF-GPU-MEM-001 Phase C
- If alternative solution: Evaluate and update implementation plan
- If declined: Consider local patch under Environment Freeze exception rules
