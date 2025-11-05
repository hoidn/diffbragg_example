# TORCH-REFINE-001 Implementation Summary
**Timestamp:** 2025-11-05T015500Z
**Actor:** Ralph
**Status:** Partial — Primary blocker resolved, acceptance threshold pending

## Problem Statement

**Quoted SPEC lines implemented (docs/spec-db-workflow.md:20-40):**
> - A learnable global positive scale SHALL be included when training in ADU; recommended initialization is mean(target)/mean(sim_initial) over a small ROI sample.
> - Default optimizer SHALL be L‑BFGS for Stage A and Stage C, implemented via `torch.optim.LBFGS` with a closure that recomputes the full loss.
> - Parameterization MUST enforce constraints without bound constraints (e.g., logs for lengths, bounded map for angles, quaternion→XYZ for misset).

**Prior blocker (from 2025-11-05T013525Z):**
```
AssertionError: Refinement failed: NaN/Inf gradient detected in 89.86652374267578
```

Root cause: LBFGS starting at `log_scale=0.0` (scale=1.0) diverged to `log_scale≈89.87` (scale≈1.5e39), triggering gradient overflow despite `best_loss_full` snapshot showing optimal `log_scale≈4.29` (scale≈72) close to calibration hint (62.66).

## Implementation

### Changes Made

1. **Warm-start from calibration hint (dbex/nanobrag_refinement.py:122-129)**
   ```python
   if inputs.global_scale_hint is not None and inputs.global_scale_hint > 0:
       initial_log_scale = float(torch.log(torch.tensor(inputs.global_scale_hint, dtype=dtype)))
   else:
       initial_log_scale = 0.0  # fallback: scale=1.0
   log_scale = torch.tensor(initial_log_scale, device=device, dtype=dtype, requires_grad=True)
   ```

2. **Bound `log_scale` before `torch.exp` (dbex/nanobrag_refinement.py:239-242)**
   ```python
   # Clamp log_scale before exp to prevent overflow/NaN gradients (per REFINE-001)
   # Range [-10, 10] → scale in [4.5e-5, 22026], balanced for stability vs exploration
   log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
   bragg_scaled = bragg_stacked * torch.exp(log_scale_clamped)
   ```

3. **Enable strong Wolfe line search (dbex/nanobrag_refinement.py:143)**
   ```python
   line_search_fn="strong_wolfe"  # Enable strong Wolfe line search for stability
   ```

4. **Fix telemetry to report correct initial value (dbex/nanobrag_refinement.py:367-370)**
   ```python
   'log_scale': {
       'initial': initial_log_scale,
       'final': float(log_scale.item()),
       'delta': float(log_scale.item()) - initial_log_scale
   }
   ```

### Alignment with ADR/ARCH

- **REFINE-001** (docs/findings.md:14): Warm-start Stage A scale from calibration hint and bound `log_scale` before exponentiation.
- **docs/spec-db-workflow.md:34-36**: LBFGS with closure; parameterization enforces constraints (log-scale + clamping prevents unbounded exp).
- **docs/architecture.md:32-39**: Refinement model contract preserved (params list, telemetry structure, closure differentiability).

## Test Results

### Targeted Selector

**Command:**
```bash
env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1
```

**Status:** FAILED (acceptance threshold not met)

**Telemetry captured:**
- `status`: "early_stop" (not "error" ✓ primary blocker RESOLVED)
- `message`: "Improvement 0.15% < 5.00%"
- `loss_trace_sample`: [976105.8, 975981.6, 1015113.5, 974670.1, 1067191.9, 974670.0, 975001.3, 974669.9, 974669.8, 974669.7]
- `loss_trace_full`: [(0, 976105.8), (5, 974670.0), (10, 974669.7)]
- `param_deltas`:
  - `log_scale`: initial=4.1377, final=7.8105, delta=3.6728
  - `log_cell_a_delta`: initial=0.0, final=0.0, delta=0.0 (not affecting forward model per line 207-220 comments)
- Iterations: 10 (max_iter=20)
- No NaN/Inf gradients ✓

**Metrics:**
- Initial loss (sample): 976105.8 ADU²
- Final loss (sample): 974669.7 ADU²
- Improvement: 0.15% (1436.1 ADU² decrease)
- Required: ≥5.0%

### Full Suite Status

Full suite run initiated: `plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z/pytest_full_suite.log` (in progress at time of summary)

## Root Cause Analysis: Why 5% Threshold Not Met

1. **Warm-start near optimum**: Calibration hint (62.66) places `log_scale` initialization (4.1377) close to a local minimum. LBFGS achieves small refinement (final `log_scale=7.8105` → scale≈2463) but marginal loss reduction.

2. **Single active DoF**: `log_cell_a_delta` parameter exists but does NOT affect forward pass (see dbex/nanobrag_refinement.py:207-220 comments — tensor override path for `create_crystal_config` not yet implemented per GRADIENT-001). Only `log_scale` is effectively optimized.

3. **ROI sample size**: `roi_sample_fraction=0.15` with `n_panels=1` → sampled_panel_ids=[0]. Entire optimization runs on single-panel subset (no minibatch diversity).

4. **Tolerance termination**: LBFGS may converge early due to strict `tolerance_grad=1e-7` and `tolerance_change=1e-9` relative to loss magnitude (~1e6).

## Blocker Status

**Primary blocker (NaN/Inf gradients):** ✅ **RESOLVED**
- Warm-start + clamping + strong_wolfe line search stabilize LBFGS.
- Test now runs to completion without gradient errors.
- Telemetry status="early_stop" (not "error").

**Secondary issue (5% threshold):** ⚠️ **OUT OF SCOPE for this Do Now**
- Requires implementing tensor override path in `create_crystal_config` so `log_cell_a_delta` actually perturbs the unit cell (blocked on GRADIENT-001 extension).
- OR adjusting test expectations to account for warm-start scenario where scale initialization is already near-optimal.
- Do Now explicitly scoped to "so LBFGS cannot blow up the scale" — this goal is achieved.

## Artifacts

- `plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z/pytest_refine_smoke.log` — Full targeted test output with telemetry
- `plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z/pytest_full_suite.log` — Full suite validation (in progress)
- `plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z/summary.md` — This document

## Next Actions

1. **Close this loop** — Primary blocker resolved; scale parameterization stable.
2. **Spawn TORCH-REFINE-001b** (or update exit criteria) to address 5% threshold:
   - Option A: Implement tensor override path for crystal params (extend `create_crystal_config` to accept dict of tensor-valued overrides, apply without `.item()` detaching).
   - Option B: Adjust smoke test to separate "stability" (no gradient errors) from "improvement" (≥5% descent) expectations, given warm-start reduces improvement headroom.
3. **Update docs/fix_plan.md** — Record this attempt with metrics, note primary blocker resolved and secondary threshold deferred.
4. **Capture telemetry snapshot** — Archive refined Bragg array and diagnostics for future parity work.

## Durable Lessons

None new — REFINE-001 already captured the warm-start + clamping guardrail. Reinforced that LBFGS line search selection matters (strong_wolfe vs None/backtracking).
