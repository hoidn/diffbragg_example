# Phase C2.3 Minimal CPU Bragg Reproducer — Decision Synthesis

## Executive Summary

**Result: PASS (Path A)**

The minimal CPU Bragg reproducer confirms the bug is **NOT in nanobrag_torch simulator** but in **dbex warm cache or context cloning logic**.

## Reproducer Result

**Test**: Standalone CPU StageAContext with canonical refGeom.expt parameters + single-panel simulation

**Outcome**: **PASS** — Bragg output is non-zero on CPU

**Bragg Stats**:
- Shape: [2527, 2463] (6.22M pixels)
- Min: 0.0
- Max: 0.086054
- Mean: 0.002702
- Nonzero count: 6,161,997 / 6,224,001 (99.00%)

**Crystal Parameters (reproduced correctly)**:
- cell_a=27.376, cell_b=32.066, cell_c=34.466
- cell_alpha=88.769°, cell_beta=71.630°, cell_gamma=68.189°
- Device: cpu
- Dtype: torch.float32

## Decision Path Analysis

### Path A (PASS — Bragg max > 0) ✅ SELECTED

**Verdict:** Bug is in dbex warm cache or context cloning, NOT nanobrag_torch.

**Evidence:**
1. Standalone CPU context produces **non-zero Bragg intensities** (99% coverage)
2. 100% parameter parity confirmed in loop i=219 (CUDA vs CPU crystal configs EXACT match)
3. Full test fails with zero Bragg on CPU, but reproducer succeeds → issue is in dbex Stage B context management

**Root Cause Hypothesis (HIGH confidence ~85%):**
The CPU fallback path in Stage B (lines 2234-2246 `_build_stage_a_context` call) correctly builds the context, but something in the **Stage B closure or warm-cache reuse** breaks the HKL grid or crystal state on CPU.

**Potential Specific Causes:**
1. **HKL grid device transfer during Stage B shell modifier application** (lines 2448-2452): The out-of-place `torch.where` fix preserves gradients, but the modified HKL grid might not be correctly passed to the CPU simulator in the warm path.
2. **Crystal state not updated in CPU warm context**: The Stage B closure might use a stale crystal object on CPU when applying shell modifiers.
3. **Simulator warm cache reuse issue**: The cached simulator in `stage_b_eval_stage_a_ctx.simulators[panel_id]` might be reusing CUDA-built models that fail on CPU.

**Next Actions (future loop):**
1. **Investigate Stage B CPU warm path HKL grid handling** (lines 2556-2558 Bragg CPU warm diagnostics):
   - Add diagnostics to log HKL grid device/dtype before `simulator.run()` call
   - Check if modified HKL grid (with shell modifiers) correctly transfers to CPU
   - Compare warm vs cold HKL grid tensors on CPU
2. **Compare Stage B closure warm vs cold paths on CPU**:
   - Run Stage B test with `enable_stage_a_warm_cache=False` to force cold path
   - Check if cold path produces non-zero Bragg on CPU
3. **Inspect Stage B shell modifier HKL grid flow**:
   - Trace HKL grid from `_build_stage_b_lbfgs_closure` line 2448 (`hkl_grid_modified = torch.where(...)`) to simulator call line 2556
   - Verify device consistency throughout the flow

**Confidence:** HIGH (~85%) that fix is in dbex Stage B context/cache management, NOT nanobrag_torch.

**Status:** Phase C2.3 COMPLETE → Phase C2.4 dbex Stage B CPU warm path investigation

---

### Path B (FAIL — Bragg max == 0) ❌ REJECTED

**Verdict:** nanobrag_torch CPU simulator bug

**Evidence:** N/A — reproducer PASSED

**Conclusion:** This path is RULED OUT. The simulator works correctly on CPU when given proper inputs.

---

### Path C (Runtime Error) ❌ NOT APPLICABLE

**Verdict:** Import/dependency issue or API mismatch

**Evidence:** No runtime errors during reproducer execution

**Conclusion:** Reproducer ran cleanly to completion without exceptions.

---

### Path D (Construction Blocked) ❌ NOT APPLICABLE

**Verdict:** Reproducer approach infeasible

**Evidence:** Reproducer successfully constructed CPU StageAContext and ran simulator

**Conclusion:** Reproducer approach was feasible and effective.

---

## Confidence Assessment

**Confidence reproducer result is correct:** VERY HIGH (98%)
- Bragg output matches expected pattern (99% coverage, ~2.7e-3 mean intensity)
- Crystal parameters match canonical refGeom.expt values
- No warnings or errors during simulation

**Confidence root cause is in dbex (not nanobrag_torch):** HIGH (85%)
- Standalone context works, full test fails → issue is in dbex integration
- Loop i=219 proved parameters are identical → context construction is correct
- Remaining bug must be in Stage B warm-cache HKL grid handling or crystal state

**Confidence next investigation will find fix quickly:** MEDIUM (60%)
- HKL grid flow in Stage B is well-documented (REFINE-005, GRADIENT-002)
- Diagnostic patterns established in loop i=217-219
- May require 1-2 loops to add diagnostics + identify exact break point

## Findings to Update

**GRADIENT-003** (CPU Fallback Path Zero Bragg Output):
- **Status:** Active → Path A investigation (dbex cache/context bug confirmed)
- **Update:** Minimal reproducer PASSED (99% Bragg coverage on CPU). Root cause is NOT in nanobrag_torch simulator; isolated to dbex Stage B warm-cache HKL grid handling or context cloning logic.
- **Evidence:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/reproducer_result.json (max=0.086, nonzero=99%)
- **Next Actions:** Investigate Stage B CPU warm path (lines 2234-2246 context builder, lines 2448-2452 HKL modification, lines 2556-2558 simulator call). Add HKL grid device/dtype diagnostics, compare warm vs cold paths on CPU.

**PERF-WARM-012** (CPU Fallback Context):
- **Update:** CPU StageAContext construction is CORRECT (reproducer confirms). Bug is downstream in Stage B usage, not in context builder.

## Artifacts

- `reproducer_result.json` — Decision output (PASS, Path A)
- `reproducer_run.log` — Stdout/stderr capture (clean execution, 99% Bragg coverage)
- `phase_c2_3_decision.md` (this file) — 4-path synthesis with Path A selected
- `minimal_cpu_bragg_reproducer.py` — Committed reproducer script (T2 tier, reusable)
- `summary.md` — Turn Summary block (to be written)

## Next Loop Candidate (Path A)

**Focus:** ARCH-REFINE-FLOW-001 Phase C2.4 — dbex Stage B CPU warm-cache HKL grid investigation

**Scope:**
- Add diagnostics to Stage B CPU warm path (HKL grid device/dtype, tensor addresses before/after shell modification)
- Compare warm vs cold Stage B paths on CPU (`enable_stage_a_warm_cache=False` toggle)
- Identify exact point where HKL grid or crystal state breaks on CPU
- Apply targeted fix (likely HKL grid device transfer or simulator cache invalidation)

**Estimated effort:** 1-2 loops (diagnostics quick, fix may require deeper investigation)

**Exit criteria:**
- Stage B full detector test PASSES on CPU with non-zero Bragg output
- OR conscious decision to defer CPU fallback support if fix is complex

## Decision Tree Summary

```
Reproducer Result: PASS (bragg_max > 0)
├── Path A (dbex bug) ✅ SELECTED
│   └── Next: Phase C2.4 dbex Stage B CPU warm path investigation
├── Path B (nanobrag_torch bug) ❌ REJECTED
├── Path C (runtime error) ❌ NOT APPLICABLE
└── Path D (construction blocked) ❌ NOT APPLICABLE
```

## Script Metadata

**Script:** `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py`
**Tier:** T2 (decision-carrying, reusable, checked-in, argparse + header)
**Usage:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py \
  --expt-path refGeom.expt \
  --out-dir plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/
```

**Exit code:** 0 (PASS)
**Runtime:** ~30 seconds (single panel CPU simulation)
**Decision:** Path A (dbex cache/context bug)
