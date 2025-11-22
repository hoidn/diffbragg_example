# Phase B Test Protocol

## Hypotheses Prioritization

Based on Phase A evidence (initialization correct, Adam convergence catastrophic), testing order:

1. **Test B1: LBFGS Optimizer** (H1 — optimizer incompatibility)
   - Rationale: LBFGS eliminates momentum accumulation (H4), uses line search to avoid exploding steps (H3), proven for scale-only per REFINE-001
   - Expected outcome: If quaternion gradient manifold is the issue, LBFGS should converge (CC ≥ 0.99, chi² stable)
   - If successful: Skip B2/B3, proceed to Phase C fix implementation (add optimizer switch for U-matrix path)
   - If failed: Proceed to Test B2 (gradient validation + loss stability analysis)

2. **Test B2: Adam LR=1e-6 + Gradient Validation** (H1 + H3 — hyperparameter tuning + gradient pathology)
   - Rationale: Lower LR (100× smaller) may stabilize quaternion updates; gradient logging will diagnose NaN/inf/exploding
   - Expected outcome: If LR is the issue, convergence should improve; gradient telemetry will diagnose pathologies
   - If successful: Proceed to Phase C with LR tuning fix
   - If failed: Proceed to Test B3 (loss clamping + variance analysis)

3. **Test B3: Loss Clamping + Variance Analysis** (H2 — variance-weighted loss numerical instability)
   - Rationale: If variance denominator (I_model + sigma²) becomes pathological during optimization, clamp loss or increase sigma_floor
   - Expected outcome: Variance telemetry will show if V_denom→0 or residuals→inf causing loss explosion
   - If successful: Proceed to Phase C with sigma_floor tuning or loss clipping
   - If failed: Escalate to hybrid parameterization (PARITY-003 Option 1: cell+quaternion+isotropic scale)

## Test B1 Implementation Plan

### Changes Required
Edit `dbex/nanobrag_refinement.py` in `run_nanobrag_refinement` function:
- Add config flag: `use_lbfgs_for_u_matrix: bool = False` to `RefinementConfig`
- In U-matrix optimizer selection block (~line 810-835):
  ```python
  if config.use_u_matrix_parameterization and config.use_lbfgs_for_u_matrix:
      # Test B1: LBFGS for quaternion U-matrix refinement
      optimizer = torch.optim.LBFGS(
          [q_params, log_scale],
          lr=1.0,  # LBFGS uses line search; LR=1.0 is standard
          max_iter=20,
          tolerance_grad=1e-7,
          tolerance_change=1e-9,
          history_size=10,
          line_search_fn='strong_wolfe'
      )
      logger.info("Stage A: Using LBFGS optimizer for U-matrix path (Test B1)")
  elif config.use_u_matrix_parameterization:
      # Default: Adam (known to fail catastrophically)
      optimizer = torch.optim.Adam([q_params, log_scale], lr=1e-4)
      logger.info("Stage A: Using Adam optimizer for U-matrix path")
  else:
      # Cell+misset default path (unchanged)
      optimizer = torch.optim.Adam(params, lr=1e-4)
  ```

### Test Execution
Run `stage_a_mapping_adam_debug.py` with LBFGS override:

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/stage_a_lbfgs_test.log
```

**Note:** Script must be extended to accept `--use-lbfgs` flag and pass it to `RefinementConfig(use_lbfgs_for_u_matrix=True)`.

### Success Criteria
- **Convergence SUCCESS:** `block_dof_results_lbfgs.json` shows:
  - `A_scale_only.cc_summary.median_after ≥ 0.99` (retain high correlation)
  - `A_scale_only.chi_squared.after / .before ≤ 1.005` (chi² stable or improving, ≤0.5% drift)
  - No NaN/inf in telemetry
- **Convergence FAILURE:** Same catastrophic signature (CC collapse, chi² explosion) → Proceed to Test B2

### Artifacts
- `phase_b_test_protocol.md` (this document)
- `phase_b_test1_lbfgs_results.json` (convergence metrics: chi² before/after, CC before/after, optimizer config)
- `stage_a_lbfgs_test.log` (full run log with LBFGS line search iterations)
- `telemetry/telemetry_step_{0..9}.json` (per-step parameter/gradient/loss telemetry)
- `block_dof_results_lbfgs.json` (final DoF results for A_scale_only variant)
