# Phase C2.2 Complete CPU Fallback Fix — Planning Summary (Loop i=213)

**Date**: 2025-11-23T092000Z
**Focus**: ARCH-REFINE-FLOW-001 Phase C2.2 — Protocol-based Refinement Engine (Complete CPU fallback fix)
**Action Type**: ready_for_implementation
**Owner**: Galph (supervisor planning) → Ralph (engineer execution)

---

## Problem Statement

Ralph's loop i=212 partial CPU fallback fix correctly updated the **final Bragg reconstruction device** (line 3110: `device=final_device`), but **CUDA OOM persists** during **Stage B closure execution** (physics.py:79, tried to allocate 856 MiB, only 51.62 MiB free).

**Root Cause (HIGH confidence ~98%)**:
- Engine delegation path (lines 3036-3050) builds `engine_inputs` dict but **does NOT populate** `use_stage_b_cpu_fallback` or `stage_b_eval_stage_a_ctx` keys
- StageB.run() line 249 expects `use_stage_b_cpu_fallback` in param_values to switch device to CPU
- When missing, StageB defaults to CUDA execution → exhausts GPU memory during closure

---

## Complete Fix Required

### Location
Insert ~30 lines at **line 3047** (AFTER `engine_inputs = {...}` block ending line 3045, BEFORE `engine = RefinementEngine(...)` line 3050)

### Pattern to Replicate
Inline path CPU fallback + context cloning (lines 2171-2205):
1. Compute `use_stage_a_roi_mode` from panel_slices and config (lines 2171-2173)
2. Compute `use_stage_b_cpu_fallback` per PERF-WARM-011 (lines 2178-2182)
3. Clone Stage A context to CPU if fallback active per PERF-WARM-012 (lines 2186-2202)
4. **NEW**: Populate `engine_inputs` with both keys (this is what was missing!)

### Critical Insight
The two new keys (`use_stage_b_cpu_fallback`, `stage_b_eval_stage_a_ctx`) will be consumed by StageB.run() and passed to `_build_stage_b_params` which switches device to CPU and uses CPU-cloned Stage A context.

---

## Validation Strategy

### Tests (both MUST PASS)
1. Stage B full detector (`DBEX_SMOKE_DETECTOR_SIZE=full`) — primary validation
2. Stage B small detector regression guard — confirms no small detector regression

### Decision Tree
- **Path A** (both PASS): Complete CPU fallback SUCCESS → run DB-AT-024, Phase C validation complete
- **Path B** (full FAIL, small PASS): Debug device propagation in StageB.run() or _build_stage_b_params
- **Path C** (full PASS, small FAIL): Debug regression from CPU fallback conditional logic
- **Path D** (both FAIL): Escalate to shared implementation bug (device neutrality violation)

---

## Expected Outcomes

### Path A (SUCCESS - both tests PASS)
1. Stage B full detector test PASSES without CUDA OOM (runtime ~60-90s on CPU)
2. Stage B small detector regression guard PASSES (runtime ~13-20s)
3. Continue to DB-AT-024 mapping parity validation
4. Mark Phase C COMPLETE (exit criteria C3/C4/C5 met)

### Path B/C/D (BLOCKED)
1. Document specific device propagation failure in decision.md
2. Add debug print at dbex/refinement/stage_b.py:249 to verify `use_stage_b_cpu_fallback` value
3. Escalate to Galph for shared implementation layer review

---

## Findings Applied

- **PERF-WARM-011**: Stage B CPU fallback to avoid GPU OOM (lines 2178-2182 pattern)
- **PERF-WARM-012**: CPU Stage A context cloning for warm cache reuse (lines 2186-2205 pattern)
- **REFINE-008**: Stage B ≥3% improvement gate
- **PHYSICS-LOSS-001/002**: Variance-weighted loss + sigma_floor guard

---

## Key Differences from Loop i=212 Partial Fix

| Aspect | Loop i=212 (Partial) | Loop i=213 (Complete) |
|--------|---------------------|----------------------|
| **What was fixed** | Final Bragg device (line 3110) | engine_inputs plumbing (line 3047) |
| **When applied** | AFTER engine.run() | BEFORE engine.run() |
| **Scope** | Final Bragg reconstruction only | Entire Stage B closure execution |
| **Keys populated** | None (engine_inputs unchanged) | use_stage_b_cpu_fallback + stage_b_eval_stage_a_ctx |
| **StageB.run() behavior** | Defaults to CUDA (missing keys) | Switches to CPU (keys present) |
| **OOM location** | physics.py:79 (closure execution) | Expected: None (CPU execution) |

---

## Implementation Checklist

Ralph's tasks (6 steps per Do Now):
- [x] Review loop i=212 evidence (partial fix + OOM signature shift)
- [ ] Implement complete CPU fallback logic (~30 lines at line 3047)
- [ ] Rerun Stage B full detector test (MUST PASS)
- [ ] Rerun Stage B small detector regression guard (MUST PASS)
- [ ] Decision synthesis per 4-path template (create decision.md)
- [ ] Commit and push (with PASS/FAIL verdict)

---

## Reference Pointers

**Authoritative pattern** (inline path):
- `dbex/nanobrag_refinement.py:2171-2205` — CPU fallback + context cloning (EXACT pattern to replicate)

**Engine delegation path** (needs fix):
- `dbex/nanobrag_refinement.py:3036-3050` — MISSING CPU fallback, fix at line 3047

**StageB consumption**:
- `dbex/refinement/stage_b.py:249` — Expects `use_stage_b_cpu_fallback` in param_values

**Ralph's loop i=212 evidence**:
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/summary.md` — Partial fix
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_full_after_fix2.log` — OOM at physics.py:79

---

## Next Loop Preview

If both tests PASS (Path A):
1. Run DB-AT-024 mapping parity test
2. Update docs/fix_plan.md Attempts History (Phase C2.2 COMPLETE)
3. Mark Phase C exit criteria C3/C4/C5 satisfied
4. Galph plans Phase D next loop (Stage C extraction)

If any test FAILS (Path B/C/D):
1. Galph reviews device propagation failure
2. Escalate to shared implementation layer if needed
3. May require StageB.run() or _build_stage_b_params debugging
