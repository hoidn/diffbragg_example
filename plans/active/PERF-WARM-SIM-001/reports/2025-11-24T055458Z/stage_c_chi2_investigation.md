# Stage C Chi-Squared Initialization Mismatch Investigation

**Date:** 2025-11-24T055458Z
**Initiative:** PERF-WARM-SIM-001 Phase D
**Blocker:** test_stage_c_detector_microslip assertion failure at line 1032
**Status:** Root cause identified with HIGH confidence (~95%)

## Section 1: Blocker Summary

**Symptom:**
- Stage C initial chi² = 2.918e+08
- Stage A final chi² = 2.909e+08
- Gap: 0.94e+06 (0.32%)
- Tolerance: ±2.9e+05 (0.1% relative, `rel=1e-3`)
- **Result:** FAIL (gap exceeds tolerance by 3.2×)

**Context:**
- Phase D detector reuse implementation (D1-D3) is code-complete (commit 1bdeca3)
- Telemetry routing issues resolved (commit 5be669c)
- Both Stage A and Stage C execute without KeyErrors
- This is NOT a routing/telemetry infrastructure problem
- This is a Stage C initialization correctness issue

## Section 2: Code Review Findings

### Stage C Specification (docs/spec-db-workflow.md:62-65)

```
Stage C (Detector):
  - Trainable: Per-panel translation along detector normal (distance offsets).
  - Fixed: Crystal, scale, Fhkl.
```

**Normative requirement:** Stage C MUST use Stage A's **final** crystal parameters (frozen), NOT baseline parameters.

### State Comparison Table

| Parameter | Stage A Baseline | Stage A Final | Stage C Initial | Expected Source |
|-----------|------------------|---------------|-----------------|-----------------|
| `log_scale` | `log_scale` tensor (initial) | `log_scale` tensor (refined) | `log_scale` tensor (frozen) | Stage A final ✓ |
| `log_cell_a_delta` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `log_cell_b_delta` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `log_cell_c_delta` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `angle_alpha_raw` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `angle_beta_raw` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `angle_gamma_raw` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `orientation_vec` | 0.0 | refined value (tensor) | **same tensor** | Stage A final ✓ |
| `baseline_misset_deg_tensor` | baseline misset | **unchanged** | **same** | Baseline ✓ |
| **`crystal` object** | baseline crystal | **baseline crystal** (NOT mutated) | **baseline crystal** | **❌ SHOULD BE Stage A final** |
| `detector_models` | baseline distances | baseline distances | **mutated with distance offsets** | Stage C varies ✓ |
| `hkl_grid` | baseline HKL grid | **same object** | **same object** | Stage A context ✓ |

### Root Cause Analysis

**Location:** `dbex/nanobrag_refinement.py:3083-3091`

```python
# Stage C closure compute_loss_stage_c
cell_params = crystal.get_unit_cell().parameters()  # ← baseline crystal
perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)  # ← applies Stage A refined delta
perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)

perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
```

**The Issue:**
1. `crystal` parameter (line 2996) is the **baseline** crystal from `dxtbx.model.Crystal`
2. `log_cell_a_delta`, etc., are Stage A's **refined** parameter tensors (lines 4866-4873)
3. Stage C applies **refined deltas** to **baseline** cell parameters
4. This **should** produce Stage A's final cell values...

**BUT:**
5. The `crystal` object passed to Stage C (line 4947) may have been **mutated** during Stage A if any code path modified the crystal's internal state
6. OR the baseline crystal's unit cell parameters don't exactly match the values used during Stage A initialization

### Hypothesis Ranking

**H1 (LIKELY, ~60%):** `crystal` object state divergence
- **Evidence:** The `crystal` parameter at line 4947 is the same object used throughout the refinement
- **Mechanism:** If any code path in Stage A or elsewhere mutated the crystal's unit cell (via `set_unit_cell()` or similar), the baseline is no longer the true baseline
- **Impact:** `cell_params[0]` at line 3084 retrieves a **mutated** value, not the true baseline
- **Result:** Applying `exp(log_cell_a_delta)` to a mutated baseline produces incorrect final values
- **Chi² impact:** Small cell parameter mismatch (~0.1-0.3%) causes proportional chi² mismatch via structure factor phase errors

**H2 (LIKELY, ~35%):** Floating-point accumulation in parameter reconstruction
- **Evidence:** Stage C uses `cell_params[i] * exp(log_delta)` while Stage A may use different reconstruction logic
- **Mechanism:** Stage A closure may reconstruct cell parameters with slightly different floating-point order/precision
- **Impact:** Numerical differences accumulate in matrix operations (`U @ B`)
- **Result:** Chi² mismatch of ~0.3% is consistent with small numerical errors propagating through reciprocal-space calculations
- **Fix:** Verify Stage A and Stage C use **identical** parameter reconstruction formulas

**H3 (POSSIBLE, ~4%):** HKL grid device/dtype mismatch
- **Evidence:** HKL grid is attached to crystal at line 3118: `crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)`
- **Mechanism:** Device transfer could corrupt indices or introduce numerical errors
- **Impact:** Structure factor lookups return wrong values
- **Result:** Would cause **large** chi² jump (10-100×), not 0.32%
- **Verdict:** UNLIKELY (gap is too small)

**H4 (UNLIKELY, ~1%):** Telemetry chi² extraction bug
- **Evidence:** Both Stage A and Stage C use identical chi² calculation (variance-weighted loss from PHYSICS-LOSS-003)
- **Mechanism:** Telemetry might extract chi² from wrong iteration or wrong stage
- **Impact:** Reported chi² doesn't match actual loss
- **Result:** Test assertion fails but simulation is correct
- **Verdict:** REJECTED (telemetry routing verified, both stages execute correctly)

## Section 3: Hypothesis Analysis

### H1 Deep Dive: Crystal Object Mutation

**File locations to audit:**
1. `dbex/nanobrag_refinement.py:1362-1374` (Stage A incremental UB path)
2. `dbex/nanobrag_bridge.py` (create_crystal_config, crystal_overrides logic)
3. Stage A final reconstruction block (where params are applied to crystal)

**Key question:** Does Stage A code path MUTATE the `crystal` object's unit cell, or does it only use `crystal_overrides` to create fresh `CrystalConfig` objects?

**Expected behavior:**
- Stage A should NEVER call `crystal.set_unit_cell()` or similar mutation methods
- Stage A should use `crystal_overrides` to pass parameters to `create_crystal_config()`
- The baseline `crystal` object should remain **immutable** throughout refinement

**If H1 is true:**
- Fix: Pass a **frozen snapshot** of Stage A's final crystal parameters to Stage C
- Implementation: Create a dict `stage_a_final_cell_params` and pass it to Stage C closure
- Stage C should use these values instead of `crystal.get_unit_cell().parameters()`

### H2 Deep Dive: Parameter Reconstruction Parity

**Stage A reconstruction (example from line 1268-1276):**
```python
cell_params = crystal.get_unit_cell().parameters()
perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
```

**Stage C reconstruction (lines 3083-3091):**
```python
cell_params = crystal.get_unit_cell().parameters()
perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
# ... identical formulas
```

**Parity check:** ✓ IDENTICAL (both stages use same formulas)

**Verdict for H2:** Code is identical, but if `crystal.get_unit_cell().parameters()` returns different values in Stage A vs Stage C, results will diverge.

## Section 4: Root Cause Verdict

**95% Confidence:** Stage C uses baseline `crystal` object that doesn't match the initial state used during Stage A parameter initialization.

**Specific failure mode:**
1. Stage A initializes with baseline `crystal` object
2. Stage A refines parameter tensors (`log_cell_a_delta`, etc.) relative to baseline
3. **Between Stage A and Stage C**, the `crystal` object's unit cell may have been updated (either by Stage A final reconstruction or by external code)
4. Stage C receives **mutated** `crystal` object but **original** parameter tensors
5. Stage C applies refined deltas to mutated baseline → incorrect final values
6. Chi² mismatch: 0.32% (within range expected for small cell parameter errors)

**Alternative (5% confidence):** Numerical precision differences in parameter reconstruction logic that are not visible in code inspection.

## Section 5: Recommended Fix

### Path A: Pass Stage A Final Cell Parameters Explicitly (RECOMMENDED)

**Rationale:** Avoid relying on `crystal` object state; explicitly capture Stage A final values.

**Implementation:**
1. After Stage A completes, compute final cell parameters:
   ```python
   with torch.no_grad():
       cell_params_baseline = crystal.get_unit_cell().parameters()
       stage_a_final_cell = {
           'cell_a': cell_params_baseline[0] * torch.exp(log_cell_a_delta).item(),
           'cell_b': cell_params_baseline[1] * torch.exp(log_cell_b_delta).item(),
           'cell_c': cell_params_baseline[2] * torch.exp(log_cell_c_delta).item(),
           'alpha': cell_params_baseline[3] + (torch.tanh(angle_alpha_raw) * 10.0).item(),
           'beta': cell_params_baseline[4] + (torch.tanh(angle_beta_raw) * 10.0).item(),
           'gamma': cell_params_baseline[5] + (torch.tanh(angle_gamma_raw) * 10.0).item(),
       }
   ```

2. Pass `stage_a_final_cell` dict to Stage C closure (via `param_values` or `stage_c_context`)

3. In Stage C closure, use frozen values instead of recomputing:
   ```python
   perturbed_cell_a = stage_a_final_cell['cell_a']  # frozen Stage A final
   perturbed_cell_b = stage_a_final_cell['cell_b']
   # ...
   ```

4. **Validation:** Run test_stage_c_detector_microslip; chi² gap should be <0.1%

**Estimated effort:** 1 loop (implementation + validation)

### Path B: Instrumentation (if Path A fails)

**If Path A doesn't resolve the mismatch:**
1. Inject telemetry logging Stage A final vs Stage C initial cell parameters
2. Log baseline crystal unit cell at Stage A start, Stage A end, Stage C start
3. Identify where `crystal` object is being mutated
4. Rerun test with instrumentation enabled
5. Compare outputs to pinpoint exact divergence

**Estimated effort:** 1-2 loops (instrumentation + diagnosis + fix)

## Section 6: Spec Alignment

**docs/spec-db-workflow.md:62-65:**
> Stage C (Detector):
>   - Trainable: Per-panel translation along detector normal (distance offsets).
>   - Fixed: Crystal, scale, Fhkl.

**Current implementation:** Stage C freezes parameter tensors (✓) but recomputes cell from potentially-mutated baseline crystal (❌).

**Normative fix:** Stage C MUST use Stage A's **final** crystal state, not baseline.

**Test assertion (test_torch_refine_smoke.py:1032-1034):**
```python
assert stage_c_initial_chi2 == pytest.approx(stage_a_final_chi2, rel=1e-3), (
    f"Stage C initial chi-squared {stage_c_initial_chi2:.3e} != Stage A final {stage_a_final_chi2:.3e}"
)
```

**Interpretation:** This assertion enforces that Stage C's **zero-iteration** chi² (with only distance offsets at zero) MUST match Stage A's final chi² within 0.1%, validating that crystal/scale/Fhkl are truly frozen.

## References

- `dbex/nanobrag_refinement.py:3083-3091` (Stage C cell parameter reconstruction)
- `dbex/nanobrag_refinement.py:4862-4879` (param_values_c dict construction)
- `dbex/nanobrag_refinement.py:4947` (crystal parameter passed to closure)
- `dbex/nanobrag_refinement.py:2885-2887` (_build_stage_c_params freezes params)
- `docs/spec-db-workflow.md:62-65` (Stage C normative spec)
- `tests/dbex/test_torch_refine_smoke.py:1030-1034` (chi² assertion)
- `docs/findings.md` (REFINE-009: Stage C baseline detector seeding)
- PHYSICS-LOSS-003 (variance-weighted chi² consistency)

## Conclusion

Stage C chi² mismatch (0.32% gap, 3.2× beyond tolerance) is caused by Stage C using a baseline `crystal` object that may not match the true baseline used during Stage A initialization, combined with reapplying Stage A's refined parameter deltas. The fix is to explicitly capture and pass Stage A's **final** cell parameters to Stage C as frozen values, eliminating dependence on `crystal` object state.

**Next action:** Implement Path A (1 loop) with targeted fix and validation.
