# Helper 3 Extraction Summary

**Date:** 2025-11-23T060000Z
**Loop:** i=194 (ralph)
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop3

## Extracted Helper

**Function:** `_run_stage_a_lbfgs`
**Location:** dbex/nanobrag_refinement.py:1729-1884 (added after `_build_stage_a_lbfgs_closure`)
**Line Range (Source):** 2625-2734 (original inline location in run_nanobrag_refinement)
**Line Count:** ~156 lines (including signature, docstring, variable unpacking, try/except blocks, fallback logic, telemetry updates, return statement)

## Parameters (14 total)

1. compute_loss: Callable (from helper 2)
2. closure: Callable (from helper 2)
3. optimizer: torch.optim.LBFGS (from helper 1)
4. params: List[Parameter] (from helper 1)
5. telemetry_state: Dict[str, Any] (from helper 1)
6. config: RefinementConfig
7. canonical_baseline: Dict[str, Any] (from run_nanobrag_refinement)
8. full_stage_a_indices: List[int] (from run_nanobrag_refinement)
9. log_scale (Parameter from helper 1)
10. log_cell_a_delta, log_cell_b_delta, log_cell_c_delta (Parameters from helper 1)
11. angle_alpha_raw, angle_beta_raw, angle_gamma_raw (Parameters from helper 1)
12. orientation_vec (Parameter from helper 1)
13. device
14. dtype

## Variables Unpacked from telemetry_state (9 total)

- iteration_count
- loss_trace_full
- chi_squared_trace_full
- chi_squared_best
- masked_mse_trace_full
- masked_mse_best
- best_loss_full
- perf_validation_runs
- best_params_snapshot (via .get())

## Mutations to telemetry_state

The helper mutates the following telemetry_state dict fields:
- loss_trace_full (appends final iteration)
- chi_squared_trace_full (appends final iteration)
- chi_squared_best (updates if new best)
- masked_mse_trace_full (appends final iteration)
- masked_mse_best (updates if new best)
- best_loss_full (updates if new best)
- best_params_snapshot (updates if new best)
- perf_validation_runs (increments for final validation)

All mutations are written back to telemetry_state dict before return.

## Mutations to canonical_baseline

The helper mutates canonical_baseline dict (passed by reference):
- chi_squared (updated with final chi² value)
- iteration (updated with final iteration count)

These mutations are visible to caller via dict reference (no explicit return needed).

## Parameter Mutations (Exception Path)

On exception, if best_params_snapshot exists, the helper restores parameter tensors:
- log_scale.data
- log_cell_a_delta.data, log_cell_b_delta.data, log_cell_c_delta.data
- angle_alpha_raw.data, angle_beta_raw.data, angle_gamma_raw.data
- orientation_vec.data

## Return Value

Tuple of 5 elements:
1. status: str ("ok", "early_stop", or "error")
2. message: str (convergence message or error message)
3. final_chi_squared_value: Optional[float]
4. final_masked_mse_value: Optional[float]
5. best_params_snapshot: Optional[Dict[str, Any]]

## Logic Blocks Preserved

- [x] optimizer.step(closure) execution (line 1770)
- [x] Final full validation with compute_loss (lines 1772-1811)
- [x] Chi² and MSE trace appends (lines 1778-1781)
- [x] Best loss tracking for both metrics (lines 1783-1789)
- [x] Best params snapshot capture (lines 1791-1808)
- [x] Canonical baseline updates (lines 1809-1811)
- [x] Convergence check (≥0.2% improvement gate) (lines 1813-1821)
- [x] Exception handler with best snapshot restoration (lines 1823-1835)
- [x] Fallback chi² trace population (lines 1837-1851)
- [x] Fallback MSE trace population (lines 1853-1862)
- [x] Canonical baseline fallback population (lines 1864-1871)
- [x] Telemetry state updates (lines 1873-1880)

## Comments Preserved

- [x] `# PERF-WARM-SIM-001` (line 1773)
- [x] `# Deprecated legacy field` (lines 1778, 1784)
- [x] `# PHYSICS-LOSS-001: Record both metrics` (lines 1779, 1785)
- [x] `# PHYSICS-LOSS-001: Track best for both metrics` (line 1785)
- [x] `# Compute misset XYZ for final snapshot (TORCH-REFINE-002)` (line 1792)
- [x] `# Check convergence: did we achieve ≥0.2% improvement?` (line 1813)
- [x] `# Use best snapshot if available` (line 1826)
- [x] `# Update telemetry_state (mutations visible to caller via dict reference)` (line 1873)
- [x] `# Canonical_baseline mutations are visible via dict reference (no need to return)` (line 1882)

## Implementation Notes

1. **Pure extraction**: No logic changes, lines 2625-2734 copied from run_nanobrag_refinement inline code
2. **Variable unpacking**: Added explicit unpacking of 9 variables from telemetry_state dict at function start
3. **Telemetry updates**: Added explicit dict writes for all mutated telemetry fields before return (lines 1873-1880)
4. **Helper not wired**: The helper exists but is NOT called by run_nanobrag_refinement yet (no behavior change)
5. **All comments preserved**: TORCH-REFINE-*, PHYSICS-LOSS-*, PERF-* annotations kept intact
6. **No new imports**: All imports remain as they were in the original code

## Next Steps (Same Loop i=194)

Refactor `run_nanobrag_refinement` to call all three helpers (~1974 lines → ~50 lines orchestration), update final Bragg generation to use dicts, run regression guard test_stage_a_expansion.
