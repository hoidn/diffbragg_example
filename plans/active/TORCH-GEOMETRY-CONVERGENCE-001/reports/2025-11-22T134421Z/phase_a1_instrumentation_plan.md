# Phase A1: Instrumentation Plan — Quaternion U-Matrix Telemetry

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** A1 (Instrumentation Design)
**Date:** 2025-11-22
**Target:** `dbex/nanobrag_refinement.py:build_stage_a_lbfgs_closure` (U-matrix path, lines ~968-1116)

## Objective

Instrument the quaternion U-matrix refinement closure to capture per-step telemetry during Adam optimization, enabling Phase A2-A6 to diagnose the root cause of catastrophic convergence failure (χ² +125,648%, CC→-0.045).

---

## Telemetry Specification

### 1. Per-Step Parameter Values

Capture at the **start** of each closure call (before forward pass):

| Parameter | Source Variable | Description | Shape | Notes |
|-----------|----------------|-------------|-------|-------|
| `q_params` | `q_params` tensor | Quaternion parameters (4-element) | (4,) | Raw quaternion before normalization |
| `q_norm_value` | `torch.norm(q_params)` | Quaternion norm (should ≈1.0) | scalar | Monitor constraint drift |
| `log_scale` | `log_scale` tensor | Log-space scale parameter | scalar | Shared with cell+misset path |
| `step_index` | Closure call counter | Iteration number (0-indexed) | int | Track temporal progression |

**Serialization:** Detach tensors, convert to Python floats/lists for JSON emission

### 2. Per-Step Gradient Norms

Capture **after** backward pass (inside closure, after `loss.backward()`):

| Metric | Source | Description | Notes |
|--------|--------|-------------|-------|
| `grad_q_norm` | `torch.norm(q_params.grad)` | L2 norm of quaternion gradient | Check for explosion/vanishing |
| `grad_q_max` | `torch.max(torch.abs(q_params.grad))` | Element-wise max absolute gradient | Identify component-specific issues |
| `grad_q_min` | `torch.min(torch.abs(q_params.grad))` | Element-wise min absolute gradient | Detect imbalance across components |
| `grad_log_scale` | `torch.abs(log_scale.grad)` | Absolute value of scale gradient | Correlate with REFINE-001 pathology |
| `grad_has_nan` | `torch.isnan(q_params.grad).any()` | Boolean flag for NaN in quaternion grad | Critical failure indicator |
| `grad_has_inf` | `torch.isinf(q_params.grad).any()` | Boolean flag for Inf in quaternion grad | Critical failure indicator |

**Serialization:** Convert to Python floats/bools for JSON emission

### 3. Per-Step Loss Components

Capture **after** variance-weighted loss computation (line ~1114):

| Metric | Source | Description | Notes |
|--------|--------|-------------|-------|
| `chi_squared` | `chi_squared_loss.item()` | Total variance-weighted chi-squared | Primary convergence metric |
| `masked_mse` | `masked_mse_loss.item()` | Masked MSE (numerator/denominator) | Secondary metric |
| `masked_pixels` | `masked_pixels_total` | Count of pixels in loss mask | Track coverage |
| `clamped_pixels` | `clamped_pixels_total` | Count of pixels where sigma_floor applied | Variance floor interaction (PHYSICS-LOSS-002) |

**Clamp Fraction Calculation:**
```python
clamp_fraction = clamped_pixels_total / max(masked_pixels_total, 1)
```

### 4. Per-Step Variance Component Analysis

Capture **during** loss computation (requires instrumentation of `_compute_variance_weighted_loss` helper or inline logging):

| Metric | Source | Description | Notes |
|--------|--------|-------------|-------|
| `i_model_min` | `torch.min(bragg_scaled)` | Minimum forward model intensity | Check for negative/anomalous values |
| `i_model_median` | `torch.median(bragg_scaled[mask_subset])` | Median intensity (masked pixels) | Central tendency |
| `i_model_max` | `torch.max(bragg_scaled)` | Maximum forward model intensity | Check for outliers |
| `i_model_std` | `torch.std(bragg_scaled[mask_subset])` | Standard deviation (masked) | Dispersion |
| `v_denom_min` | Variance denominator min | Minimum variance weight | Check for near-zero (→ inf weights) |
| `v_denom_median` | Variance denominator median | Central variance weight | Typical variance scale |
| `v_denom_max` | Variance denominator max | Maximum variance weight | Check for outliers |

**Note:** Variance denominator computed inline during loss calculation; may require temporary storage or second pass to extract histograms without mutating production logic.

### 5. Per-Step Forward Metrics (Optional)

Capture **if low overhead** (may defer to Phase A3 if telemetry slows convergence):

| Metric | Source | Description | Notes |
|--------|--------|-------------|-------|
| `median_roi_cc` | Correlation coefficient | Median ROI CC across processed regions | Expensive (requires per-ROI scoring); skip unless trivial to compute |

**Decision:** SKIP median_roi_cc in Phase A1; use chi_squared + masked_mse as convergence proxies. If Phase A2 telemetry suggests first divergence is subtle, add CC in subsequent runs.

---

## Injection Points

### Primary Instrumentation Location
**File:** `dbex/nanobrag_refinement.py`
**Function:** `build_stage_a_lbfgs_closure` (inner closure function `closure_impl`)
**Lines:** ~950-1200 (U-matrix path starts at line 968)

### Specific Injection Sites

#### 1. Parameter Logging (After Line 971)
```python
# After: q_norm = q_params / torch.norm(q_params)
q_norm_value = torch.norm(q_params).item()
telemetry_params = {
    'q_params': q_params.detach().cpu().tolist(),
    'q_norm_value': q_norm_value,
    'log_scale': log_scale.item(),
}
```

#### 2. Gradient Logging (After Loss Backward, ~Line 1180)
```python
# After: chi_squared_loss.backward() or combined_loss.backward()
telemetry_gradients = {
    'grad_q_norm': torch.norm(q_params.grad).item() if q_params.grad is not None else None,
    'grad_q_max': torch.max(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
    'grad_q_min': torch.min(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
    'grad_log_scale': torch.abs(log_scale.grad).item() if log_scale.grad is not None else None,
    'grad_has_nan': torch.isnan(q_params.grad).any().item() if q_params.grad is not None else False,
    'grad_has_inf': torch.isinf(q_params.grad).any().item() if q_params.grad is not None else False,
}
```

#### 3. Loss Component Logging (After Line 1114)
```python
# After: chi_squared_loss = chi_squared_accum
clamp_fraction = clamped_pixels_total / max(masked_pixels_total, 1)
telemetry_loss = {
    'chi_squared': chi_squared_loss.item(),
    'masked_mse': masked_mse_loss.item() if masked_pixels_total > 0 else 0.0,
    'masked_pixels': masked_pixels_total,
    'clamped_pixels': clamped_pixels_total,
    'clamp_fraction': clamp_fraction,
}
```

#### 4. Variance Component Logging (Inside ROI Loop, After Line 1096)
```python
# After: bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)
# Accumulate variance histograms across ROIs (or log per-ROI and aggregate later)
i_model_values = bragg_scaled[mask_subset]
telemetry_variance_roi = {
    'i_model_min': torch.min(bragg_scaled).item(),
    'i_model_median': torch.median(i_model_values).item() if i_model_values.numel() > 0 else 0.0,
    'i_model_max': torch.max(bragg_scaled).item(),
    'i_model_std': torch.std(i_model_values).item() if i_model_values.numel() > 1 else 0.0,
}
# Variance denominator: V = max(I_model + sigma_readout^2, sigma_floor^2)
# Computed inside _compute_variance_weighted_loss; may require helper return values or inline logging
```

**Challenge:** Variance denominator is computed inside `_compute_variance_weighted_loss` helper. Options:
- **A)** Extend helper to return variance component stats alongside loss (preferred, minimal overhead)
- **B)** Inline the variance computation in the closure for U-matrix path only (duplicates logic, but preserves encapsulation)
- **C)** Recompute variance denominator after loss for logging only (wastes computation but avoids helper mutation)

**Recommendation:** Option A — extend `_compute_variance_weighted_loss` signature to optionally return `v_denom_stats` dict when a flag is set, e.g., `return_variance_stats=True`.

---

## Emission Format

### File Naming Convention
```
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/<timestamp>/telemetry_step_{i}.json
```
Where `{i}` is 0-indexed step number (0, 1, 2, ..., 9 for 10-step run).

### JSON Schema
```json
{
  "step_index": 0,
  "parameters": {
    "q_params": [0.25, 0.25, 0.25, 0.866],
    "q_norm_value": 1.0,
    "log_scale": 8.314
  },
  "gradients": {
    "grad_q_norm": 123456.78,
    "grad_q_max": 98765.43,
    "grad_q_min": 12345.67,
    "grad_log_scale": 876543.21,
    "grad_has_nan": false,
    "grad_has_inf": false
  },
  "loss": {
    "chi_squared": 1133420.75,
    "masked_mse": 0.123,
    "masked_pixels": 13084,
    "clamped_pixels": 0,
    "clamp_fraction": 0.0
  },
  "variance": {
    "i_model_min": 0.0,
    "i_model_median": 12.34,
    "i_model_max": 567.89,
    "i_model_std": 45.67,
    "v_denom_min": 1.0,
    "v_denom_median": 15.6,
    "v_denom_max": 890.12
  }
}
```

### Emission Timing
- Write JSON file **at the end of each closure call** (after backward pass, before return)
- Use step counter (closure-scoped mutable list `[0]`) to track iteration number
- Increment counter after emission

---

## Constraints & Guardrails

### 1. Observation Only (No Logic Mutation)
- Telemetry MUST NOT alter production code behavior
- All logging operations must use `.detach()` or `.item()` to prevent autograd graph pollution
- Do NOT add print statements to stdout (interferes with pytest capture); emit JSON only

### 2. Device/Performance
- Run on CPU (`--device cpu`) to avoid CUDA sync overhead
- Disable torch.compile (`NANOBRAGG_DISABLE_COMPILE=1`) to prevent telemetry from being compiled out
- Accept ~10-20% performance penalty for telemetry; 10-step run should complete in <5 minutes on CPU

### 3. Failure Handling
- If gradient is None (not yet computed), log as `null` in JSON
- If variance component extraction fails (e.g., empty mask), log 0.0 or skip that metric
- If file write fails, do NOT crash the closure; log error to stderr and continue (optimization must complete for data to be useful)

### 4. Environment Setup
```bash
export KMP_DUPLICATE_LIB_OK=TRUE  # Suppress Intel MKL warnings
export NANOBRAGG_DISABLE_COMPILE=1  # Disable torch.compile
```

---

## Implementation Strategy

### Phase A1 Code Changes (Minimal, Reversible)

1. **Add telemetry flag to `RefinementConfig`** (optional, for feature gating):
   ```python
   enable_convergence_telemetry: bool = False
   convergence_telemetry_dir: Optional[str] = None
   ```

2. **Extend `_compute_variance_weighted_loss` signature**:
   ```python
   def _compute_variance_weighted_loss(
       bragg_scaled, target, mask, sigma_readout, sigma_floor_sq,
       return_variance_stats=False
   ):
       # ... existing logic ...
       if return_variance_stats:
           v_denom_values = V_denom[mask]
           variance_stats = {
               'v_denom_min': torch.min(v_denom_values).item(),
               'v_denom_median': torch.median(v_denom_values).item(),
               'v_denom_max': torch.max(v_denom_values).item(),
           }
           return chi_sq_loss, mse_loss, masked_pixels, clamped_pixels, variance_stats
       else:
           return chi_sq_loss, mse_loss, masked_pixels, clamped_pixels
   ```

3. **Inject telemetry into U-matrix closure** (lines ~968-1116):
   - Add step counter: `closure_call_count = [0]` (before closure definition)
   - After line 971: Log parameters
   - After line 1114: Log loss components
   - Inside ROI loop (after line 1096): Log I_model stats
   - After backward pass (~line 1180): Log gradients
   - Before return: Write JSON file, increment counter

4. **Conditional gating** (if using config flags):
   ```python
   if config.enable_convergence_telemetry and config.convergence_telemetry_dir:
       # ... emit telemetry ...
   ```

### Phase A2 Execution Command

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T<next_timestamp>Z/
```

**Note:** If `stage_a_mapping_adam_debug.py` does not expose telemetry flags, modify the script to pass `enable_convergence_telemetry=True` and `convergence_telemetry_dir=<out-dir>` to `RefinementConfig` before building the closure.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Telemetry overhead slows convergence test → timeout | Run on CPU with conservative 10-minute timeout; skip expensive metrics (median_roi_cc) in Phase A1 |
| Variance component extraction requires helper mutation | Use optional return value pattern (backward compatible) |
| Telemetry breaks autograd graph → NaN gradients | Always detach tensors before JSON serialization; validate gradients are non-None before logging |
| JSON write fails → no telemetry data | Wrap file writes in try/except; log error to stderr but continue closure execution |
| Step counter out of sync with optimizer → wrong step labels | Use closure-scoped mutable list incremented after each call; validate step_index monotonicity in Phase A3 analysis |

---

## Success Criteria

Phase A1 instrumentation is complete when:
1. Telemetry code is injected into U-matrix closure path (lines ~968-1116)
2. `_compute_variance_weighted_loss` extended to return variance stats (optional flag)
3. Phase A2 execution produces 10 JSON files (`telemetry_step_0.json` through `telemetry_step_9.json`)
4. All JSON files contain non-null values for: `q_params`, `q_norm_value`, `log_scale`, `chi_squared`, `masked_pixels`, `clamped_pixels`, gradient norms
5. No regressions in cell+misset path (telemetry gated to U-matrix branch only)

---

## Next Steps After A1

- **Phase A2:** Execute instrumented run, capture 10 telemetry JSON files
- **Phase A3:** Analyze telemetry to identify first divergence step (χ² spike, CC drop, gradient explosion, NaN/inf)
- **Phase A4 (if needed):** Finite-difference gradient validation at first-divergence step
- **Phase A5:** Variance/loss component analysis (histograms, pathological distributions)
- **Phase A6:** Synthesize root cause determination (H1/H2/H3/H4), recommend Phase B test

---

## Appendix: Example Telemetry Output (Step 0)

```json
{
  "step_index": 0,
  "parameters": {
    "q_params": [0.0, 0.0, 0.0, 1.0],
    "q_norm_value": 1.0,
    "log_scale": 8.314
  },
  "gradients": {
    "grad_q_norm": 288000000.0,
    "grad_q_max": 216000000.0,
    "grad_q_min": 61600000.0,
    "grad_log_scale": 428000.0,
    "grad_has_nan": false,
    "grad_has_inf": false
  },
  "loss": {
    "chi_squared": 1133420.75,
    "masked_mse": 0.0867,
    "masked_pixels": 13084,
    "clamped_pixels": 0,
    "clamp_fraction": 0.0
  },
  "variance": {
    "i_model_min": 0.0,
    "i_model_median": 10.5,
    "i_model_max": 450.2,
    "i_model_std": 35.8,
    "v_denom_min": 1.0,
    "v_denom_median": 12.3,
    "v_denom_max": 560.7
  }
}
```

(Note: Gradient values are hypothetical examples; actual values from Phase A2 will guide root cause determination.)
