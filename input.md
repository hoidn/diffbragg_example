# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase A1 Instrumentation Implementation

## Summary
Implement per-step telemetry in quaternion U-matrix closure to capture parameter/gradient/loss/variance metrics for convergence failure diagnosis.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (U-matrix path must not break cell+misset default)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/

## Do Now

**Checklist Items:** Phase A1 (Instrument Quaternion Closure), Phase A2 (Execute Instrumented Run), Phase A3 (First Divergence Analysis)

**Your Task (Production Code + Instrumented Execution):**

### Step 1: Implement Telemetry in Quaternion U-Matrix Closure

**File to Edit:** `dbex/nanobrag_refinement.py`
**Function:** `build_stage_a_lbfgs_closure` (inner closure `closure_impl`, U-matrix path lines ~968-1116)

**Telemetry Requirements (per `phase_a1_instrumentation_plan.md`):**

1. **Add Closure Step Counter** (before line 950):
   - Create a mutable step counter outside `closure_impl` to track iteration number:
     ```python
     step_counter = [0]  # Mutable list for closure capture
     ```

2. **Capture Parameters** (after line 971, after `q_norm = q_params / torch.norm(q_params)`):
   ```python
   q_norm_value = torch.norm(q_params).item()
   telemetry_params = {
       'step_index': step_counter[0],
       'q_params': q_params.detach().cpu().tolist(),
       'q_norm_value': q_norm_value,
       'log_scale': log_scale.item(),
   }
   ```

3. **Capture Gradients** (after line ~1180, after `loss.backward()` or `chi_squared_loss.backward()`):
   ```python
   telemetry_gradients = {
       'grad_q_norm': torch.norm(q_params.grad).item() if q_params.grad is not None else None,
       'grad_q_max': torch.max(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
       'grad_q_min': torch.min(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
       'grad_log_scale': torch.abs(log_scale.grad).item() if log_scale.grad is not None else None,
       'grad_has_nan': torch.isnan(q_params.grad).any().item() if q_params.grad is not None else False,
       'grad_has_inf': torch.isinf(q_params.grad).any().item() if q_params.grad is not None else False,
   }
   ```

4. **Capture Loss Components** (after line ~1114, after `chi_squared_loss = chi_squared_accum`):
   ```python
   clamp_fraction = clamped_pixels_total / max(masked_pixels_total, 1)
   telemetry_loss = {
       'chi_squared': chi_squared_loss.item(),
       'masked_mse': masked_mse_loss.item() if masked_pixels_total > 0 else 0.0,
       'masked_pixels': masked_pixels_total,
       'clamped_pixels': clamped_pixels_total,
       'clamp_fraction': clamp_fraction,
   }
   ```

5. **Capture Variance Components** (inside ROI loop, after line ~1096 where `bragg_scaled` is computed):
   - Add accumulators outside the ROI loop:
     ```python
     i_model_min_global = float('inf')
     i_model_max_global = float('-inf')
     i_model_values_list = []  # Collect masked values for median/std
     ```
   - Inside ROI loop, after `bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)`:
     ```python
     i_model_values = bragg_scaled[mask_subset]
     i_model_min_global = min(i_model_min_global, torch.min(bragg_scaled).item())
     i_model_max_global = max(i_model_max_global, torch.max(bragg_scaled).item())
     i_model_values_list.append(i_model_values.detach().cpu())
     ```
   - After ROI loop completes:
     ```python
     if i_model_values_list:
         i_model_all = torch.cat(i_model_values_list)
         telemetry_variance = {
             'i_model_min': i_model_min_global,
             'i_model_median': torch.median(i_model_all).item(),
             'i_model_max': i_model_max_global,
             'i_model_std': torch.std(i_model_all).item() if i_model_all.numel() > 1 else 0.0,
         }
     else:
         telemetry_variance = {
             'i_model_min': None,
             'i_model_median': None,
             'i_model_max': None,
             'i_model_std': None,
         }
     ```

6. **Emit Telemetry JSON** (before `return` statement, after all metrics captured):
   ```python
   # Combine all telemetry
   telemetry_step = {
       **telemetry_params,
       **telemetry_gradients,
       **telemetry_loss,
       **telemetry_variance,
   }

   # Emit to JSON file if telemetry output directory is configured
   # (Pass via RefinementConfig.telemetry_output_dir or env var)
   telemetry_out_dir = config.telemetry_output_dir if hasattr(config, 'telemetry_output_dir') else None
   if telemetry_out_dir:
       import json
       from pathlib import Path
       telemetry_path = Path(telemetry_out_dir) / f"telemetry_step_{step_counter[0]:03d}.json"
       telemetry_path.parent.mkdir(parents=True, exist_ok=True)
       with open(telemetry_path, 'w') as f:
           json.dump(telemetry_step, f, indent=2)

   # Increment step counter
   step_counter[0] += 1
   ```

7. **Add Telemetry Config Field** (in `dbex/common.py` or wherever `RefinementConfig` is defined):
   - Add `telemetry_output_dir: Optional[str] = None` field to `RefinementConfig` dataclass/class

**Constraints:**
- **Observation only** — Do NOT mutate production logic (no changes to loss computation, optimizer behavior, parameter updates)
- **Conditional emission** — Telemetry only emits if `config.telemetry_output_dir` is set (default None = no overhead)
- **CPU tensors for JSON** — Detach and `.cpu()` before `.tolist()` to avoid CUDA memory/serialization issues

### Step 2: Extend `stage_a_mapping_adam_debug.py` with Telemetry Flag

**File to Edit:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`

Add CLI flag to enable telemetry output:

```python
# In argparse setup (~line 1400):
ap.add_argument(
    '--telemetry-dir',
    type=str,
    default=None,
    help='Directory for per-step telemetry JSON files (enables instrumentation)',
)

# When building RefinementConfig (~line 1450):
config = RefinementConfig(
    # ... existing fields ...
    telemetry_output_dir=args.telemetry_dir,  # Pass through to enable telemetry
)
```

### Step 3: Execute Instrumented Run (Phase A2)

**Command:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/
```

**Expected Outputs:**
- `telemetry/telemetry_step_000.json` through `telemetry_step_009.json` (10 steps)
- `block_dof_results.json` (Phase 5 convergence metrics for A_scale_only variant)
- Standard `stage_a_debug.log`

**Timeout:** 1200 seconds (20 minutes, to account for telemetry overhead + HKL grid builds)

### Step 4: First Divergence Analysis (Phase A3)

After instrumented run completes, analyze telemetry to identify first divergence point:

1. **Read All Telemetry Files** (`telemetry_step_*.json`)
2. **Identify First Divergence Step** where ANY of these conditions occurs:
   - χ² increases >10% from step 0 value
   - `grad_has_nan = true` OR `grad_has_inf = true`
   - `grad_q_norm > 1e10` (gradient explosion) OR `grad_q_norm < 1e-10` (gradient vanishing)
   - `clamp_fraction > 0.95` (sigma_floor dominates 95%+ of pixels, suggests numerical instability)

3. **Document First Divergence** in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/phase_a_first_divergence.md`:
   - First divergence step index
   - Parameter values at that step (`q_params`, `q_norm_value`, `log_scale`)
   - Gradient values (`grad_q_norm`, `grad_q_max`, `grad_q_min`, `grad_log_scale`, NaN/Inf flags)
   - Loss components (`chi_squared`, `masked_mse`, `clamp_fraction`)
   - Variance components (`i_model_min/median/max/std`)
   - Primary failure mode classification: `gradient_explosion`, `gradient_nan`, `loss_explosion`, `variance_pathology`

4. **Preliminary Hypothesis Verdict** (one-line note on which of H1-H4 is most supported by first divergence evidence)

### Step 5: Regression Guard

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

**Expected:** PASSED (cell+misset default path unaffected; U-matrix path optional and gated by `use_u_matrix_parameterization` flag)

**If Fails:** Document regression in blockers, do not proceed to Phase A4-A6

### Step 6: Update Implementation Plan Checklist

Mark Phase A1, A2, A3 as complete in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:

- `[x] A1: Instrument Quaternion Closure` — Add completion note with telemetry JSON count and artifact path
- `[x] A2: Execute Instrumented Run` — Add completion note with runtime, χ² final value, CC final value from `block_dof_results.json`
- `[x] A3: First Divergence Analysis` — Add completion note with first divergence step index and primary failure mode

### Step 7: Emit Summary

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/summary.md`:

```markdown
### Turn Summary
Implemented per-step telemetry in quaternion U-matrix closure (parameters, gradients, loss, variance); executed instrumented A_scale_only Adam run (10 steps); identified first divergence at step X with primary failure mode Y (gradient explosion/NaN/variance pathology).
Regression guard test_stage_a_expansion PASSED (cell+misset default path unaffected).
Next: Phase A4 finite-difference validation, A5 variance analysis, A6 hypothesis decision to select Phase B targeted fix.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/ (telemetry/*.json, phase_a_first_divergence.md, block_dof_results.json, pytest_stage_a_regression.log)
```

(Prepend this exact block to existing `summary.md` if it already exists from Phase A0)

## How-To Map

**Telemetry Implementation:**
```bash
# Read instrumentation plan for exact injection points
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a1_instrumentation_plan.md

# Locate U-matrix closure in dbex/nanobrag_refinement.py
grep -n "use_u_matrix_parameterization" dbex/nanobrag_refinement.py

# Implement telemetry per Step 1 above (parameters, gradients, loss, variance)
# Add telemetry_output_dir to RefinementConfig
# Extend stage_a_mapping_adam_debug.py with --telemetry-dir flag per Step 2
```

**Instrumented Run Execution:**
```bash
# Create telemetry output directory
mkdir -p plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/

# Run Phase 5 A_scale_only with telemetry enabled
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/

# Verify telemetry files created
ls -lh plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/
```

**First Divergence Analysis:**
```bash
# Read all telemetry files
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/telemetry_step_*.json | jq .

# Identify first divergence step (chi² >10% increase, NaN/Inf gradients, gradient explosion)
# Extract step 0 chi² baseline:
jq -r '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/telemetry_step_000.json

# For each step, check if chi² increased >10%:
for i in {0..9}; do
  jq -r ".step_index, .chi_squared, .grad_q_norm, .grad_has_nan, .grad_has_inf" \
    plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/telemetry_step_$(printf "%03d" $i).json
done

# Document first divergence in phase_a_first_divergence.md per Step 4
```

**Regression Guard:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/pytest_stage_a_regression.log
```

## Pitfalls To Avoid

1. **Do NOT mutate production logic** — Telemetry is observation only; do not change loss computation, parameter updates, or optimizer behavior. All instrumentation must be conditional on `config.telemetry_output_dir` being set (default None = no overhead).

2. **Tensor serialization** — Always `.detach().cpu().tolist()` before JSON serialization to avoid CUDA memory leaks and serialization errors.

3. **Gradient availability** — Check `q_params.grad is not None` before accessing gradient values (gradients may be None on first closure call before optimizer step).

4. **Step counter scope** — Use mutable list `step_counter = [0]` outside `closure_impl` so the counter persists across closure calls and increments correctly.

5. **Variance components overhead** — Collecting `i_model_values_list` across ROIs adds memory overhead; use `.detach().cpu()` to avoid retaining autograd graph and move to CPU immediately.

6. **Telemetry directory creation** — The `telemetry_path.parent.mkdir(parents=True, exist_ok=True)` ensures directory exists before writing JSON; do not assume it's pre-created.

7. **First divergence criteria** — Do NOT require all conditions (chi² AND gradients AND clamp fraction); identify the FIRST step where ANY condition triggers. Some failures may have clean gradients but exploding loss, or vice versa.

8. **Hypothesis premature closure** — Phase A3 first divergence analysis should note which hypothesis is MOST SUPPORTED, but defer definitive verdict to Phase A6 after A4 (finite-difference validation) and A5 (variance analysis) complete. Do not collapse hypotheses yet.

9. **Regression guard environment** — Use exact environment flags from `docs/TESTING_GUIDE.md` per AUTHORITATIVE_CMDS_DOC; do not omit `DBEX_SMOKE_SIGMA_SOURCE=cli_override` or `DBEX_SMOKE_DETECTOR_SIZE=small` (required for small-detector fixture used in test).

10. **Timeout handling** — 1200s timeout is generous but may still trigger if HKL grid builds are slow; if timeout occurs, capture partial telemetry and note in blockers. Do NOT remove timeout (infinite hangs are worse than partial data).

## If Blocked

**If telemetry implementation breaks closure compilation or runtime:**
1. Verify all tensor operations are correctly detached before `.item()` or `.tolist()`
2. Check that `step_counter` is mutable list (not integer) for closure capture
3. Confirm `config.telemetry_output_dir` field exists and is passed through correctly
4. Document blocker in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/blocker.md` with exact error message

**If instrumented run times out or crashes:**
1. Capture partial telemetry files (any `telemetry_step_*.json` that were written before crash)
2. Note step count at crash in blocker
3. If crash is due to NaN/Inf propagation, that IS the first divergence — document it
4. Do NOT retry without telemetry; partial data is valuable for Phase A3 analysis

**If regression guard fails:**
1. Check if failure is in cell+misset default path (blocker — telemetry broke production code) or U-matrix path (acceptable — U-matrix is experimental)
2. If default path fails: revert telemetry changes, investigate what mutation occurred
3. If U-matrix path fails but default passes: proceed to Phase A3 analysis (failure is expected per PARITY-003 escalation)
4. Document regression details in blocker with exact pytest output

**If first divergence is immediate (step 0):**
1. Root cause is likely initialization or forward-pass numerical issue, NOT optimizer
2. Pivot to investigating `quaternion_to_matrix` implementation or U₀ extraction from MOSFLM A*
3. Note this in `phase_a_first_divergence.md` and recommend Phase A4 finite-difference validation at step 0 to verify autograd correctness

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards): Monitor for `grad_log_scale` explosion similar to REFINE-001 signature; if detected, consider scale warm-start or bounds for quaternion path.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Capture `clamp_fraction` per-step to detect if sigma_floor interaction causes numerical instability; high clamp_fraction (>0.95) suggests variance denominator pathology.
- **GRADIENT-001** (autograd graph preservation, crystal_overrides): Ensure telemetry `.detach()` operations do not break gradient flow in production path; verify `grad_has_nan/inf` flags remain False until divergence point.
- No other findings in the knowledge base directly address quaternion parameterization convergence pathology.

## Pointers

- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence expectations), docs/spec-db-runtime.md §Gradient stability (NaN/Inf guards), docs/spec-db-core.md §Variance Model (sigma_floor guard)
- **Architecture:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (full Phase A-C plan, diagnostic protocol at lines 76-113)
- **Instrumentation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a1_instrumentation_plan.md (exact injection points, telemetry spec)
- **Evidence Synthesis:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/phase_a0_evidence_synthesis.md (failure signature, hypothesis space H1-H4)
- **Fix Plan:** docs/fix_plan.md line 40 (TORCH-GEOMETRY-CONVERGENCE-001 entry, Tier 1 top priority)
- **Testing:** docs/TESTING_GUIDE.md §2 (Stage A expansion selector), docs/development/TEST_SUITE_INDEX.md (regression guard expectations)

## Next Up (Optional)

If you finish Phase A1-A3 early (instrumentation + execution + first divergence analysis):
- **Do NOT proceed to Phase A4-A6** — Those are separate analysis steps requiring review of A3 results
- Instead, perform preliminary hypothesis screening: review first divergence metrics and note in `phase_a_first_divergence.md` which of H1-H4 is most consistent with observed failure mode (e.g., if `grad_has_nan=true` → H3 gradient pathology; if `grad_q_norm > 1e10` → H1 Adam hyperparameters or H3 explosion; if `clamp_fraction > 0.95` → H2 variance-weighted loss)
- This preliminary screening will inform Phase A4-A6 next loop (finite-difference validation, variance analysis, hypothesis decision)

## Doc Sync Plan

Not applicable (no tests added/renamed this loop; instrumentation is internal telemetry, not test infrastructure).
