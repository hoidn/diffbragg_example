# Galph Loop i=220 — Phase C2.2 Minimal Reproducer Planning

## Executive Summary

Reviewed Ralph's loop i=219 evidence and **confirmed Hypothesis 1 (crystal parameter mismatch) is DISPROVEN** with 100% config parity. The zero Bragg output despite correct parameters points to a nanobrag_torch CPU simulator bug (90% confidence). Escalating to **Path E** (minimal reproducer OR source inspection).

## Analysis

### Evidence Review

Ralph's diagnostic instrumentation compared CUDA vs CPU crystal configs at two checkpoints:
- **PRE**: dxtbx crystal state before `_build_stage_a_context`
- **POST**: nanobrag_torch CrystalConfig after `create_crystal_config`

**Result**: ZERO parameter discrepancies across all 13 parameters:
- Cell parameters: a=27.376Å, b=32.066Å, c=34.466Å, α=88.769°, β=71.630°, γ=68.189°
- MOSFLM a*/b*/c* vectors: EXACT match to float32 precision
- misset_deg: [0,0,0]
- A/U/B matrices: EXACT match
- device: correctly set (cuda:0 vs cpu)

### Critical Finding

Despite identical configs, **CPU simulator produces ZERO Bragg intensities**:
```
[BRAGG_CPU_WARM] bragg_panel.shape=torch.Size([2527, 2463])
                 bragg_panel.min=0.0
                 bragg_panel.max=0.0
                 bragg_panel.mean=0.0
```

This is 100% pixel failure across 6.2M pixels per panel, across 3 closure calls.

### Root Cause Update

RCA v3 Hypothesis 1 (crystal parameter mismatch): **REJECTED** with 95% confidence.

**New Hypothesis 5 (90% confidence)**: nanobrag_torch CPU simulator bug.

**Evidence**:
1. Identical inputs (configs)
2. Zero output (all Bragg pixels)
3. Interpolation warnings ("out of range for three point interpolation")
4. CUDA path works (small detector test PASSED)

**Suspected Location**: nanobrag_torch internal CPU-specific paths:
- Miller index calculation using wrong reciprocal lattice on CPU
- CPU interpolation path has tensor device/dtype mismatch
- Warm cache CPU context has stale crystal state

## Decision: Path E (Minimal Reproducer OR Source Inspection)

RCA v3 did not anticipate this scenario (parameters correct, simulator fails). **Path E** is unlisted but required.

### Option A: Minimal Reproducer (Preferred)

**Rationale**: Isolate dbex vs nanobrag_torch quickly before committing to source inspection.

**Approach**:
1. Create standalone script `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py`
2. Build CPU StageAContext with known HKL grid
3. Run one panel simulation
4. Check if Bragg output is non-zero
5. **If reproducer fails** → confirms nanobrag_torch bug (proceed to source inspection + patch)
6. **If reproducer succeeds** → dbex cache/context setup bug (return to dbex investigation)

**Estimated effort**: 1 loop

### Option B: Direct Source Inspection

**Rationale**: If reproducer route is blocked or time-sensitive.

**Approach**:
1. Read `nanobrag_torch/simulator.py::run()` CPU-specific paths
2. Read `nanobrag_torch/models/crystal.py::get_structure_factor()` interpolation logic
3. Look for:
   - Device guards that might skip CPU
   - Conditional logic that differs between CPU/CUDA
   - Reciprocal lattice vector computation bugs
   - HKL grid indexing errors
4. Draft targeted patch per POLICY-001
5. Test patch in isolation
6. Validate both tests PASS

**Estimated effort**: 2-3 loops

## Findings Update

Created **GRADIENT-003** in `docs/findings.md`:
- Tags: gradients, cpu-fallback, stage-b, nanobrag-torch, simulator
- Summary: CPU fallback produces zero Bragg despite 100% param parity; suspected simulator bug in Miller index / interpolation logic
- Status: Active — requires minimal reproducer OR source inspection
- Next Actions: Build reproducer → if fails, inspect source + patch OR defer CPU; if succeeds, return to dbex investigation

## Next Loop Planning

### Scope

**Phase C2.3**: Minimal Reproducer OR Source Inspection

**Mode**: ready_for_implementation (reproducer script + execution)

**Focus**: ARCH-REFINE-FLOW-001 Phase C2.3

**Dwell**: Reset to 0 (last loop review_or_housekeeping with decision synthesis)

### Do Now Tasks

**Option A: Minimal Reproducer** (Recommended)

1. Create `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py` (T2 script per scriptization policy):
   - Argparse: `--crystal-path`, `--detector-path`, `--hkl-grid-path`, `--output-dir`
   - Build CPU StageAContext from refGeom inputs
   - Run single panel simulation
   - Check Bragg tensor stats (min, max, mean, nonzero fraction)
   - Write JSON result: `{reproducer_passed: bool, bragg_stats: {...}, error: str or null}`
2. Execute script with refGeom inputs
3. Analyze result:
   - **If Bragg ≠ 0** → PASS, dbex bug (escalate to cache investigation)
   - **If Bragg == 0** → FAIL, nanobrag_torch bug (proceed to source inspection)
4. Write decision synthesis
5. Commit findings + decision

**Option B: Source Inspection** (If reproducer blocked)

1. Read nanobrag_torch source files
2. Identify CPU-specific bug
3. Draft patch
4. Test patch
5. Validate

### Artifacts

`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z/`:
- `summary.md` (this file)
- `input.md` (Do Now for Ralph)

## Recommendations

1. **Prefer minimal reproducer** (Option A) — isolates dbex vs nanobrag_torch quickly
2. **If reproducer fails**: Apply POLICY-001 exception for targeted nanobrag_torch patch OR defer CPU fallback support
3. **If reproducer succeeds**: Return to dbex warm cache / context cloning investigation
4. **Environment Freeze**: Reproducer script is T2 (reusable, decision-carrying) → save with proper header template

---

### Turn Summary
Disproved Hypothesis 1 (parameter mismatch) with 100% config parity evidence; zero Bragg output despite correct params points to nanobrag_torch CPU simulator bug (90% confidence).
Escalated to Path E (minimal reproducer to isolate dbex vs nanobrag_torch OR direct source inspection); created GRADIENT-003 finding documenting CPU simulator zero-output bug.
Next: build minimal reproducer script → if fails, inspect nanobrag_torch source + patch OR defer CPU fallback.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z/ (summary.md, input.md)
