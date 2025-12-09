### Turn Summary
Threaded `pixel_batch_size` through all refinement engine call sites (Stage A/B/C, reconstruction). Stage A smoke passed with chunk_size=32 (128 caused OOM during reconstruction). Physics unchanged — partiality tests pass.
Next: Update fix_plan.md with completion status and commit changes.
Artifacts: plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/ (stage_a_pixel_batch_3.log, partiality_parity.log)

---

# PERF-GPU-MEM-001 Phase C Summary

**Date:** 2025-12-09T000000Z
**Loop:** i=241 (Ralph)
**Focus:** GPU Memory Usage Analysis and Optimization — Phase C (Optimization Verification)

## Problem Statement

OOM during Stage A smoke tests on 24GB GPUs due to full vectorization of detector simulation. The upstream `pixel_batch_size` feature was implemented in nanobrag_torch but needed threading through the DBEX refinement engine.

## Changes Made

### 1. RefinementConfig Field Added
**File:** `dbex/refinement/config.py:158-163`
```python
# GPU memory optimization (PERF-GPU-MEM-001)
# Number of detector rows to process per chunk in simulator.run().
pixel_batch_size: Optional[int] = None
```

### 2. Simulator.run() Call Sites Updated

Threaded `pixel_batch_size` through all refinement engine call sites:

| File | Line(s) | Context |
|------|---------|---------|
| `dbex/refinement/stage_a.py` | 439, 539, 1398 | Stage A closure (warm cache + cold path) |
| `dbex/refinement/reconstruction.py` | 435, 569, 1018, 1060 | Final Bragg reconstruction |
| `dbex/refinement/stage_a_utils.py` | 551, 646 | Shared panel loss helpers |
| `dbex/refinement/stage_b.py` | 1051, 1079, 1109 | Stage B evaluation |
| `dbex/refinement/stage_c.py` | 529, 1238 | Stage C microslip |

### 3. Test Updated
**File:** `tests/dbex/test_torch_refine_smoke.py:427-429`
```python
# PERF-GPU-MEM-001: Enable chunked execution to avoid OOM on 24GB GPUs
# Using 32 rows to account for tricubic interpolation overhead
pixel_batch_size=32,
```

## Test Results

### Stage A Smoke Test
- **Status:** PASSED
- **Chunk Size:** 32 rows (128 rows OOMed during reconstruction)
- **Duration:** 41.14s
- **Command:** `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small -v`

### Partiality Parity Tests
- **Status:** PASSED (2/2)
- **Configurations:** CPU and CUDA both passed
- **Duration:** 10.03s
- **Physics validation:** Unchanged

## Key Findings

1. **Recommended chunk size for 24GB GPUs is 32 rows**, not 128 as initially suggested by upstream docs
   - The tricubic interpolation has significant memory overhead beyond the base detector simulation
   - Reconstruction phase has higher memory requirements than LBFGS closure

2. **Feature is opt-in** — `pixel_batch_size=None` (default) uses full vectorization

3. **No physics changes** — partiality tests confirm identical results

## Artifacts

- `stage_a_pixel_batch.log` — First attempt (OOM at reconstruction:565)
- `stage_a_pixel_batch_2.log` — Second attempt (OOM at reconstruction:569 with chunking active)
- `stage_a_pixel_batch_3.log` — Third attempt (PASSED with chunk_size=32)
- `partiality_parity.log` — Physics parity validation

---

## Previous Turn Summary (Galph i=241)
Acknowledged ARCH-GRADIENT-FLOW-001 completion (Phase B.10, all 6 DB-AT-010 gradcheck tests PASS) and pivoted to PERF-GPU-MEM-001 Phase C.
Wrote input.md delegating pixel batching validation: thread `pixel_batch_size=128` through DBEX, run Stage A smoke, confirm OOM fix on 24GB GPU.
Next: Ralph implements Phase C — wire `pixel_batch_size` parameter, run smoke tests, validate physics unchanged.
Artifacts: plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/

## Focus Pivot Rationale

- ARCH-GRADIENT-FLOW-001: **done** (commit `10319760`, GRADIENT-004 finding added)
- Tier 0: Only blocked items remain (ARCH-SIM-CONSTRUCTION-001, ARCH-REFACTOR-001)
- Tier 1: DB-AT-SUITE-CARE-001 in maintenance mode (D.3/D.5 optional)
- Tier 3 PERF-GPU-MEM-001: Upstream `pixel_batch_size` feature ready; Phase C is next actionable

## Phase C Delegation

Tasks for Ralph:
1. C.1: Verify `pixel_batch_size` feature available in nanobrag_torch ✅
2. C.2: Thread `pixel_batch_size` through DBEX (CLI and/or API) ✅
3. C.3: Run Stage A smoke with `--smoke-detector-size=small` ✅
4. C.4: Validate physics unchanged (partiality tests) ✅
5. C.5: Document results in summary.md ✅

Expected outcome: Stage A smoke completes without OOM on 24GB GPU. ✅ ACHIEVED
