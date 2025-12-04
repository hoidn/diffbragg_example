# Boundary Bisection Plan — HKL Query Coverage

**Goal:** Determine whether the Stage A simulator is sampling the intended HKL lattice or drifting into an offset/rotated grid, causing the intensity redistribution captured in the transformation ledger.

1. **Tap Point:** Stage A warm-cache simulators (`StageAContext.simulators`) and the mapping reference path (`simulate_forward_once`).  
   - Enable existing nanobrag_torch `collect_hkl_stats` debug hook via `_build_stage_a_context(..., debug_config={'collect_hkl_stats': True})` and `simulate_forward_once(..., debug_config={'collect_hkl_stats': True})`.

2. **Evidence to Capture:**  
   - Per-panel `h_min/h_max`, `k_min/k_max`, `l_min/l_max`, and in/out-of-bounds counters.  
   - Aggregate hit-rate comparison against the populated HKL grid metadata (expected bounds from `build_structure_factor_grid`).  
   - Same detector+calibration bundle used for the reflection ledger to avoid cross-fixture drift.

3. **Decision Gate:**  
   - If hit rate ≪100 % or ranges sit outside the populated HKL grid, root cause = simulator projection bug ⇒ escalate to nanobrag_torch or coordinate transform audit.  
   - If hit rate ≈100 % yet ROI mismatches persist, the fault is inside the physics kernel (e.g., missing Lorentz/polarization or amplitude normalization); prepare to instrument simulator outputs per HKL.

4. **Implementation Hook:** extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` with `--collect-hkl-stats` so the same probe run produces Stage A/mapping HKL telemetry alongside the reflection ledger.

5. **Validation:** rerun the enhanced probe (baseline + perturbed geometry) and DB-AT-028/029 selectors under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/` to tie HKL stats directly to the failing selectors.
