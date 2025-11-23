### Turn Summary
Reviewed Ralph's Phase C validation evidence showing Stage B small detector PASSED but full detector FAILED with CUDA OOM (tried to allocate 1.67 GiB, only 49.62 MiB free).
Root cause identified with HIGH confidence (95%): engine delegation path (lines 3029-3048) missing CPU fallback initialization logic required by PERF-WARM-011/012.
Authored targeted 8-task Do Now for Ralph to implement CPU fallback fix (add 8-12 lines before engine instantiation), rerun Stage B full/small detector smokes + DB-AT-024 mapping parity, verify telemetry shows CPU fallback active.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/ (input.md, summary.md)

---

## Loop i=211 Review Summary

**Objective:** Review Ralph's Phase C validation execution and plan CPU fallback fix.

**Ralph's Evidence (Loop i=211):**
- **Stage B small detector**: PASSED (13.45s) - validates engine delegation core logic works
- **Stage B full detector**: FAILED - CUDA OOM (tried to allocate 1.67 GiB, GPU has only 49.62 MiB free)
- **DB-AT-024**: Collection check PASSED (1 test collected), execution deferred until Stage B fixed
- **Root cause analysis**: Excellent diagnosis in `phase_c_decision.md` with HIGH confidence (~95%)

**Root Cause (Confirmed):**
Engine delegation path (`dbex/nanobrag_refinement.py:3029-3108`) is MISSING CPU fallback initialization logic required by findings PERF-WARM-011 and PERF-WARM-012.

**Evidence:**
1. Inline path (lines 2174-2203) correctly implements CPU fallback:
   - Computes `use_stage_a_roi_mode` from Stage A context
   - Computes `use_stage_b_cpu_fallback = (config.stage_b_full_eval_on_cpu AND device=cuda AND not use_stage_a_roi_mode)`
   - Clones Stage A context to CPU device when fallback active (PERF-WARM-012)
   - Passes CPU context to Stage B helpers

2. Engine delegation path (lines 3029-3108):
   - Does NOT compute `use_stage_b_cpu_fallback`
   - Does NOT clone Stage A context to CPU
   - Stage B tries to allocate full-panel tensors on GPU → CUDA OOM

3. StageB.run() (dbex/refinement/stage_b.py:249):
   - Already correctly consumes `use_stage_b_cpu_fallback` from param_values
   - Fix only needs to wire the CPU fallback logic in engine delegation path

**Fix Strategy:**
Targeted 8-12 line addition before engine instantiation (line 3048):
1. Compute `use_stage_a_roi_mode` from context
2. Compute `use_stage_b_cpu_fallback` per PERF-WARM-011 pattern
3. If CPU fallback active: build fresh CPU Stage A context using `_build_stage_a_context(..., device=cpu)`
4. Add CPU context to `engine_inputs` dict for StageB consumption

**Fix Complexity**: LOW
- Pattern already proven in inline path (lines 2174-2203)
- No new abstractions needed
- No StageB.run() changes required (already consumes CPU context correctly)
- Localized change (8-12 lines in one location)

**Validation Plan:**
Ralph will execute 3-test validation suite:
1. Stage B full detector smoke (MUST PASS - primary validation)
2. Stage B small detector smoke (MUST PASS - regression guard)
3. DB-AT-024 mapping parity (MUST PASS - confirms no regression)

**Expected Outcome:**
Path A (HIGH confidence ~85%):
- All 3 tests PASS
- Telemetry shows `stage_b_full_eval_on_cpu=True` + `cache_mode="warm"`
- Phase C exit criteria met (C3/C4/C5 complete)
- Phase C marked COMPLETE (2025-11-23T090000Z)
- Next loop: Galph plans Phase D (Stage C extraction)

**Dwell Status:**
- Last loop: planning (validation Do Now)
- This loop: ready_for_implementation (CPU fallback fix)
- Dwell = 0 (consecutive non-implementation count reset)

**Findings Applied:**
- PERF-WARM-011: Stage B CPU fallback for full-panel runs (canonical detector OOM mitigation)
- PERF-WARM-012: Clone Stage A warm cache to CPU when fallback active
- REFINE-008: Stage B ≥3% improvement gate
- PHYSICS-LOSS-001/002: Variance-weighted loss + sigma_floor guard

**Artifacts Created:**
- `input.md` — 8-task Do Now with CPU fallback fix instructions, test commands, decision tree
- `summary.md` — This file (Turn Summary + loop review)

**Next Actions:**
Ralph implements CPU fallback fix, reruns validation suite, updates docs/fix_plan.md with results. If all tests PASS → Phase C COMPLETE. If blocked → Ralph documents blocker → Galph reviews.
