# Phase C2.3 CPU Simulator Bug Investigation — Minimal Reproducer

## Summary
Build and execute standalone minimal reproducer to isolate whether zero Bragg output on CPU is a nanobrag_torch simulator bug or a dbex context setup bug.

## Mode
none — evidence-only (minimal reproducer script + execution + decision synthesis)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.3 nanobrag_torch CPU simulator bug investigation)

## Branch
integration

## Mapped Tests
none — minimal reproducer is an analysis script, not a pytest test

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z/{minimal_cpu_reproducer.py, reproducer_result.json, decision.md, summary.md}

## Do Now

### Context Review
1. Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/decision.md` (Hypothesis 1 DISPROVEN with 100% param parity evidence)
2. Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z/summary.md` (Galph's Path E escalation with minimal reproducer strategy)
3. Review GRADIENT-003 finding in `docs/findings.md` (CPU simulator zero-output bug documented)

### Minimal Reproducer Implementation
4. **Create standalone reproducer script** at `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py`:
   - **Purpose**: Isolate whether CPU zero-Bragg bug is in nanobrag_torch simulator OR dbex context setup
   - **Scope**: Minimal script (≤100 lines) that builds CPU StageAContext and runs single panel simulation
   - **Header template** (per scriptization T2 policy):
     ```python
     #!/usr/bin/env python3
     """
     Minimal reproducer for CPU simulator zero-Bragg bug (initiative: ARCH-REFINE-FLOW-001, owner: galph)
     Inputs: refGeom data paths    Data deps: tests/dbex/fixtures/refGeom/{...}
     Outputs: reproducer_result.json
     Repro: python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py
     """
     import argparse
     import json
     import torch
     from pathlib import Path

     def main():
         ap = argparse.ArgumentParser(description="CPU simulator minimal reproducer")
         ap.add_argument("--output-dir", type=str, default="plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z",
                         help="Output directory for result JSON")
         args = ap.parse_args()
         # ... body ...

     if __name__ == "__main__":
         main()
     ```

   - **Implementation**:
     ```python
     # 1. Load refGeom fixtures (minimal subset)
     from dbex.data_load import DataLoad
     from dbex.nanobrag_refinement import _build_stage_a_context
     from dbex.nanobrag_bridge import create_detector_config, create_beam_config, create_crystal_config
     import numpy as np

     # 2. Build CPU StageAContext (mirroring dbex/nanobrag_refinement.py:2206-2221)
     DL = DataLoad(...)  # Load refGeom data
     crystal = DL.crystal
     detector = DL.detector
     beam = DL.beam
     hkl_grid = ...  # Load from refGeom
     hkl_metadata = ...
     config = ...  # Minimal config with enable_hkl_interpolation=True

     device = torch.device("cpu")
     dtype = torch.float32

     # Build context
     stage_a_ctx = _build_stage_a_context(
         detector=detector,
         beam=beam,
         crystal=crystal,
         hkl_grid=hkl_grid,
         hkl_metadata=hkl_metadata,
         config=config,
         device=device,
         dtype=dtype,
         trusted_mask=DL.trusted_mask,
         baseline_misset_deg_tensor=None
     )

     # 3. Run single panel simulation (panel 0)
     from nanobrag_torch import Simulator
     panel_id = 0
     detector_config = stage_a_ctx['detector_configs'][panel_id]
     crystal_model = stage_a_ctx['crystal']

     simulator = Simulator(
         detector=detector_config,
         crystal=crystal_model,
         device=device,
         dtype=dtype
     )

     # Run simulation
     bragg_panel = simulator.run()

     # 4. Check Bragg tensor stats
     bragg_min = bragg_panel.min().item()
     bragg_max = bragg_panel.max().item()
     bragg_mean = bragg_panel.mean().item()
     bragg_nonzero_frac = (bragg_panel > 0).float().mean().item()

     # 5. Verdict
     reproducer_passed = bragg_nonzero_frac > 0.0  # Any nonzero pixels → simulator works

     # 6. Write result JSON
     result = {
         "reproducer_passed": reproducer_passed,
         "bragg_stats": {
             "min": bragg_min,
             "max": bragg_max,
             "mean": bragg_mean,
             "nonzero_fraction": bragg_nonzero_frac,
             "shape": list(bragg_panel.shape)
         },
         "device": str(device),
         "panel_id": panel_id,
         "error": None if reproducer_passed else "Zero Bragg output on CPU — nanobrag_torch simulator bug confirmed"
     }

     output_path = Path(args.output_dir) / "reproducer_result.json"
     output_path.parent.mkdir(parents=True, exist_ok=True)
     with open(output_path, "w") as f:
         json.dump(result, f, indent=2)

     print(f"[REPRODUCER] Verdict: {'PASS' if reproducer_passed else 'FAIL'}")
     print(f"[REPRODUCER] Bragg stats: min={bragg_min}, max={bragg_max}, mean={bragg_mean}, nonzero_frac={bragg_nonzero_frac}")
     print(f"[REPRODUCER] Result written to {output_path}")

     return 0 if reproducer_passed else 1
     ```

### Reproducer Execution
5. **Run the minimal reproducer**:
   ```bash
   python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py --output-dir plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z
   ```
   - Expected runtime: <10s
   - **Expected outcome**: Either PASS (Bragg ≠ 0, dbex bug) OR FAIL (Bragg == 0, nanobrag_torch bug)

### Decision Synthesis
6. **Read reproducer_result.json** and analyze verdict:
   - Extract `reproducer_passed` boolean
   - Extract `bragg_stats` for evidence

7. **Write decision.md** with 4-path decision tree:

   **Path A (Reproducer FAILS — nanobrag_torch bug confirmed)**:
   - **Verdict**: Zero Bragg output is a nanobrag_torch CPU simulator bug, NOT dbex setup
   - **Root cause**: nanobrag_torch internal pathology (Miller index calculation, reciprocal lattice, or interpolation)
   - **Next Actions**:
     - Inspect nanobrag_torch source (`nanobrag_torch/simulator.py::run()`, `nanobrag_torch/models/crystal.py::get_structure_factor()`)
     - Draft targeted patch per POLICY-001 (Environment Freeze exception for blocking local source bugfix)
     - OR defer CPU fallback support for Stage B (document as known limitation in PERF-WARM-012, mark CPU path unsupported)
   - **Confidence**: HIGH (95%) that minimal reproducer isolates the bug

   **Path B (Reproducer PASSES — dbex bug)**:
   - **Verdict**: Standalone CPU simulator works, so bug is in dbex context setup or cache cloning
   - **Root cause**: Warm cache CPU context has stale/uninitialized crystal state, OR device transfers are incorrect
   - **Next Actions**:
     - Compare `_build_stage_a_context` output in reproducer vs full test
     - Check `stage_a_ctx` cloning logic at dbex/nanobrag_refinement.py:2209
     - Verify HKL grid device transfers
     - Inspect warm cache crystal state management

   **Path C (Reproducer errors / import failures)**:
   - **Verdict**: Reproducer script has implementation bug OR dependencies missing
   - **Next Actions**: Debug reproducer script, fix imports, rerun

   **Path D (Reproducer blocked by Environment Freeze)**:
   - **Verdict**: Cannot build standalone reproducer without package installs
   - **Next Actions**: Skip reproducer, proceed directly to source inspection (Option B from Galph's summary)

8. **Document next steps**:
   - If Path A → Next loop: nanobrag_torch source inspection + patch OR defer CPU fallback
   - If Path B → Next loop: dbex cache/context investigation
   - If Path C → Debug reproducer and rerun this loop
   - If Path D → Next loop: direct source inspection

### Artifacts & Documentation
9. **Write summary.md** with:
   - Reproducer implementation summary (script structure, approach)
   - Execution result (PASS/FAIL, Bragg stats)
   - Decision path selected (A/B/C/D)
   - Recommended next loop actions
   - Turn Summary block (prepend to summary.md per end-of-loop hygiene)

10. **Update implementation.md** checklist:
    - Mark Phase C2.3 status: COMPLETE (if decision clear) OR BLOCKED (if Path C/D)

## How-To Map

**Reproducer script template** (already provided in step 4).

**Minimal refGeom data loading**:
```python
from dbex.data_load import DataLoad
DL = DataLoad(
    experiment_json="tests/dbex/fixtures/refGeom/refine_experimental_image_0_indexed.json",
    reflections_pkl="tests/dbex/fixtures/refGeom/refine_experimental_image_0_indexed.refl",
    image_index=0,
    trusted_mask_pkl="tests/dbex/fixtures/refGeom/shoebox_mask_0.pickle",
    mtz_path="tests/dbex/fixtures/refGeom/4bs7.mtz"
)
```

**HKL grid loading**:
```python
import torch
hkl_grid = torch.load("tests/dbex/fixtures/refGeom/hkl_grid_halo.pt", map_location="cpu")
hkl_metadata = torch.load("tests/dbex/fixtures/refGeom/hkl_metadata.pt", map_location="cpu")
```

**Config setup**:
```python
from dbex.nanobrag_refinement import RefinementConfig
config = RefinementConfig(
    enable_hkl_interpolation=True,
    # ... other minimal flags ...
)
```

## Pitfalls To Avoid

1. **Do NOT load full test harness** — reproducer should be standalone, not invoke `run_nanobrag_refinement`
2. **Do NOT use CUDA device** — this reproducer is CPU-only to isolate the CPU bug
3. **Minimal dependencies** — avoid importing heavy modules; use `_build_stage_a_context` helper directly
4. **Explicit device/dtype** — hardcode `device=torch.device("cpu")`, `dtype=torch.float32` to match diagnostic conditions
5. **Single panel only** — no need to loop over all 12 panels; panel 0 is sufficient
6. **Check for import failures** — if `_build_stage_a_context` is not importable, document as Path D blocker
7. **Preserve diagnostics** — DO NOT remove existing CPU_FALLBACK_DIAGNOSTICS or HKL_GRAD_CHECK blocks yet (keep for next loop)
8. **T2 scriptization** — this is a decision-carrying analysis tool, so save with proper header template and argparse
9. **Environment Freeze** — no package installs; if reproducer requires new deps, document as Path D and switch to source inspection
10. **Zero-tolerance for Bragg zeros** — even 0.001% nonzero fraction is a PASS; 100% zeros is a FAIL

## Findings Applied

- **GRADIENT-003** (CPU Fallback Path Zero Bragg Output): Hypothesis 1 (parameter mismatch) DISPROVEN with 100% parity; minimal reproducer will isolate dbex vs nanobrag_torch
- **GRADIENT-002** (In-Place HKL Fix): Out-of-place `torch.where` fix WORKS on CUDA (HKL_GRAD_CHECK shows `grad_fn=<WhereBackward0>`)
- **POLICY-001** (Environment Freeze): Reproducer script is T2 analysis tool (reusable, decision-carrying); if nanobrag_torch bug confirmed, patch per POLICY-001 exception OR defer CPU fallback
- **PERF-WARM-011/012** (CPU Fallback Context): CPU context params correct (diagnostics confirmed), issue is downstream in simulator execution

## Pointers

- Hypothesis 1 DISPROVEN evidence: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/decision.md`
- Crystal config comparison (100% parity): `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/crystal_config_comparison.txt`
- Galph's Path E escalation: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z/summary.md`
- GRADIENT-003 finding: `docs/findings.md` (line ~51)
- CPU context builder: `dbex/nanobrag_refinement.py:2206-2221`
- `_build_stage_a_context` helper: `dbex/nanobrag_refinement.py:490-652`
- refGeom fixture paths: `tests/dbex/fixtures/refGeom/`

## If Blocked

If reproducer script errors or import failures (Path C/D):
1. Capture full error traceback in `reproducer_error.txt`
2. Write `decision.md` documenting blocker (import failures, missing deps, or implementation bug)
3. Propose next steps: either (a) debug reproducer and rerun, or (b) skip reproducer and proceed to direct source inspection per Galph's Option B
4. Document block in `summary.md` and commit diagnostic artifacts
5. Next loop: Galph reviews and decides escalation path (fix reproducer OR source inspection)

## Next Up

If reproducer FAILS (Path A — nanobrag_torch bug confirmed):
- **Next Loop (ready_for_implementation)**: Inspect nanobrag_torch source (`Simulator.run()`, `get_structure_factor()`), draft targeted patch, test patch in isolation, validate both tests PASS, OR defer CPU fallback support and document limitation

If reproducer PASSES (Path B — dbex bug):
- **Next Loop (gathering_evidence)**: Investigate dbex warm cache cloning, compare context outputs, check device transfers, identify dbex-specific bug

## Doc Sync Plan

None — reproducer script is analysis tool, no tests modified.

## Normative References

- See `docs/spec-db-core.md` for HKL grid semantics and structure factor lookup requirements
- See `docs/spec-db-runtime.md` for device neutrality requirements (CPU simulator SHOULD work identically to CUDA)
- See `POLICY-001` in `docs/findings.md` for Environment Freeze exception criteria (targeted bugfixes to local source permitted when blocking critical paths)
