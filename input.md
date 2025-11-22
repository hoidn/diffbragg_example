# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase B Hypothesis Testing (LBFGS Alternative)

## Summary
Test LBFGS optimizer as alternative to catastrophically-failing Adam for quaternion U-matrix convergence.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (U-matrix path must not break cell+misset default)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/

## Do Now

**Checklist Items:** Phase B0-B1 (Test Protocol Design + LBFGS Hypothesis Test)

**Context:** Ralph's Phase A bugfix (2025-11-22T152500Z) successfully resolved initialization pathology:
- Pre-bugfix: Step 0 chi² = 1.425B (1000× worse than expected)
- Post-bugfix: Step 0 chi² = 1.13M (matches zero-point check ~990k-1.13M)
- Regression guard PASSED
- Zero-point parity perfect (corr ≈ 1.0, max_abs_diff ~85 photons)

**However, Adam optimization STILL fails catastrophically:**
- Steps 1-9: chi² explodes 1.13M → 1.425B (1257× worse)
- Final median CC: -0.045 (negative correlation)
- Verdict: Initialization bug FIXED, but convergence pathology is a SEPARATE issue

**Root Cause Hypothesis Update (from phase_a_bugfix_decision.md):**
- H1 (Adam hyperparameters): PLAUSIBLE — Adam LR=1e-4 may be incompatible with quaternion gradient manifold (S³ unit sphere)
- H2 (Variance-weighted loss instability): PLAUSIBLE — Variance denominator may destabilize during optimization
- H3 (Gradient pathology): PLAUSIBLE — Quaternion normalization or matrix ops may produce NaN/inf/exploding gradients
- H4 (Quaternion constraint): PLAUSIBLE — Unit-norm constraint vs momentum accumulation

**Phase B Strategy:** Test **H1 first** (optimizer alternative) as most direct fix. LBFGS has no momentum (eliminating H1+H4 concerns), uses line search (mitigating H2/H3), and is already proven for scale-only refinement per REFINE-001.

### Step 1: Phase B Test Protocol Design

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test_protocol.md`:

```markdown
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
```

**Your task:** Create this protocol document exactly as specified above.

### Step 2: Extend stage_a_mapping_adam_debug.py with LBFGS Flag

Edit `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`:

**Find argparse block (~line 50-80):**
```python
ap.add_argument("--use-u-matrix", action="store_true",
                help="Use quaternion U-matrix parameterization instead of cell+misset")
ap.add_argument("--adam-steps", type=int, default=10,
                help="Number of Adam optimization steps")
```

**Add after `--use-u-matrix`:**
```python
ap.add_argument("--use-lbfgs", action="store_true",
                help="Use LBFGS optimizer instead of Adam for U-matrix path (Test B1)")
ap.add_argument("--optimizer-steps", type=int, default=10,
                help="Number of optimizer steps (Adam or LBFGS)")
```

**Find RefinementConfig construction (~line 150-180):**
```python
config = RefinementConfig(
    use_u_matrix_parameterization=args.use_u_matrix,
    ...
)
```

**Add field:**
```python
config = RefinementConfig(
    use_u_matrix_parameterization=args.use_u_matrix,
    use_lbfgs_for_u_matrix=args.use_lbfgs,  # Test B1 flag
    ...
)
```

**Update step count references:**
Replace all `args.adam_steps` with `args.optimizer_steps` (backward compatible since default=10 matches).

### Step 3: Add LBFGS Support to RefinementConfig

Edit `dbex/nanobrag_refinement.py`:

**Find RefinementConfig dataclass (~line 80-120):**
```python
@dataclass
class RefinementConfig:
    use_u_matrix_parameterization: bool = False
    ...
```

**Add field after `use_u_matrix_parameterization`:**
```python
@dataclass
class RefinementConfig:
    use_u_matrix_parameterization: bool = False
    use_lbfgs_for_u_matrix: bool = False  # Test B1: LBFGS optimizer for U-matrix path
    ...
```

### Step 4: Implement LBFGS Optimizer Branch

Edit `dbex/nanobrag_refinement.py` in `run_nanobrag_refinement` function:

**Find optimizer selection block for U-matrix path (~line 810-835):**
```python
if config.use_u_matrix_parameterization:
    # Quaternion U-matrix path
    optimizer = torch.optim.Adam([q_params, log_scale], lr=1e-4)
else:
    # Cell+misset default path
    optimizer = torch.optim.Adam(params, lr=1e-4)
```

**Replace with:**
```python
if config.use_u_matrix_parameterization and config.use_lbfgs_for_u_matrix:
    # Test B1: LBFGS for quaternion U-matrix refinement
    # LBFGS eliminates momentum (H4), uses line search (H3/H2), proven for scale per REFINE-001
    optimizer = torch.optim.LBFGS(
        [q_params, log_scale],
        lr=1.0,  # LBFGS uses line search; LR=1.0 is standard
        max_iter=20,  # LBFGS iterations per optimizer.step() call
        tolerance_grad=1e-7,
        tolerance_change=1e-9,
        history_size=10,
        line_search_fn='strong_wolfe'
    )
    logger.info("Stage A: Using LBFGS optimizer for U-matrix path (CONVERGENCE-001 Test B1)")
elif config.use_u_matrix_parameterization:
    # Default Adam (known to fail catastrophically; kept for comparison)
    optimizer = torch.optim.Adam([q_params, log_scale], lr=1e-4)
    logger.info("Stage A: Using Adam optimizer for U-matrix path (default)")
else:
    # Cell+misset default path (unchanged)
    optimizer = torch.optim.Adam(params, lr=1e-4)
    logger.info("Stage A: Using Adam optimizer for cell+misset path (default)")
```

**Important:** LBFGS optimizer API requires closure to be called multiple times per step. Ensure the closure (build_stage_a_lbfgs_closure or equivalent) supports this pattern.

### Step 5: Verify LBFGS Closure Compatibility

Check `dbex/nanobrag_refinement.py` closure construction (~line 850-900):

**Required pattern for LBFGS:**
```python
def closure():
    optimizer.zero_grad()
    loss = compute_loss(...)
    loss.backward()
    return loss

# LBFGS requires closure as argument to step()
optimizer.step(closure)
```

**If current code uses Adam pattern (no closure argument):**
```python
optimizer.zero_grad()
loss = compute_loss(...)
loss.backward()
optimizer.step()  # Adam doesn't take closure
```

**Refactor to support both:**
```python
if config.use_lbfgs_for_u_matrix:
    # LBFGS requires closure
    def closure():
        optimizer.zero_grad()
        loss = compute_loss_stage_a(...)
        loss.backward()
        return loss
    optimizer.step(closure)
else:
    # Adam pattern
    optimizer.zero_grad()
    loss = compute_loss_stage_a(...)
    loss.backward()
    optimizer.step()
```

**Note:** If `build_stage_a_lbfgs_closure` already exists (from REFINE-001), reuse it. If it's Adam-only, adapt per above.

### Step 6: Run LBFGS Test

Execute the test command from Step 1:

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/stage_a_lbfgs_test.log
```

**Expected outcomes:**
- If LBFGS converges (CC ≥ 0.99, chi² stable): Test B1 SUCCESS → Skip B2/B3, proceed to Phase C fix implementation
- If LBFGS fails like Adam: Test B1 FAILURE → Extract telemetry, document failure mode, proceed to Test B2 (gradient validation + LR tuning)

### Step 7: Extract LBFGS Test Metrics

After Step 6 completes, extract metrics:

```bash
# Extract final DoF results
jq '.' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/block_dof_results_lbfgs.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test1_lbfgs_results.json

# Check convergence metrics
jq -r '.A_scale_only | {median_cc_after: .cc_summary.median_after, chi2_ratio: (.chi_squared.after / .chi_squared.before)}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test1_lbfgs_results.json
```

### Step 8: Synthesize Test B1 Decision

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test1_decision.md`:

```markdown
# Phase B Test 1 Decision: LBFGS Optimizer

## Test Configuration
- Optimizer: torch.optim.LBFGS(lr=1.0, max_iter=20, line_search_fn='strong_wolfe')
- Parameters: q_params (quaternion), log_scale
- Variant: A_scale_only (scale-only refinement, orientation fixed)
- Steps: 10 optimizer.step() calls (each may invoke closure multiple times due to line search)

## Results

**Convergence Metrics:**
- Chi² Before: [paste from phase_b_test1_lbfgs_results.json]
- Chi² After: [paste]
- Chi² Ratio: [paste]
- Median CC Before: [paste]
- Median CC After: [paste]

**Decision Tree:**

### Path A: LBFGS Convergence SUCCESS (CC ≥ 0.99, chi² ratio ≤ 1.005)
- **Verdict:** H1 CONFIRMED — Adam optimizer is incompatible with quaternion U-matrix gradients; LBFGS resolves convergence pathology
- **Root Cause:** Adam momentum accumulation violates quaternion unit-norm constraint (H4) or amplifies gradient errors (H3); LBFGS line search stabilizes optimization
- **Recommended Fix:** Add optimizer switch for U-matrix path (config.use_lbfgs_for_u_matrix default to True when use_u_matrix_parameterization=True)
- **Next Actions:**
  1. Mark Phase B complete (B0-B1 done, B2-B3 skipped)
  2. Proceed to Phase C fix implementation (C1: permanent LBFGS switch + documentation)
  3. Run Phase C validation (C2 A_scale_only, C3 D_full, C4 regression guard, C5 findings update CONVERGENCE-002)

### Path B: LBFGS Convergence FAILURE (CC < 0.95 OR chi² ratio > 1.5)
- **Verdict:** H1 REJECTED — Optimizer choice is NOT the root cause; convergence pathology persists with LBFGS
- **Hypothesis Update:**
  - If LBFGS chi² exploded like Adam (ratio > 100): H3 (gradient pathology) or H2 (variance instability) likely
  - If LBFGS stalled (chi² flat, CC unchanged): H4 (quaternion constraint) or optimization landscape issue
- **Recommended Next Test:** Test B2 (gradient validation + Adam LR=1e-6 to diagnose H3)
- **Next Actions:**
  1. Document LBFGS failure mode in this decision.md
  2. Extract gradient telemetry (check for NaN/inf, exploding magnitudes)
  3. Implement Test B2 per phase_b_test_protocol.md
  4. If B2 also fails, proceed to Test B3 (variance analysis + loss clamping)

### Path C: LBFGS Inconclusive (partial improvement, CC=0.95-0.99 OR chi² ratio=1.0-1.5)
- **Verdict:** LBFGS partially resolves issue but doesn't fully achieve exit criteria
- **Recommended Actions:**
  1. Try LBFGS with tighter tolerances (tolerance_grad=1e-9, tolerance_change=1e-11)
  2. Increase LBFGS max_iter from 20 to 50 (more line search iterations per step)
  3. Check telemetry for early termination signals (tolerance_grad met prematurely)
  4. If second LBFGS run with tighter tolerances succeeds → Select Path A
  5. If second run still inconclusive → Proceed to Test B2 (gradient validation)
```

**Your task:** Fill in the metrics placeholders with actual values from Step 7, select the appropriate decision path (A/B/C), and document the verdict with confidence level (high/medium/low).

### Step 9: Regression Guard

Run regression guard to ensure cell+misset default path unaffected:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/pytest_stage_a_regression.log
```

**Expected:** PASSED (LBFGS flag is off by default; cell+misset path unchanged)

### Step 10: Update Implementation Plan Checklist

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:

**Mark Phase B items:**
- [x] B0: **Test Protocol Design** — Prioritized H1 (LBFGS) → H1+H3 (LR+gradients) → H2 (variance). DONE (2025-11-22T165000Z).
- [x] B1: **Execute Test 1 (LBFGS)** — Implemented LBFGS optimizer branch, ran A_scale_only test, extracted convergence metrics. DONE (2025-11-22T165000Z).
- [ ] B2: **Execute Test 2** — PENDING (conditional on Test B1 decision path)
- [ ] B3: **Execute Test 3** — PENDING
- [ ] B4: **Test Result Synthesis** — PENDING

**Add Test B1 note to B1:**
```markdown
**Test B1 Results (2025-11-22T165000Z):** LBFGS optimizer with quaternion U-matrix parameterization [SUCCESS/FAILURE]. Chi² ratio=[value], median CC after=[value]. [If SUCCESS: H1 confirmed, proceed to Phase C fix. If FAILURE: H1 rejected, proceed to Test B2 gradient validation.]
```

## How-To Map

**Protocol Design (Step 1):**
```bash
# Write phase_b_test_protocol.md per template above
# No commands; documentation task
```

**Script Extension (Step 2):**
```bash
# Edit plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
# Add --use-lbfgs and --optimizer-steps flags to argparse
# Pass use_lbfgs_for_u_matrix=args.use_lbfgs to RefinementConfig
```

**Config Extension (Step 3):**
```bash
# Edit dbex/nanobrag_refinement.py RefinementConfig dataclass
# Add: use_lbfgs_for_u_matrix: bool = False
```

**LBFGS Implementation (Step 4-5):**
```bash
# Edit dbex/nanobrag_refinement.py run_nanobrag_refinement optimizer selection
# Add LBFGS branch with closure pattern per template above
# Ensure closure supports LBFGS API (returns loss, called multiple times per step)
```

**Test Execution (Step 6):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/stage_a_lbfgs_test.log
```

**Metrics Extraction (Step 7):**
```bash
jq '.' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/block_dof_results_lbfgs.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test1_lbfgs_results.json

jq -r '.A_scale_only | {median_cc_after: .cc_summary.median_after, chi2_ratio: (.chi_squared.after / .chi_squared.before)}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test1_lbfgs_results.json
```

**Regression Guard (Step 9):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/pytest_stage_a_regression.log
```

## Pitfalls To Avoid

1. **LBFGS closure API:** LBFGS requires `optimizer.step(closure)` with closure returning loss. Adam uses `optimizer.step()` with no arguments. Do NOT mix these patterns; use conditional branching per Step 5.

2. **LBFGS max_iter vs optimizer steps:** LBFGS `max_iter=20` is the **per-step** line search iteration limit. Total optimization steps = `args.optimizer_steps` (e.g., 10). Do NOT confuse these two numbers.

3. **Closure side effects:** LBFGS calls closure multiple times per step (line search). Ensure telemetry emission (if inside closure) doesn't create duplicate files. Consider emitting telemetry OUTSIDE closure, after each optimizer.step() call.

4. **LBFGS memory:** LBFGS history_size=10 stores last 10 gradient/parameter vectors. For quaternion (4 params) + scale (1 param) = 5 DOF, memory is negligible. Do NOT increase history_size unnecessarily.

5. **Config flag default:** `use_lbfgs_for_u_matrix` defaults to False so existing tests (cell+misset path, Adam U-matrix experiments) are unaffected. Only enable via explicit `--use-lbfgs` flag.

6. **Telemetry file naming:** Use `block_dof_results_lbfgs.json` (not `block_dof_results.json`) to avoid overwriting Adam test artifacts from Phase A.

7. **Timeout:** LBFGS line search may be slower than Adam fixed-step. Keep timeout=1200s; if insufficient, extend to 2400s in rerun.

8. **Regression guard:** Run AFTER implementing LBFGS branch to ensure default path unaffected. Do NOT skip this step.

9. **Gradient validation:** If Test B1 fails, DO NOT proceed to Phase C. Extract gradient telemetry and diagnose failure mode before declaring convergence unachievable.

10. **Protected Assets:** Do not modify `dbex/data_load.py`, `dbex/run_diffbragg.py`, or `dbex/refine_one.py`. Changes scoped to `dbex/nanobrag_refinement.py` (optimizer branch) and `stage_a_mapping_adam_debug.py` (CLI flag) only.

## If Blocked

**If LBFGS convergence fails (Step 8 Path B):**
- Extract telemetry from `telemetry/telemetry_step_*.json`
- Check for NaN/inf in gradients: `jq -r '.gradients' telemetry_step_000.json`
- Check for exploding gradient norms: `jq -r '.gradients.q_params_norm' telemetry_step_*.json | sort -n`
- Document failure signature in `phase_b_test1_decision.md` (e.g., "LBFGS chi² exploded to 1.4B like Adam" vs "LBFGS stalled at 1.13M without improvement")
- Do NOT proceed to Phase C; transition to Test B2 (gradient validation + Adam LR=1e-6)

**If LBFGS test times out (Step 6):**
- Check `stage_a_lbfgs_test.log` for progress indicators (e.g., "LBFGS iteration 5/10")
- If timeout during line search (stuck in closure loop) → LBFGS may be unsuitable (landscape too rough); document and proceed to Test B2
- If timeout during HKL grid build → Extend timeout to 2400s and rerun

**If regression guard fails (Step 9):**
- Check if failure is in cell+misset default path (config.use_u_matrix_parameterization=False)
- If default path broken → REVERT all LBFGS changes immediately (config flag should isolate U-matrix code but verify)
- If U-matrix path broken → Investigate but do NOT revert (U-matrix is experimental)

**If closure pattern incompatible (Step 5):**
- Check existing `build_stage_a_lbfgs_closure` function signature
- If it already supports LBFGS pattern → Reuse it (rename from "lbfgs" to generic "closure" if needed)
- If it's Adam-only → Refactor per Step 5 template to support both optimizers

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards): Directly applicable — LBFGS proven for scale-only refinement; reusing same optimizer for quaternion U-matrix test. Ensure NaN/inf guards active in closure.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Relevant — variance denominator instability (H2) may manifest with LBFGS if line search explores extreme parameter regions. Monitor telemetry for V_denom pathologies.
- **GRADIENT-001** (autograd graph preservation): Applicable — closure must not use `.item()` or `.numpy()` on differentiable tensors; ensure loss.backward() graph is preserved across LBFGS line search iterations.
- **GEOMETRY-003** (baseline misset derivation): Not applicable to U-matrix path (no misset in quaternion parameterization).
- **GEOMETRY-004** (U-matrix parameterization conventions): Directly applicable — Test B1 validates whether LBFGS resolves quaternion convergence pathology identified in PARITY-002/003.

## Pointers

- **Phase A Bugfix:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/phase_a_bugfix_decision.md (initialization fixed, convergence fails)
- **Phase A Telemetry:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/block_dof_results_u_matrix.json (Adam catastrophic failure baseline)
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (Phase B checklist B0-B4)
- **REFINE-001:** docs/findings.md line 28 (LBFGS for scale-only, proven pattern)
- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence requirements), docs/spec-db-runtime.md §Gradient Stability
- **Optimizer Code:** dbex/nanobrag_refinement.py:810-835 (current Adam selection block to refactor)
- **Script:** plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:50-180 (argparse + RefinementConfig construction to extend)

## Next Up (Optional)

If you finish Step 10 early AND Step 8 selected Path A (LBFGS convergence SUCCESS):
- Prepare for Phase C transition by reading Phase C checklist (C1-C6 in implementation.md)
- Note that Phase C Do Now will include:
  - C1: Make LBFGS switch permanent (default to True when use_u_matrix_parameterization=True, document rationale)
  - C2: Phase 5 A_scale_only full validation (10 steps, verify CC ≥ 0.99, chi² stable)
  - C3: Phase 5 D_full validation (multi-DoF, verify monotonic chi² improvement)
  - C4: Regression guard
  - C5: Findings update CONVERGENCE-002 (root cause: Adam momentum incompatible with quaternion manifold; fix: LBFGS eliminates momentum)
- Do NOT implement Phase C this loop; just prep context for next Galph handoff

If Step 8 selected Path B (LBFGS convergence FAILURE):
- Read Test B2 protocol in `phase_b_test_protocol.md`
- Prepare for gradient validation (finite-difference check, NaN/inf diagnosis)
- Note that Test B2 will require D_full or C_scale_plus_orientation variant (A_scale_only has no orientation gradients to validate)
- Do NOT implement Test B2 this loop; document LBFGS failure thoroughly first

## Doc Sync Plan

Not applicable (no tests added/renamed this loop; Test B1 is implementation + validation only).

If Test B1 succeeds and reaches Phase C5 findings update, that loop will include:
- Create CONVERGENCE-002 finding in docs/findings.md documenting:
  - Root cause: Adam momentum accumulation violates quaternion unit-norm constraint (H4) or amplifies gradient errors (H3)
  - Fix: LBFGS optimizer with line search for U-matrix path (eliminates momentum, stabilizes optimization)
  - Validation: A_scale_only CC ≥ 0.99, chi² stable/improving; D_full monotonic convergence
  - Usage: Set `RefinementConfig(use_u_matrix_parameterization=True, use_lbfgs_for_u_matrix=True)` for quaternion refinement
- Cross-reference GEOMETRY-004 (U-matrix parameterization) and REFINE-001 (LBFGS proven for scale-only)
