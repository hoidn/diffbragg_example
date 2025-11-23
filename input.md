# Ralph Input — Loop i=220

## Summary
Build minimal CPU Bragg reproducer to isolate nanobrag_torch simulator bug vs dbex context setup issue.

## Mode
none (reproducer script authorship + decision analysis, no production dbex code changes)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.3: minimal CPU Bragg reproducer)

## Branch
`integration` (current working branch)

## Mapped Tests
none — evidence-only loop (reproducer construction + decision analysis)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/`

Store all outputs under this timestamp directory:
- `minimal_cpu_bragg_reproducer.py` — reproducer script (to be committed to `plans/active/ARCH-REFINE-FLOW-001/bin/`)
- `reproducer_result.json` — decision output with Bragg stats and next path
- `reproducer_run.log` — stdout/stderr from script execution
- `phase_c2_3_decision.md` — decision synthesis with 4-path tree analysis
- `summary.md` — Turn Summary block

## Do Now

Build a minimal standalone reproducer script to isolate whether the zero Bragg output on CPU (loop i=219 finding) is caused by a nanobrag_torch simulator bug or a dbex context setup issue.

**Context:** Loop i=219 diagnostic evidence proved 100% crystal parameter parity between CUDA and CPU paths (cell, MOSFLM A* vectors, misset, A/U/B matrices ALL identical), yet CPU simulator produces zero Bragg intensities across all 6.2M pixels per panel. This suggests a bug inside nanobrag_torch Simulator.run() or interpolation logic on CPU, NOT a dbex configuration mismatch.

**Objective:** Create a standalone script that builds a CPU StageAContext using the SAME parameters that work on CUDA, runs a single panel simulation, and checks whether Bragg output is non-zero. If the reproducer fails (zero Bragg), the bug is in nanobrag_torch. If it succeeds (non-zero Bragg), the bug is in dbex warm cache or context cloning.

### Task Breakdown (10 steps)

#### 1. Review Phase C2.2 Evidence
Read the following artifacts from loop i=219:
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/decision.md`
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/summary.md`
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/crystal_config_comparison.txt`

Understand:
- 100% parameter parity (13 parameters match exactly)
- Zero Bragg output on CPU despite correct params
- "Out of range for three point interpolation" warnings
- Hypothesis 5: nanobrag_torch CPU simulator bug (90% confidence)

#### 2. Create Reproducer Script Stub

Create file: `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py`

Use this header template (T2 scriptization policy):
```python
#!/usr/bin/env python3
"""
Minimal CPU Bragg Reproducer — Isolate dbex vs nanobrag_torch bug
Initiative: ARCH-REFINE-FLOW-001, Owner: galph, Loop: i=220

Purpose:
  Build CPU StageAContext with canonical refGeom.expt parameters,
  run single-panel simulation, check if Bragg output is non-zero.

Inputs:
  --expt-path (optional): Path to refGeom.expt (default: tests/fixtures/refGeom.expt)
  --out-dir (optional): Output directory for JSON decision (default: current dir)

Outputs:
  reproducer_result.json: {"result": "PASS"|"FAIL", "bragg_stats": {...}, "next_path": "A"|"B"|"C"|"D"}

Repro:
  python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py \\
    --expt-path tests/fixtures/refGeom.expt \\
    --out-dir plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/

Decision Criteria:
  - IF bragg.max() > 0 → PASS (dbex bug, Path A: investigate cache/context)
  - ELSE → FAIL (nanobrag_torch bug, Path B: source inspection + patch OR defer)
"""
import argparse
import json
import sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="Minimal CPU Bragg reproducer")
    ap.add_argument("--expt-path", type=str, default="tests/fixtures/refGeom.expt",
                    help="Path to refGeom.expt")
    ap.add_argument("--out-dir", type=str, default=".",
                    help="Output directory for JSON decision")
    args = ap.parse_args()

    # (Implementation below)
    pass

if __name__ == "__main__":
    main()
```

#### 3. Load Canonical Crystal/Detector/Beam

Inside `main()`, add:
```python
# Lazy imports to avoid circular dependencies
import torch
from dxtbx.model.experiment_list import ExperimentListFactory

# Load refGeom.expt
expt_path = Path(args.expt_path)
if not expt_path.exists():
    print(f"ERROR: {expt_path} not found", file=sys.stderr)
    sys.exit(1)

expt_list = ExperimentListFactory.from_json_file(str(expt_path), check_format=False)
expt = expt_list[0]
detector = expt.detector
beam = expt.beam
crystal = expt.crystal

print(f"[LOAD] Loaded {expt_path}")
print(f"[CRYSTAL] cell={crystal.get_unit_cell().parameters()}")
print(f"[DETECTOR] {len(detector)} panels")
print(f"[BEAM] wavelength={beam.get_wavelength()}")
```

#### 4. Build CPU StageAContext

Add:
```python
# Import dbex helper (lazy to avoid circular deps)
from dbex.nanobrag_refinement import _build_stage_a_context
from dbex.nanobrag_bridge import load_structure_factors_from_mtz

# Device
device = torch.device("cpu")
dtype = torch.float32

# Load MTZ (use canonical path from test fixtures)
mtz_path = Path("tests/fixtures/1vpj.mtz")
if not mtz_path.exists():
    print(f"ERROR: {mtz_path} not found", file=sys.stderr)
    sys.exit(1)

hkl_data = load_structure_factors_from_mtz(str(mtz_path))
print(f"[MTZ] Loaded {mtz_path}, {len(hkl_data)} structure factors")

# Build CPU context (same parameters as CUDA path)
# Reference: dbex/nanobrag_refinement.py:2206-2221 (CPU context builder in inline path)
stage_a_ctx = _build_stage_a_context(
    detector=detector,
    beam=beam,
    crystal=crystal,
    hkl_data=hkl_data,
    enable_hkl_interpolation=True,  # tricubic per REFINE-005
    device=device,
    dtype=dtype,
    enable_hkl_padding=True,        # halo per REFINE-005
    baseline_crystal=None,          # no incremental UB for reproducer
)

print(f"[CONTEXT] Built CPU StageAContext")
print(f"[CONTEXT] HKL grid shape: {stage_a_ctx['hkl_grid'].shape}")
print(f"[CONTEXT] Detectors cached: {len(stage_a_ctx['detectors'])}")
```

#### 5. Extract Panel 0 Config + Simulator

Add:
```python
# Extract panel 0 (first panel)
panel_id = 0
detector_config = stage_a_ctx["detectors"][panel_id]
hkl_grid = stage_a_ctx["hkl_grid"]
crystal_config = stage_a_ctx["crystal"]

print(f"[PANEL] Extracted panel {panel_id}")
print(f"[PANEL] detector pixels: {detector_config.npixels_slow} x {detector_config.npixels_fast}")

# Create Simulator
# Lazy import nanobrag_torch
from nanobrag_torch import Simulator

simulator = Simulator(
    detector=detector_config,
    beam=stage_a_ctx["beam"],
    crystal=crystal_config,
    device=device,
    dtype=dtype,
)

print(f"[SIMULATOR] Created on device={device}, dtype={dtype}")
```

#### 6. Run Single Panel Simulation

Add:
```python
# Run simulator.run() with HKL grid
print(f"[SIMULATION] Running single panel on CPU...")

with torch.no_grad():  # No gradients needed for reproducer
    bragg_panel = simulator.run(hkl_grid)

print(f"[SIMULATION] Complete")
```

#### 7. Check Bragg Output Stats

Add:
```python
# Compute Bragg stats
bragg_min = float(bragg_panel.min().item())
bragg_max = float(bragg_panel.max().item())
bragg_mean = float(bragg_panel.mean().item())
nonzero_count = int((bragg_panel > 0).sum().item())
total_pixels = bragg_panel.numel()

print(f"[BRAGG] shape={bragg_panel.shape}")
print(f"[BRAGG] min={bragg_min}, max={bragg_max}, mean={bragg_mean}")
print(f"[BRAGG] nonzero_count={nonzero_count}/{total_pixels} ({100*nonzero_count/total_pixels:.2f}%)")

bragg_stats = {
    "shape": list(bragg_panel.shape),
    "min": bragg_min,
    "max": bragg_max,
    "mean": bragg_mean,
    "nonzero_count": nonzero_count,
    "total_pixels": total_pixels,
    "nonzero_fraction": nonzero_count / total_pixels,
}
```

#### 8. Write JSON Decision File

Add:
```python
# Decision criteria: bragg_max > 0 → PASS, else FAIL
if bragg_max > 0:
    result = "PASS"
    next_path = "A"  # dbex bug (cache/context issue)
    message = "Bragg output is non-zero on CPU reproducer. Bug is in dbex warm cache or context cloning."
else:
    result = "FAIL"
    next_path = "B"  # nanobrag_torch bug (simulator issue)
    message = "Bragg output is zero on CPU reproducer. Bug is in nanobrag_torch Simulator.run() CPU path."

decision = {
    "result": result,
    "next_path": next_path,
    "message": message,
    "bragg_stats": bragg_stats,
    "crystal_params": {
        "cell_a": float(crystal.get_unit_cell().parameters()[0]),
        "cell_b": float(crystal.get_unit_cell().parameters()[1]),
        "cell_c": float(crystal.get_unit_cell().parameters()[2]),
        "cell_alpha": float(crystal.get_unit_cell().parameters()[3]),
        "cell_beta": float(crystal.get_unit_cell().parameters()[4]),
        "cell_gamma": float(crystal.get_unit_cell().parameters()[5]),
    },
    "device": str(device),
    "dtype": str(dtype),
}

# Write JSON
out_dir = Path(args.out_dir)
out_dir.mkdir(parents=True, exist_ok=True)
json_path = out_dir / "reproducer_result.json"
with open(json_path, "w") as f:
    json.dump(decision, f, indent=2)

print(f"[RESULT] {result} ({next_path})")
print(f"[OUTPUT] {json_path}")

# Exit code: 0 if PASS, 1 if FAIL
sys.exit(0 if result == "PASS" else 1)
```

#### 9. Run Reproducer and Capture Output

Execute:
```bash
KMP_DUPLICATE_LIB_OK=TRUE python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py \
  --expt-path tests/fixtures/refGeom.expt \
  --out-dir plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/ \
  2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/reproducer_run.log
```

Expected runtime: ~30 seconds (single panel CPU simulation)

Capture:
- Exit code (0 = PASS, 1 = FAIL)
- stdout/stderr in `reproducer_run.log`
- `reproducer_result.json` with decision

#### 10. Decision Synthesis

Read `reproducer_result.json` and synthesize decision per 4-path tree:

**Path A (reproducer PASS, bragg_max > 0):**
- **Verdict:** Bug is in dbex warm cache or context cloning, NOT nanobrag_torch
- **Evidence:** Standalone CPU context produces non-zero Bragg, but full test fails
- **Next Actions (future loop):**
  - Investigate dbex warm cache HKL grid device transfer (lines 2460-2470)
  - Check if `stage_a_ctx` cloning (lines 2206-2221) drops gradient or device info
  - Compare warm vs cold path HKL grids on CPU
- **Confidence:** HIGH (~85%) that fix is in dbex context management
- **Status:** Phase C2.3 COMPLETE → Phase C2.4 dbex cache investigation

**Path B (reproducer FAIL, bragg_max == 0):**
- **Verdict:** Bug is in nanobrag_torch Simulator.run() CPU-specific code
- **Evidence:** Standalone CPU reproducer with correct params produces zero Bragg
- **Next Actions (future loop):**
  - Inspect `nanobrag_torch/simulator.py::run()` CPU paths (lines ~877-885: reciprocal lattice rotation)
  - Inspect `nanobrag_torch/models/crystal.py::get_structure_factor()` (interpolation logic)
  - Add diagnostics to log Miller indices, reciprocal lattice vectors, interpolation bounds
  - Draft targeted patch per POLICY-001 OR defer CPU fallback if complex
- **Confidence:** VERY HIGH (~95%) that bug is in nanobrag_torch simulator
- **Status:** Phase C2.3 COMPLETE → Phase C2.4 nanobrag_torch source inspection + patch OR deferral

**Path C (reproducer runtime error):**
- **Verdict:** Import/dependency issue or API mismatch
- **Evidence:** Script crashes with ImportError, AttributeError, or TypeError
- **Next Actions (same loop if quick, else next loop):**
  - Diagnose error signature
  - Fix imports (lazy imports, handle missing modules)
  - Adjust API calls if nanobrag_torch/dbex signatures changed
  - Retry reproducer
- **Confidence:** LOW (~30%) — reproducer construction should be straightforward
- **Status:** Phase C2.3 BLOCKED → debug + retry

**Path D (script construction blocked):**
- **Verdict:** Reproducer approach infeasible (complex dependency chain)
- **Evidence:** Cannot extract StageAContext parameters cleanly
- **Next Actions (fallback to direct inspection):**
  - Skip reproducer, go directly to nanobrag_torch source inspection
  - Add diagnostic prints to Simulator.run() and Crystal.get_structure_factor()
  - Run full test with diagnostics, log Miller indices and reciprocal lattice
  - Analyze diagnostics to identify CPU-specific bug
- **Confidence:** LOW (~20%) — reproducer should be feasible
- **Status:** Phase C2.3 BLOCKED → fallback to source inspection

Write decision synthesis to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/phase_c2_3_decision.md` with:
- Reproducer result (PASS/FAIL/ERROR/BLOCKED)
- Bragg stats from JSON
- Selected path (A/B/C/D) with evidence
- Confidence assessment
- Next loop actions

Update `plans/active/ARCH-REFINE-FLOW-001/implementation.md` with Phase C2.3 status and artifacts path.

Write Turn Summary to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/summary.md` (use lightweight format, 3-5 sentences, no focus IDs or selectors).

Commit script to `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py` with message:
```
SUPERVISOR: Phase C2.3 minimal CPU Bragg reproducer - tests: not run
```

Push to remote.

## How-To Map

### Environment Flags
```bash
KMP_DUPLICATE_LIB_OK=TRUE  # Required for CPU torch operations (per CONFORMANCE-001)
```

### Reproducer Execution
```bash
cd /home/ollie/Documents/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py \
  --expt-path tests/fixtures/refGeom.expt \
  --out-dir plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/
```

Expected exit codes:
- 0 → PASS (Bragg non-zero, dbex bug)
- 1 → FAIL (Bragg zero, nanobrag_torch bug)
- >1 → ERROR (runtime exception)

### JSON Output Schema
```json
{
  "result": "PASS" | "FAIL",
  "next_path": "A" | "B" | "C" | "D",
  "message": "Human-readable verdict",
  "bragg_stats": {
    "shape": [2527, 2463],
    "min": 0.0,
    "max": 123.45,
    "mean": 0.67,
    "nonzero_count": 12345,
    "total_pixels": 6226401,
    "nonzero_fraction": 0.00198
  },
  "crystal_params": {
    "cell_a": 27.376,
    "cell_b": 32.066,
    "cell_c": 34.466,
    "cell_alpha": 88.769,
    "cell_beta": 71.630,
    "cell_gamma": 68.189
  },
  "device": "cpu",
  "dtype": "torch.float32"
}
```

### Bragg Decision Threshold
- `bragg_max > 0` → PASS (Path A)
- `bragg_max == 0` → FAIL (Path B)

### Artifacts Locations
All artifacts under: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/`
- `reproducer_result.json` — decision output
- `reproducer_run.log` — stdout/stderr capture
- `phase_c2_3_decision.md` — 4-path synthesis
- `summary.md` — Turn Summary block

Script committed to: `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py`

## Pitfalls To Avoid

1. **Circular imports:** Use lazy imports for `dbex.nanobrag_refinement`, `dbex.nanobrag_bridge`, and `nanobrag_torch` inside `main()`, not at module level
2. **Device/dtype consistency:** All tensors must be on `device=cpu` with `dtype=torch.float32` (match production paths)
3. **torch.compile on CPU:** Do NOT use `torch.compile` on CPU (per RUNTIME-001), though reproducer doesn't use gradients so this is less critical
4. **Missing fixtures:** If `refGeom.expt` or `1vpj.mtz` not found, print clear error and exit with code 1
5. **ImportError handling:** Wrap imports in try/except if needed, but expect all dependencies available (dxtbx, nanobrag_torch, dbex modules)
6. **No production dbex edits:** This loop is reproducer-only; do NOT modify `dbex/nanobrag_refinement.py` or any production code
7. **Argparse required:** Use argparse per T2 scriptization policy (no hardcoded paths except defaults)
8. **Header template:** Include all required fields (Purpose, Inputs, Outputs, Repro, Decision Criteria)
9. **JSON serialization:** All numeric values must be Python native types (float/int), not torch tensors (use `.item()`)
10. **Exit code:** Return 0 if PASS, 1 if FAIL (enables shell-level decision logic)

## If Blocked

**Scenario 1: ImportError (nanobrag_torch not found)**
- Check if nanobrag_torch is installed: `python -c "import nanobrag_torch; print(nanobrag_torch.__file__)"`
- If missing, DO NOT install (Environment Freeze) — document blocker, mark script BLOCKED, escalate to Galph

**Scenario 2: AttributeError (API mismatch)**
- Check nanobrag_torch API: `python -c "from nanobrag_torch import Simulator; help(Simulator.__init__)"`
- Adjust reproducer to match current API
- Document API changes in blocker report

**Scenario 3: RuntimeError during simulation**
- Capture full stack trace in `reproducer_run.log`
- Extract error signature (e.g., "CUDA out of memory" should NOT happen on CPU)
- Write blocker report with stack trace + next steps
- Mark Path C (runtime error) in decision synthesis

**Scenario 4: Reproducer approach infeasible**
- If `_build_stage_a_context` cannot be called standalone (dependency chains too complex)
- Abandon reproducer, mark Path D (blocked)
- Escalate to Galph with blocker report
- Fallback: direct nanobrag_torch source inspection in next loop

In all blocker scenarios:
1. Write detailed blocker report in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/blocker.md`
2. Include error signatures, stack traces, attempted fixes
3. Mark Phase C2.3 status as BLOCKED in `implementation.md`
4. Commit blocker artifacts + summary
5. Do NOT proceed to decision synthesis if reproducer did not run

## Findings Applied

### Mandatory Application
- **GRADIENT-003** (CPU Fallback Path Zero Bragg Output): This reproducer directly tests the hypothesis that nanobrag_torch CPU simulator has a bug. If reproducer FAILS (zero Bragg), finding is confirmed. If reproducer PASSES, root cause is in dbex cache/context, requiring GRADIENT-003 update.
- **POLICY-001** (Environment Freeze): Reproducer is analysis tool only; no package installs, no environment modifications. If nanobrag_torch bug confirmed next loop, patch may be applied per POLICY-001 exception (local source bugfix).
- **GRADIENT-002** (Out-of-Place HKL Grid Fix): Reproducer uses `torch.no_grad()` context (no gradients needed for zero-check), so HKL grid construction is simpler. If reproducer PASSES but full test FAILS, gradient preservation may be the differentiator.
- **PERF-WARM-011/012** (CPU Fallback Context): Reproducer uses same `_build_stage_a_context` call as production code (line 2206-2221). If reproducer FAILS, context builder is correct and bug is downstream in simulator.

### Cross-References
- **RUNTIME-001** (NANOBRAGG_DISABLE_COMPILE=1): Not needed for reproducer (no torch.compile on CPU), but document for completeness
- **CONFORMANCE-001** (KMP_DUPLICATE_LIB_OK=TRUE): Required for CPU torch operations (set in How-To Map)
- **REFINE-005** (Tricubic Interpolation + Halo): Reproducer enables `enable_hkl_interpolation=True` and `enable_hkl_padding=True` to match production paths

## Pointers

### Spec/Arch Documents
- `docs/spec-db-runtime.md:34-39` — CPU/CUDA parity requirement (device neutrality mandate)
- `docs/pytorch_runtime_checklist.md` — Device/dtype neutrality checklist (float32, cpu/cuda agnostic code)
- `docs/spec-db-core.md:48-68` — Crystal parameter contracts (cell, A*, U, B definitions)

### Code References
- `dbex/nanobrag_refinement.py:2206-2221` — CPU StageAContext builder (inline path, to be replicated in reproducer)
- `dbex/nanobrag_refinement.py:542-558` — `_build_stage_a_context` helper implementation (called by reproducer)
- `dbex/nanobrag_bridge.py:450-506` — MOSFLM A* injection logic (per GRADIENT-001)
- `nanobrag_torch/simulator.py:877-885` — Reciprocal lattice rotation (suspected CPU bug location)
- `nanobrag_torch/models/crystal.py::get_structure_factor` — Tricubic interpolation (suspected out-of-bounds logic)

### Findings Documents
- `docs/findings.md:69` — GRADIENT-003 (CPU zero Bragg, 100% param parity, reproducer mandate)
- `docs/findings.md:66` — CONVERGENCE-001 (code path divergence detection pattern, may apply if reproducer PASSES)
- `docs/findings.md:35` — GRADIENT-002 (out-of-place HKL grid fix, proven on CUDA, gradient context differs from reproducer)

### Testing Guide
- `docs/TESTING_GUIDE.md:2` — Canonical environment flags table (KMP_DUPLICATE_LIB_OK required)
- `docs/development/TEST_SUITE_INDEX.md` — Test registry (no relevant selectors for reproducer loop)

### Fix Plan
- `docs/fix_plan.md:185-219` — ARCH-REFINE-FLOW-001 main ledger entry (Phase C2 attempts history)
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:246-281` — Phase C2.2 completion status + Phase C2.3 (this loop)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/decision.md` — Loop i=219 decision (Hypothesis 1 DISPROVEN, Path E escalation)

### Scriptization Policy
- `prompts/main.md` (Ralph's prompt) — T2 scriptization tier (decision-carrying, reusable, checked-in, argparse + header)
- `galph_memory.md:27-36` — Phase C2.3 planning entry (reproducer scope, decision tree, T2 tier rationale)

## Next Up (Optional)

If reproducer completes quickly and decision is clear:

**Path A (PASS) next loop candidate:**
- ARCH-REFINE-FLOW-001 Phase C2.4: dbex warm cache HKL grid investigation (add diagnostics, compare warm vs cold HKL grids on CPU)

**Path B (FAIL) next loop candidate:**
- ARCH-REFINE-FLOW-001 Phase C2.4: nanobrag_torch source inspection (read Simulator.run() CPU paths, add diagnostics, identify CPU-specific bug)

**Path C/D (ERROR/BLOCKED):**
- No next candidate; Galph will review blocker and decide escalation path

## Doc Sync Plan

Not applicable (no new tests authored this loop; reproducer is analysis tool, not a pytest test).

If future loops create nanobrag_torch patch or defer CPU fallback:
- Update `docs/TESTING_GUIDE.md` with CPU fallback status (supported/unsupported)
- Update `docs/findings.md` GRADIENT-003 with patch details OR limitation documentation
- Update `docs/pytorch_runtime_checklist.md` with CPU parity notes

## Mapped Tests Guardrail

Not applicable (Mode: none — evidence-only loop, no pytest selectors).

Reproducer script execution is NOT a pytest test; it's a standalone diagnostic tool with exit code decision logic.

## Normative Math/Physics

Not applicable (reproducer uses existing simulator APIs; no new physics implementations).

If nanobrag_torch source inspection is needed next loop, reference:
- `docs/spec-db-core.md §Reciprocal Lattice Vectors` — A*, B*, C* definitions
- `docs/spec-db-core.md §Miller Indices` — h,k,l computation from scattering vectors
- `docs/architecture/pytorch_design.md §Tricubic Interpolation` — HKL grid bounds and interpolation logic
