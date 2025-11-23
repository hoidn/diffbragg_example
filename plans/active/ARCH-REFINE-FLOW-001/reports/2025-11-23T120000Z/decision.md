# Phase C2.2 HKL Hit-Rate Diagnostic Decision

## Executive Summary

**Hypothesis 1 (Crystal Parameter Mismatch) is DISPROVEN.**

Crystal parameter diagnostics reveal **IDENTICAL** parameters between CUDA and CPU paths:
- Cell parameters: **EXACT match** (a=27.376, b=32.066, c=34.466, α=88.769°, β=71.630°, γ=68.189°)
- MOSFLM A* vectors: **EXACT match** (down to float32 precision)
- Misset angles: **EXACT match** ([0, 0, 0])
- Device: Correctly set (cuda:0 vs cpu)

However, **ALL Bragg intensities on CPU are zero** (`bragg_panel.min=0.0, bragg_panel.max=0.0, bragg_panel.mean=0.0`), while CUDA produces normal intensities. The "out of range for three point interpolation" warning appears on CPU but not on a working CUDA path, suggesting the root cause is **deeper in the nanobrag_torch simulator**, not in parameter setup.

## Evidence

### Crystal Config Comparison

**CUDA PRE** (dxtbx crystal state):
- cell=(27.376, 32.066, 34.466, 88.769°, 71.630°, 68.189°)
- A_matrix, U_matrix, B_matrix: [values match CPU]

**CUDA POST** (nanobrag_torch CrystalConfig):
- cell_a/b/c, cell_alpha/beta/gamma: **EXACT match with CPU**
- mosflm_a_star=[-0.02757067, -0.02869191, -0.01245197]: **EXACT match**
- mosflm_b_star=[-0.00416187, 0.02966329, -0.01563749]: **EXACT match**
- mosflm_c_star=[0.02523375, -0.00187283, -0.01747896]: **EXACT match**
- misset_deg=[0, 0, 0]: **EXACT match**

**CPU PRE** (dxtbx crystal state):
- Identical to CUDA PRE

**CPU POST** (nanobrag_torch CrystalConfig):
- **100% IDENTICAL** to CUDA POST for all parameters

### Bragg Tensor Diagnostics

**CPU Warm Path** (3 closure calls):
```
[BRAGG_CPU_WARM] bragg_panel.shape=torch.Size([2527, 2463])
                 bragg_panel.min=0.0
                 bragg_panel.max=0.0
                 bragg_panel.mean=0.0
```

**Critical Finding**: Despite identical crystal configs, the CPU simulator produces **zero Bragg intensities** across the entire detector panel. This means:
1. Either **ALL Miller indices are out of bounds** (100% HKL grid misses), OR
2. The simulator has a CPU-specific bug that zeros out the output

### Warning Signature

```
WARNING: out of range for three point interpolation
WARNING: further warnings will not be printed!
```

This warning appears during CPU simulation but is **suppressed after first occurrence**, so we don't know how many pixels are affected. The warning originates from nanobrag_torch's tricubic interpolation code when Miller indices fall outside the HKL grid bounds.

## Root Cause Analysis

### Updated Hypothesis Ranking

**Hypothesis 2 (A* Matrix Injection Bug):** REJECTED
*Reason:* MOSFLM A* vectors are **identical** between CUDA and CPU after `create_crystal_config`.

**Hypothesis 1 (Crystal Parameter Mismatch):** REJECTED
*Reason:* **Zero parameter discrepancies** found. Cell, A*, U, B, misset all match exactly.

**Hypothesis 3 (Detector Geometry Mismatch):** REJECTED (by proxy)
*Reason:* Same detector object used; geometry is device-agnostic. If this were the issue, we'd see partial (not zero) Bragg output.

**NEW Hypothesis 5 (nanobrag_torch CPU Simulator Bug):** **PROMOTED to 90% confidence**
*Reason:* Identical inputs + zero output + interpolation warnings → simulator internal pathology.

## Decision Path: E (nanobrag_torch Simulator Bug)

RCA v3 did not anticipate a scenario where parameters are correct but the simulator still fails. This is **Path E** (unlisted in RCA v3): a simulator-level bug in nanobrag_torch CPU-specific code.

### Evidence for Path E

1. **Zero Bragg output despite correct parameters** → simulator bug, not setup bug
2. **"out of range for three point interpolation" warning** → Miller indices or interpolation logic broken
3. **CUDA path works** → bug is CPU-specific
4. **100% failure rate** → not a numerical precision issue (would show partial failures)

### Potential Root Causes (nanobrag_torch internal)

1. **Miller index calculation on CPU uses wrong A* vectors internally**
   - Hypothesis: Even though `crystal_config.mosflm_a_star` is correct, the simulator might recompute reciprocal lattice vectors incorrectly on CPU
   - Test: Add diagnostics inside nanobrag_torch.Simulator.run() around line 877-885 (reciprocal lattice rotation)

2. **CPU-specific tensor device mismatch in interpolation**
   - Hypothesis: HKL grid or Miller indices have mixed device/dtype causing interpolation to return zeros
   - Test: Check tensor devices inside nanobrag_torch.Crystal.get_structure_factor()

3. **CPU path uses stale or uninitialized crystal state**
   - Hypothesis: Warm cache CPU context might not properly update crystal parameters before simulation
   - Test: Compare crystal.hkl_data addresses between warm context setup and closure call

### Next Investigation Steps

**Phase 3 (Escalated to nanobrag_torch inspection):**

1. **Minimal Reproducer** (highest priority):
   - Create standalone script that:
     - Builds a CPU StageAContext with known HKL grid
     - Runs one panel simulation
     - Checks if Bragg output is non-zero
   - If reproducer fails → confirms simulator bug (not dbex issue)
   - If reproducer succeeds → cache/context setup bug in dbex

2. **nanobrag_torch Source Inspection** (if reproducer fails):
   - Read `nanobrag_torch/simulator.py::run()` CPU-specific paths
   - Read `nanobrag_torch/models/crystal.py::get_structure_factor()` interpolation logic
   - Look for:
     - Device guards that might skip CPU
     - Conditional logic that differs between CPU/CUDA
     - Reciprocal lattice vector computation bugs
     - HKL grid indexing errors

3. **Patch or Escalate** (if bug found):
   - If fixable: Apply patch per POLICY-001 (Environment Freeze exception for local source bugfix)
   - If complex: Defer CPU fallback support, mark as known limitation
   - Document in GRADIENT-003 finding

## Recommended Action (Next Loop)

**DO NOT APPLY FIX** (this loop is evidence-only per input.md Mode: none).

**Next Loop Tasks:**
1. Build minimal reproducer to isolate dbex vs nanobrag_torch
2. If nanobrag_torch bug confirmed:
   - Inspect simulator source
   - Draft targeted patch
   - Test patch in isolation
3. If dbex bug:
   - Investigate warm cache crystal state management
   - Check HKL grid device transfers

**Alternative (if investigation is blocked):**
- Escalate to defer CPU fallback support for Stage B
- Update PERF-WARM-012 finding with CPU limitation
- Mark full detector Stage B tests as CUDA-only

## Confidence Assessment

**Confidence:** VERY HIGH (95%) that Hypothesis 1 is WRONG.
**Confidence:** HIGH (90%) that root cause is in nanobrag_torch simulator CPU path, not dbex parameter setup.
**Confidence:** MEDIUM (60%) that a minimal reproducer will isolate the issue quickly.

## Findings to Update

**GRADIENT-003** (CPU Fallback Path Zero Bragg Output):
- **Tags:** gradient, cpu-fallback, stage-b, nanobrag-torch, simulator-bug
- **Summary:** CPU fallback path produces zero Bragg intensities despite identical crystal/detector parameters to CUDA. Diagnostic comparison (CRYSTAL_CUDA_PRE/POST vs CRYSTAL_CPU_PRE/POST) shows 100% parameter parity, ruling out configuration mismatch. "Out of range for three point interpolation" warnings suggest simulator-level Miller index or interpolation bug on CPU.
- **Source:** Loop i=219 (diagnostic), dbex/nanobrag_refinement.py:2206-2221 (CPU context builder), nanobrag_torch Simulator.run() (suspected)
- **Status:** Active — Requires nanobrag_torch minimal reproducer + source inspection
- **Next Actions:** Build minimal reproducer, inspect simulator.run() CPU paths, consider patch or defer CPU support

**PERF-WARM-012** (CPU Fallback Context):
- Update: CPU StageAContext parameters are correct; issue is downstream in simulator execution

## Artifacts

- `pytest_stage_b_full_diagnostic.log` — Full test run with crystal config and Bragg diagnostics
- `crystal_config_comparison.txt` — Extracted CUDA vs CPU parameter comparison (100% match)
- `decision.md` (this file) — Root cause analysis and next steps
- `summary.md` — To be written in step 10

## Decision

**Path E (nanobrag_torch Simulator Bug)** is the correct escalation path.

Next loop: Build minimal reproducer or inspect nanobrag_torch source directly.
