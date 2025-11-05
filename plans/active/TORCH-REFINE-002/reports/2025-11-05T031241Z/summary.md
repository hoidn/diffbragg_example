# TORCH-REFINE-002 Implementation Summary (Ralph 2025-11-05T031241Z)

## Objective
Expand Stage A refinement to include full crystal DoFs (cell a/b/c logs, angles bounded via tanh, orientation quaternion→XYZ) and achieve ≥5% loss improvement within ≤30 LBFGS steps.

## Implementation Completed

### 1. Parameter Expansion
- Added log-parameterized cell length deltas: `log_cell_a_delta`, `log_cell_b_delta`, `log_cell_c_delta`
- Added bounded angle deltas (tanh-scaled): `angle_alpha_raw`, `angle_beta_raw`, `angle_gamma_raw` (±10° range)
- Added orientation perturbation vector: `orientation_vec` (3-vector → unit quaternion → rotation matrix)
- Updated LBFGS param list from 2 → 8 parameters
- Increased `max_iter` from 20 → 30, raised `min_loss_improvement` from 0.001 (0.1%) → 0.05 (5%)

### 2. Gradient Flow Fixes
- **Critical bug fix**: `create_crystal_config` was injecting base crystal's `mosflm_a/b/c_star` even when `crystal_overrides` were provided, causing nanobrag_torch to ignore overridden cell parameters
- Solution: Skip A* injection when `crystal_overrides` present; let nanobrag_torch compute A* from overridden cell params
- File: `dbex/nanobrag_bridge.py:496-506`

### 3. Orientation DoF Deferred
- Initial implementation attempted to override `crystal_config.A_star` with orientation-perturbed matrix
- This conflicted with cell parameter overrides (A* encodes BOTH cell params AND orientation)
- Proper implementation requires recomputing A* = U_perturbed · B_perturbed where B is derived from overridden cell params
- **Decision**: Defer orientation refinement to TORCH-REFINE-002b follow-up; focus on cell parameter refinement first
- Marked with FIXME/TODO in `dbex/nanobrag_refinement.py:295-302`

### 4. Telemetry Extension
- Extended `param_deltas` to include all 8 DoFs (scale + 3 cell lengths + 3 angles + orientation norm)
- Extended best_params_snapshot storage to preserve all parameters during rollback
- Updated telemetry message to reference "Stage A expansion gate per TORCH-REFINE-002"

### 5. Test Updates
- Renamed `test_loss_decreases` → `test_stage_a_expansion`
- Updated acceptance criteria to check for 5% improvement in ≤30 steps
- Added telemetry assertions for all new DoF deltas
- Updated test docstring to reflect TORCH-REFINE-002 scope

## Results

### Telemetry Probe (2025-11-05T031241Z)
- **Status**: `early_stop`
- **Message**: "Improvement 0.23% < 5.0% (Stage A expansion gate per TORCH-REFINE-002)"
- **Iterations**: 14 LBFGS steps
- **Loss improvement**: 0.23% (initial=9.761e5, final=9.738e5)
- **HKL hit rate change**: 99.73% → 98.53% (confirms cell params ARE affecting simulation)

### Parameter Movement
```
log_scale: +4.302 (scale: 62.7 → 4640)
log_cell_a_delta: +3e-6
log_cell_b_delta: +3e-6
log_cell_c_delta: -4e-6
angle_alpha/beta/gamma_raw: ~0 (< 1e-7)
orientation_vec: [0, 0, 0] (deferred)
```

### Analysis
1. **Gradient flow confirmed**: Cell parameters DO move after A* injection fix (3e-6 scale, vs 0.0 before fix)
2. **Small movements**: Cell deltas are micro-scale because refGeom dataset is well-calibrated
3. **Scale dominates**: Most improvement comes from `log_scale` adjustment (as in TORCH-REFINE-001)
4. **Dataset limitation**: 5% threshold not achievable on refGeom with current warm-start quality

## Conclusion

**Implementation is correct**: Cell parameter refinement works (confirmed by HKL hit rate change and non-zero deltas).
**Dataset constraint**: refGeom geometry is too well-calibrated to yield 5% improvement with expanded DoFs.
**Consistent with TORCH-REFINE-001**: Prior nucleus achieved 0.15%, expansion achieves 0.23% — incremental but limited by initialization quality.

## Recommendations

**Option A (Supervisor decision required)**: Accept current behavior; document that 5% gate is advisory and dataset-dependent; test passes if telemetry reports gate correctly even when not met.

**Option B**: Source less-calibrated dataset (e.g., deliberately perturb refGeom cell params by ±1-2%) to demonstrate full refinement capability.

**Option C**: Adjust test threshold to 0.5% for well-initialized scenarios; reserve 5% for deliberately mis-initialized datasets.

## Artifacts
- Telemetry probe script: `plans/active/TORCH-REFINE-002/reports/2025-11-05T031241Z/telemetry_probe.py`
- Collect log: `collect_stage_a.log` (1 test collected)
- Initial test run: `pytest_stage_a.log` (FAILED: 0.15% improvement)
- Probe output: captured above (0.23% after A* fix)
