# Input — TORCH-GEOMETRY-CONVERGENCE-001 Phase C3 Parameter Update Investigation

## Summary
Investigate why first optimizer step causes catastrophic failure (chi² 1.13M → 8.84M) INDEPENDENT of learning rate after H1 (LR tuning) decisively rejected.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — Regression guard
- Evidence-only (no new test nodes)

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/`

## Do Now

**CRITICAL PIVOT:** Phase C2 LR reduction (1e-5) produced IDENTICAL failure to Phase C1 (1e-4): chi²_after=8.84M (+679.6%), CC=0.765. **H1 (Adam LR too high) REJECTED** — 10× LR change → 0% improvement.

**Pattern recognition from Phase B history:** Similar symptom (initialization healthy, first step catastrophic, optimizer-agnostic) previously indicated CODE PATH DISCREPANCY (Phase B4: script _forward_once vs run_nanobrag_refinement used different B_ideal sources; Phase B5: crystal_overrides["A_star"] bypassed MOSFLM tuple injection).

**Hypothesis H5 (NEW):** Parameter update propagation bug — optimizer.step() modifies `log_scale` parameter correctly, but forward model in NEXT closure evaluation uses STALE or WRONG log_scale value (similar to B_ideal mismatch pattern).

### Step 1: Review Phase C1/C2 Evidence
- **Read:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_c3_decision.json`
- **Confirm:** LR change produced ZERO effect (chi²_after 8.836M vs 8.829M, <0.1% difference)
- **Note:** This rules out step-size issues and points to forward model/parameter propagation bug

### Step 2: Add Parameter Lifecycle Logging to Closure
- **Target:** `dbex/nanobrag_refinement.py` — Stage A LBFGS closure (U-matrix branch, lines ~966-1116)
- **Scope:** Add minimal logging BEFORE and AFTER optimizer.step() to track log_scale parameter value changes
- **Implementation:**
  1. Locate closure definition (line ~970: `def closure():`)
  2. Add logging INSIDE closure at entry:
     ```python
     # Top of closure, after "def closure():" and before forward model
     if telemetry_output_dir is not None:
         log_scale_before = log_scale_param.item()
         # Log to telemetry file
     ```
  3. Log log_scale value AFTER forward/backward but BEFORE return:
     ```python
     # After loss.backward(), before return loss
     if telemetry_output_dir is not None:
         log_scale_after_backward = log_scale_param.item()
         # Check if log_scale changed during backward (should NOT change)
     ```
  4. In outer loop (AFTER optimizer.step()), log the updated log_scale:
     ```python
     # After optimizer.step(closure) completes
     if telemetry_output_dir is not None:
         log_scale_post_step = log_scale_param.item()
         # This should differ from log_scale_before by ~-LR * gradient
     ```
- **Diagnostic question:** Does log_scale value ACTUALLY CHANGE after optimizer.step()? If not → parameter update not propagating. If yes → forward model using wrong value.

### Step 3: Execute 2-Step Diagnostic with Lifecycle Logging
- **Command:**
  ```bash
  timeout 1200 python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
    --use-u-matrix \
    --u-matrix-lr 1e-5 \
    --phases 5 \
    --dof-variants A_scale_only \
    --adam-steps 2 \
    --device cpu \
    --telemetry-dir telemetry \
    --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic/ \
    > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic.log 2>&1
  ```
- **Expected artifacts:**
  - `telemetry/telemetry_step_000_init.json` (log_scale BEFORE step)
  - `telemetry/telemetry_step_000_post.json` (log_scale AFTER step)
  - `telemetry/telemetry_step_001_init.json`
  - `block_dof_results_u_matrix.json` (sanity check: chi²_before ~1.13M, chi²_after ~8.84M)

### Step 4: Extract Lifecycle Metrics
```bash
python3 << 'PYEOF'
import json

# Read telemetry files
with open('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic/telemetry/telemetry_step_000_init.json') as f:
    step0_init = json.load(f)
with open('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic/telemetry/telemetry_step_000_post.json') as f:
    step0_post = json.load(f)

print("=== STEP 0 LIFECYCLE ===")
print(f"log_scale BEFORE optimizer.step(): {step0_init['log_scale']:.6f}")
print(f"grad_log_scale: {step0_init['grad_log_scale']:.2e}")
print(f"log_scale AFTER optimizer.step(): {step0_post['log_scale']:.6f}")
print(f"Δlog_scale: {step0_post['log_scale'] - step0_init['log_scale']:.6e}")
print(f"Expected Δ (≈ -LR × grad): {-1e-5 * step0_init['grad_log_scale']:.6e}")
print(f"chi² BEFORE: {step0_init.get('chi_squared', 'N/A')}")
print(f"chi² AFTER: {step0_post.get('chi_squared', 'N/A')}")
PYEOF
```

### Step 5: Synthesize Root Cause Determination
- **Create:** `phase_c3_parameter_lifecycle_decision.md`
- **Decision tree (4 paths):**

  **Path A: Parameter update WORKS, forward model uses NEW value (Δlog_scale matches expected)**
  - Verdict: H5 (parameter propagation bug) REJECTED
  - Evidence: log_scale changed by ≈ -LR × gradient, forward model evaluated at NEW log_scale
  - Interpretation: Optimizer and forward model are communicating correctly → root cause is ELSEWHERE (likely variance weighting, loss formula, or gradient correctness)
  - Next action: Finite-difference gradient validation (Phase C4) OR variance component analysis (Phase C5)

  **Path B: Parameter update FAILS (Δlog_scale ≈ 0 despite non-zero gradient)**
  - Verdict: H5 (parameter not updating) CONFIRMED
  - Evidence: log_scale UNCHANGED after optimizer.step() despite gradient ~150k
  - Root cause: Likely detach() placement error, requires_grad=False, or parameter not in optimizer.param_groups
  - Next action: Audit log_scale_param initialization, check requires_grad flag, verify optimizer.param_groups contains log_scale
  - Fix: Remove accidental detach, set requires_grad=True

  **Path C: Parameter update CORRECT, but forward model uses OLD value (chi² doesn't respond to Δlog_scale)**
  - Verdict: H5 (stale parameter in forward model) CONFIRMED
  - Evidence: log_scale changed correctly by optimizer, BUT chi² UNCHANGED or wrong magnitude change
  - Root cause: Forward model closure captures OLD log_scale value (variable scope issue, similar to Phase B5 crystal_overrides aliasing)
  - Next action: Audit closure variable scope, check if log_scale is captured by reference vs value
  - Fix: Ensure forward model reads log_scale_param.item() fresh each closure call

  **Path D: Parameter update TOO LARGE (Δlog_scale >> expected, suggests different LR or gradient)**
  - Verdict: LR not being applied correctly OR gradient wrong
  - Evidence: Δlog_scale far from -LR × gradient (e.g., 10× larger)
  - Root cause: LR config not propagating to optimizer OR gradient includes unexpected term
  - Next action: Print optimizer.param_groups[0]['lr'] to verify LR value used
  - Fix: Audit RefinementConfig.u_matrix_learning_rate propagation to optimizer

### Step 6: Update Implementation Plan
- **Edit:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`
- **Mark C2 as [~] BLOCKED** with "LR reduction ZERO effect, H1 rejected"
- **Add C3 entry:** `- [x] C3: Parameter Lifecycle Investigation — <verdict from Path A/B/C/D>`

### Step 7: Regression Guard
```bash
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -xvs \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/pytest_regression.log 2>&1
```

### Step 8: Write Summary and Commit
- **Summary:** Prepend to `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/summary.md`
- **Format:**
  ```markdown
  ### Turn Summary
  Investigated parameter update lifecycle after H1 (LR tuning) rejected (C2 FAIL: LR 1e-5 → identical chi²=8.84M).
  Lifecycle diagnostic showed <Path A/B/C/D verdict>: <parameter update works/fails/uses stale value/wrong magnitude>.
  Next: <Phase C4 gradient validation / fix parameter update bug / audit closure scope> based on evidence.
  Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/ (lifecycle_diagnostic.log, telemetry/, phase_c3_parameter_lifecycle_decision.md)
  ```
- **Commit:**
  ```bash
  git add -A
  git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase C3: Parameter lifecycle diagnostic to investigate LR-independent failure (tests: test_stage_a_expansion)"
  git push
  ```

## How-To Map

### Lifecycle Logging Implementation (Step 2)
```python
# In dbex/nanobrag_refinement.py, Stage A closure (U-matrix branch)
# Add at top of closure definition (after "def closure():", line ~970):

def closure():
    # Capture log_scale BEFORE forward model
    if telemetry_output_dir is not None:
        log_scale_entry = log_scale_param.item()

    # ... existing forward model code ...
    loss.backward()

    # Capture log_scale AFTER backward (should be UNCHANGED by backward)
    if telemetry_output_dir is not None:
        log_scale_post_backward = log_scale_param.item()
        assert abs(log_scale_post_backward - log_scale_entry) < 1e-9, \
            f"log_scale changed during backward: {log_scale_entry} → {log_scale_post_backward}"

    return loss

# In outer optimization loop (AFTER optimizer.step(closure), line ~1090):
optimizer.step(closure)

if telemetry_output_dir is not None:
    log_scale_post_step = log_scale_param.item()
    # Emit to telemetry_step_{i}_post.json:
    telemetry_data['log_scale_post_step'] = log_scale_post_step
    telemetry_data['delta_log_scale'] = log_scale_post_step - log_scale_entry
    telemetry_data['expected_delta'] = -optimizer.param_groups[0]['lr'] * log_scale_param.grad.item()
```

### Diagnostic Execution (Step 3)
```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic

timeout 1200 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --u-matrix-lr 1e-5 \
  --phases 5 \
  --dof-variants A_scale_only \
  --adam-steps 2 \
  --device cpu \
  --telemetry-dir telemetry \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic/ \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic.log 2>&1

echo "Exit code: $?" >> plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/lifecycle_diagnostic.log
```

### Metrics Extraction (Step 4)
Paste the Python script from Step 4 into terminal, or save as micro probe in summary.md.

## Pitfalls to Avoid

1. **Telemetry Scope:** Emit lifecycle metrics (log_scale_before/after) to BOTH _init and _post telemetry files for complete picture.
2. **Closure Variable Capture:** Beware Python closure variable capture by reference vs value — ensure log_scale_param is the SAME tensor object accessed by optimizer.
3. **Detach Placement:** Do NOT call .detach() on log_scale_param anywhere in lifecycle; would break gradient flow.
4. **LR Verification:** ALWAYS print `optimizer.param_groups[0]['lr']` in telemetry to confirm config value propagated.
5. **Chi² Evaluation Timing:** chi² in _init telemetry is BEFORE optimizer.step(), chi² in _post is AFTER step (should be catastrophic 8.84M).
6. **Backward Side Effects:** Backward pass should NOT modify parameter VALUES (only .grad attribute); assert to catch bugs.
7. **Adam State:** Adam optimizer maintains momentum buffers; first step uses zero momentum, second step uses momentum from first → Δlog_scale may differ between steps.
8. **FP Precision:** Use abs(Δ) < 1e-9 for "unchanged" checks (not ==), account for float32 rounding.
9. **Regression Guard:** Run BEFORE committing lifecycle logging changes (ensure no side effects on cell+misset path).
10. **Normalization:** This diagnostic focuses on log_scale only (A_scale_only variant); quaternion parameters have train_orientation=False so no q_params updates to track.

## If Blocked

**Blocker 1: Diagnostic test times out**
- Reduce to 1 step instead of 2
- Capture whatever telemetry completed
- Mark decision as PARTIAL

**Blocker 2: Telemetry files missing lifecycle fields**
- Fallback: Add print() statements instead of JSON emission
- Capture from log file via grep
- Proceed with decision based on printed values

**Blocker 3: Regression guard fails**
- Revert lifecycle logging changes
- Run diagnostic manually via REPL
- Document blocker in decision.md

## Findings Applied

**Relevant findings:**
- **Phase B5** (Code path discrepancy pattern): Script _forward_once vs run_nanobrag_refinement used different crystal_overrides handling → initialization healthy, optimization catastrophic. Current symptom matches → investigate parameter propagation similar to B_ideal mismatch.
- **GRADIENT-001** (autograd graph preservation): Parameter update requires requires_grad=True and no accidental detach() → lifecycle diagnostic will verify.
- **REFINE-001** (optimizer stability): Adam vs LBFGS behavior differences understood → lifecycle diagnostic applies to BOTH (currently testing Adam, but Path B4 showed LBFGS has same failure).

No relevant findings for parameter lifecycle logging methodology (novel diagnostic for CONVERGENCE-001).

## Pointers

- **Implementation Plan:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Phase C checklist
- **Phase C2 Failure:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T235959Z/phase_c2_c3_decision.json` — LR reduction null result
- **Phase B5 Pattern:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/code_path_audit.md` — Similar diagnostic approach (audit parameter propagation)
- **Closure Code:** `dbex/nanobrag_refinement.py:~966-1116` — Stage A LBFGS closure (U-matrix branch)
- **Spec:** `docs/spec-db-runtime.md` §Optimizer Convergence — Parameter update mechanics

## Next Up

If lifecycle diagnostic completes early AND verdict is Path A (parameter update works correctly):

**Option 1: Finite-Difference Gradient Validation**
- Implement FD validation script (compare autograd vs numerical gradients for log_scale)
- Check if autograd is computing correct ∂χ²/∂log_scale

**Option 2: Variance Component Analysis**
- Log variance denominator components (V_denom histogram, clamp_fraction, weighted_residuals)
- Check if variance weighting becomes unstable after parameter update

## Normative Math/Physics

**Adam Parameter Update Rule:** See `docs/spec-db-runtime.md` §Adam Optimizer

Expected parameter change after one step:
```
Δθ ≈ -LR × gradient  (first step, zero momentum)
```

For log_scale with gradient ~150k and LR=1e-5:
```
Δlog_scale ≈ -1e-5 × 150,000 = -1.5
```

**Lifecycle invariant:** Parameter value must ONLY change after optimizer.step(), NOT during forward() or backward().
