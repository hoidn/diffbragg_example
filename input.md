# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase B Deep Diagnostic

## Summary
Instrument LBFGS closure to identify B_ideal mismatch root cause and implement fix.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (validate after implementing fix)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/

## Do Now

**Checklist Items:** Phase B Deep Diagnostic (mandatory Priority 1 escalation from Test B1 Path B verdict)

**Context:** Phase B1 LBFGS test rerun (2025-11-22T172000Z) confirmed **Path B (BLOCKED)** with decisive evidence:
- Zero-point validation PASSED (chi²=989k, B_ideal bugfix works when use_mapping_zero_geometry=True)
- LBFGS step 000 CATASTROPHIC (chi²=1.425B, matches pre-bugfix signature when use_mapping_zero_geometry=False)
- Code path divergence: zero-point bypasses U @ B_ideal reconstruction (direct MOSFLM A* usage) → healthy; LBFGS optimization forces U @ B_ideal reconstruction → catastrophic
- Reproducible across two runs (2025-11-22T165000Z and 2025-11-22T172000Z), ruling out telemetry/data corruption

**Root Cause Hypothesis (High Confidence):**
The `derive_u_matrix_from_mosflm_a_star` bugfix (826f4c9) correctly returns `(U_matrix, B_ideal_reciprocal)`, but somewhere in the LBFGS optimization loop, `components.B_ideal_reciprocal` is:
- Being overwritten/mutated with wrong value (cctbx fractionalization_matrix), OR
- Not being used (different code path computes B_ideal separately), OR
- Experiencing tensor aliasing/device mismatch causing reversion to wrong value

**Objective:** Identify the EXACT point in the LBFGS closure lifecycle where B_ideal diverges from the correct MOSFLM-derived value, implement fix, and revalidate Test B1.

### Step 1: Code Audit — Search for Alternate B_ideal Computations

Before adding instrumentation, audit all B_ideal computation paths to find potential sources of the wrong value:

```bash
# Search for ALL uses of fractionalization_matrix in the workspace
grep -rn "fractionalization_matrix" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py dbex/nanobrag_refinement.py dbex/nanobrag_bridge.py

# Search for ALL uses of compute_cell_tensors (TorchCrystal B_ideal source)
grep -rn "compute_cell_tensors" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py dbex/nanobrag_refinement.py dbex/nanobrag_bridge.py

# Search for B_ideal assignments (where it might get overwritten)
grep -rn "B_ideal_reciprocal\s*=" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py dbex/nanobrag_refinement.py
```

Document findings in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/code_audit_b_ideal_sources.md`:
- List ALL code locations that compute or assign B_ideal
- Note which path is used in zero-point check (MOSFLM A* direct, bypassing U @ B_ideal)
- Note which path is used in LBFGS closure (U @ B_ideal reconstruction)
- Identify ANY cctbx fractionalization_matrix calls still present after bugfix 826f4c9

### Step 2: Instrument LBFGS Closure with B_ideal Lifecycle Logging

Edit `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` to add comprehensive B_ideal checksum and device/dtype logging.

**Location:** Find the `_stage_a_adam_core` function where the LBFGS closure is defined (around line 800-1000, look for `def closure():`).

**Instrumentation to add:**

```python
# At the TOP of the closure (before optimizer.zero_grad()), add:
def closure():
    # CONVERGENCE-001 Deep Diagnostic: B_ideal lifecycle check
    import hashlib

    # Checkpoint 1: B_ideal hash at closure entry
    B_ideal_np = components.B_ideal_reciprocal.cpu().numpy()
    B_ideal_hash = hashlib.sha256(B_ideal_np.tobytes()).hexdigest()[:16]
    B_ideal_first = components.B_ideal_reciprocal[0, 0].item()
    B_ideal_last = components.B_ideal_reciprocal[2, 2].item()
    B_ideal_device = components.B_ideal_reciprocal.device
    B_ideal_dtype = components.B_ideal_reciprocal.dtype

    logger.info(f"[DIAGNOSTIC-CLOSURE-ENTRY] step={step_index} B_ideal_hash={B_ideal_hash} first={B_ideal_first:.6e} last={B_ideal_last:.6e} device={B_ideal_device} dtype={B_ideal_dtype}")

    optimizer.zero_grad()

    # Checkpoint 2: Reconstruct A* and compute chi² (this is where divergence may occur)
    # (Existing forward pass code here...)

    # After A* reconstruction (find the line where U_matrix @ components.B_ideal_reciprocal is computed):
    # ADD BEFORE matmul:
    logger.info(f"[DIAGNOSTIC-PRE-MATMUL] step={step_index} U_device={U_matrix.device} U_dtype={U_matrix.dtype} B_device={components.B_ideal_reciprocal.device} B_dtype={components.B_ideal_reciprocal.dtype}")

    # Reconstruct A* and hash it
    A_star_reconstructed = U_matrix @ components.B_ideal_reciprocal
    A_star_hash = hashlib.sha256(A_star_reconstructed.detach().cpu().numpy().tobytes()).hexdigest()[:16]
    logger.info(f"[DIAGNOSTIC-POST-MATMUL] step={step_index} A_star_hash={A_star_hash}")

    # (Existing loss computation code here...)

    loss.backward()

    # Checkpoint 3: Log chi² and gradients
    logger.info(f"[DIAGNOSTIC-CLOSURE-EXIT] step={step_index} chi2={loss.item():.3e} grad_log_scale={log_scale.grad.item() if log_scale.grad is not None else None:.3e}")

    return loss
```

**Alternative (Simpler):** If logger.info is not available or too verbose, save diagnostic data to a JSON file per step:

```python
def closure():
    import hashlib
    import json
    from pathlib import Path

    # Compute diagnostics
    B_ideal_np = components.B_ideal_reciprocal.cpu().numpy()
    B_ideal_hash = hashlib.sha256(B_ideal_np.tobytes()).hexdigest()[:16]

    diagnostic_data = {
        "step_index": step_index,
        "closure_call_count": getattr(closure, 'call_count', 0),  # Track how many times closure called
        "b_ideal_hash": B_ideal_hash,
        "b_ideal_first": components.B_ideal_reciprocal[0, 0].item(),
        "b_ideal_last": components.B_ideal_reciprocal[2, 2].item(),
        "b_ideal_device": str(components.B_ideal_reciprocal.device),
        "b_ideal_dtype": str(components.B_ideal_reciprocal.dtype),
    }

    optimizer.zero_grad()

    # (Forward pass...)
    # After A* reconstruction:
    A_star_reconstructed = U_matrix @ components.B_ideal_reciprocal
    diagnostic_data["a_star_hash"] = hashlib.sha256(A_star_reconstructed.detach().cpu().numpy().tobytes()).hexdigest()[:16]

    # (Loss computation...)
    loss.backward()

    diagnostic_data["chi_squared"] = loss.item()
    diagnostic_data["grad_log_scale"] = log_scale.grad.item() if log_scale.grad is not None else None

    # Increment closure call counter
    closure.call_count = getattr(closure, 'call_count', 0) + 1

    # Save diagnostic JSON
    diag_dir = Path(args.out_dir) / "closure_diagnostics"
    diag_dir.mkdir(exist_ok=True)
    diag_file = diag_dir / f"closure_step_{step_index:03d}_call_{closure.call_count:03d}.json"
    with open(diag_file, 'w') as f:
        json.dump(diagnostic_data, f, indent=2)

    return loss
```

**Your task:** Choose the instrumentation approach (logger.info vs JSON files) that fits best with the script structure. Implement it in the LBFGS closure.

### Step 3: Compute Reference B_ideal Hash for Comparison

To validate whether the closure is using the correct B_ideal, we need a reference hash from the MOSFLM-derived value.

**Add BEFORE the optimizer loop starts** (where components are first created):

```python
# CONVERGENCE-001 Deep Diagnostic: Compute reference B_ideal hash
import hashlib
B_ideal_reference_np = components.B_ideal_reciprocal.cpu().numpy()
B_ideal_reference_hash = hashlib.sha256(B_ideal_reference_np.tobytes()).hexdigest()[:16]
logger.info(f"[DIAGNOSTIC-REFERENCE] B_ideal_hash={B_ideal_reference_hash} first={components.B_ideal_reciprocal[0,0].item():.6e} last={components.B_ideal_reciprocal[2,2].item():.6e}")

# Also save to file for comparison
import json
ref_data = {
    "b_ideal_reference_hash": B_ideal_reference_hash,
    "b_ideal_first": components.B_ideal_reciprocal[0, 0].item(),
    "b_ideal_last": components.B_ideal_reciprocal[2, 2].item(),
    "b_ideal_device": str(components.B_ideal_reciprocal.device),
    "b_ideal_dtype": str(components.B_ideal_reciprocal.dtype),
}
with open(Path(args.out_dir) / "b_ideal_reference.json", 'w') as f:
    json.dump(ref_data, f, indent=2)
```

### Step 4: Run 2-Step LBFGS Diagnostic Variant

Execute the instrumented test with REDUCED steps (2 instead of 10) to save time:

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 2 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/stage_a_diagnostic.log
```

**Expected duration:** ~20 minutes (2 steps × ~10 minutes per step, including closure evaluations during line search)

**Expected artifacts:**
- `b_ideal_reference.json` — Reference hash from MOSFLM-derived B_ideal
- `closure_diagnostics/closure_step_000_call_*.json` — One file per closure evaluation during LBFGS line search for step 0
- `closure_diagnostics/closure_step_001_call_*.json` — Same for step 1
- `zero_point_check.json` — Zero-point validation (should PASS as before)
- `telemetry/telemetry_step_000.json`, `telemetry/telemetry_step_001.json` — Per-step optimizer telemetry
- `stage_a_diagnostic.log` — Full console output with [DIAGNOSTIC-*] log lines

### Step 5: Analyze B_ideal Lifecycle and Identify Divergence Point

After Step 4 completes, analyze the diagnostic artifacts to find WHERE and WHEN B_ideal diverges:

```bash
# 1. Extract reference hash
REF_HASH=$(jq -r '.b_ideal_reference_hash' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/b_ideal_reference.json)
echo "Reference B_ideal hash: $REF_HASH"

# 2. Extract hashes from ALL closure calls (LBFGS line search may call closure 10-20 times per step)
echo "Closure B_ideal hashes (step 0):"
jq -r '.b_ideal_hash' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/closure_diagnostics/closure_step_000_call_*.json | sort | uniq -c

# 3. Compare: Does any closure call show a DIFFERENT hash than reference?
for file in plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/closure_diagnostics/closure_step_000_call_*.json; do
  HASH=$(jq -r '.b_ideal_hash' "$file")
  CHI2=$(jq -r '.chi_squared' "$file")
  CALL=$(basename "$file" | grep -oP 'call_\K\d+')
  if [ "$HASH" != "$REF_HASH" ]; then
    echo "DIVERGENCE at call $CALL: hash=$HASH chi2=$CHI2"
  else
    echo "OK at call $CALL: hash=$HASH chi2=$CHI2"
  fi
done

# 4. Extract chi² from closure diagnostics vs telemetry (should match at accepted step)
echo "Telemetry step 0 chi²:"
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/telemetry/telemetry_step_000.json

# 5. Check device/dtype consistency
jq '{b_ideal_device, b_ideal_dtype}' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/closure_diagnostics/closure_step_000_call_001.json
```

Document findings in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/b_ideal_divergence_analysis.md`:
- Does B_ideal hash MATCH reference in ALL closure calls, or does it CHANGE?
- If it changes: at which closure call (first call, second call, etc.)?
- If it changes: what are the new first/last element values (compare to cctbx fractionalization_matrix values)?
- Are device/dtype consistent across all closure calls?
- Does chi² correlate with B_ideal hash (wrong hash → catastrophic chi²)?

### Step 6: Synthesize Root Cause and Implement Fix

Based on Step 5 analysis, synthesize the root cause and implement the fix:

**Scenario A: B_ideal hash CHANGES during closure calls**
- **Root Cause:** `components.B_ideal_reciprocal` tensor is being mutated or overwritten
- **Fix:** Ensure `components.B_ideal_reciprocal` is immutable (clone + detach) when assigned:
  ```python
  # In stage_a_mapping_adam_debug.py, where components are created (around line 320):
  components = StageAContext(
      ...
      B_ideal_reciprocal=torch.as_tensor(B_ideal_reciprocal_np, dtype=torch.float32, device=device).clone(),  # ADD .clone()
      ...
  )
  ```

**Scenario B: B_ideal hash MATCHES reference BUT chi²=1.425B anyway**
- **Root Cause:** U_matrix or A_star_reconstructed computation is wrong, OR device/dtype mismatch during matmul
- **Fix:** Check U_matrix source (is it being computed correctly from quaternion?), ensure U and B_ideal are on same device/dtype before `U @ B_ideal`
  ```python
  # Before A* reconstruction in closure:
  U_matrix = quaternion_to_matrix(q_params / torch.norm(q_params))  # Normalize first
  U_matrix = U_matrix.to(device=components.B_ideal_reciprocal.device, dtype=components.B_ideal_reciprocal.dtype)  # Match device/dtype
  A_star_reconstructed = U_matrix @ components.B_ideal_reciprocal
  ```

**Scenario C: B_ideal hash DIFFERS from reference at FIRST closure call**
- **Root Cause:** `components.B_ideal_reciprocal` is assigned the WRONG value before LBFGS loop starts (different from zero-point check)
- **Fix:** Trace back to where components are created; ensure `derive_u_matrix_from_mosflm_a_star` return value is used correctly; check for any `fractionalization_matrix` calls that overwrite B_ideal after the bugfix

**Your task:** Based on diagnostic output, write a comprehensive root cause document (`b_ideal_divergence_analysis.md`) and implement the appropriate fix from Scenario A/B/C.

### Step 7: Rerun Test B1 After Fix

After implementing the fix from Step 6, rerun the full LBFGS Test B1 to validate:

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 2400 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/stage_a_lbfgs_fixed.log
```

**Increased timeout to 2400s (40 minutes)** to allow for 10 LBFGS steps on CPU.

**Success Criteria:**
- Zero-point check: chi²=989k (unchanged)
- **LBFGS step 0: chi²~1M (NOT 1.425B)** — THIS IS THE KEY FIX VALIDATION
- LBFGS convergence: chi² stable or improving, median CC ≥ 0.99 (if test completes)

If step 0 chi² is still catastrophic (1.425B), fix was incomplete → revisit Step 5-6 with deeper instrumentation.

If step 0 chi² is healthy (~1M), extract convergence metrics:

```bash
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/telemetry/telemetry_step_000.json
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/telemetry/telemetry_step_009.json

jq '.A_scale_only | {median_cc_after, chi2_before, chi2_after, chi2_ratio}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/block_dof_results.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/convergence_metrics_fixed.json
```

### Step 8: Synthesize Phase B Deep Diagnostic Decision

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/phase_b_deep_diagnostic_decision.md`:

```markdown
# Phase B Deep Diagnostic Decision

## Root Cause
[Scenario A/B/C from Step 6, with evidence from closure diagnostics]

## Fix Implemented
[Describe the code change: which file, which line, what was changed, why]

## Fix Validation (Test B1 Rerun After Fix)
- Zero-point check: chi²=[value] (expected ~989k)
- LBFGS step 0: chi²=[value] (expected ~1M, NOT 1.425B)
- LBFGS convergence: chi² before=[value], chi² after=[value], ratio=[value]
- Median CC after: [value] (expected ≥ 0.99)

## Decision Path
[Path A: Fix SUCCESS - chi² step 0 ~1M, convergence metrics meet thresholds → Proceed to Phase C]
[Path B: Fix INCOMPLETE - chi² step 0 still 1.425B → Escalate to deeper diagnostic or alternative parameterization]
[Path C: Fix PARTIAL - chi² step 0 improved but convergence fails → Rerun with tighter tolerances or try Test B2]

## Confidence Level
[High / Medium / Low]

## Rationale
[2-3 sentences explaining the decision]

## Next Actions
[If Path A: Proceed to Phase C (make LBFGS default, validate D_full, findings update)]
[If Path B: Escalate to PARITY-003 hybrid parameterization or mark quaternion approach non-viable]
[If Path C: Try Test B2 (Adam LR tuning) or Test B3 (variance analysis)]
```

### Step 9: Regression Guard

Run the regression guard to ensure production code changes didn't break cell+misset default path:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/pytest_stage_a_regression.log 2>&1
```

**Expected:** PASSED (cell+misset default path unaffected by U-matrix diagnostic instrumentation)

If test FAILS, remove instrumentation code (Step 2-3 additions) or guard it with `if config.use_u_matrix_parameterization:` to avoid affecting default path.

### Step 10: Update Implementation Plan and Fix Plan

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:

**Mark Phase B checklist B1:**
- [x] B1: **Execute Test 1 (LBFGS)** — Deep diagnostic completed (2025-11-22T180000Z). Root cause: [Scenario A/B/C]. Fix: [describe]. Revalidation: chi² step 0=[value], convergence=[Path A/B/C]. [If Path A: SUCCESS, proceed to Phase C. If Path B/C: describe next steps].

Edit `docs/fix_plan.md` to append Attempts History entry for 2025-11-22T180000Z deep diagnostic.

### Step 11: Commit and Summary

Commit all changes (instrumentation code, diagnostic artifacts, decision docs):

```bash
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B deep diagnostic: [ROOT CAUSE] - [FIX SUMMARY] (tests: [PASSED/BLOCKED])"
git push
```

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/summary.md` with Turn Summary format (3-5 sentences).

## How-To Map

**Code Audit (Step 1):**
```bash
grep -rn "fractionalization_matrix" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py dbex/nanobrag_refinement.py dbex/nanobrag_bridge.py \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/grep_fractionalization_matrix.txt
grep -rn "compute_cell_tensors" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py dbex/nanobrag_refinement.py dbex/nanobrag_bridge.py \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/grep_compute_cell_tensors.txt
grep -rn "B_ideal_reciprocal\s*=" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py dbex/nanobrag_refinement.py \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/grep_b_ideal_assignments.txt
# Review these files and document in code_audit_b_ideal_sources.md
```

**Instrument Closure (Step 2-3):**
```bash
# Use Edit tool to add diagnostic logging to stage_a_mapping_adam_debug.py
# Find the LBFGS closure definition (search for "def closure():" inside _stage_a_adam_core)
# Add hashlib/json instrumentation per templates above
```

**Run Diagnostic (Step 4):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 2 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/stage_a_diagnostic.log
```

**Analyze Divergence (Step 5):**
```bash
# Extract and compare hashes per bash commands in Step 5
# Document findings in b_ideal_divergence_analysis.md
```

**Implement Fix (Step 6):**
```bash
# Use Edit tool to modify stage_a_mapping_adam_debug.py based on Scenario A/B/C diagnosis
```

**Revalidate (Step 7):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 2400 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/stage_a_lbfgs_fixed.log

# Extract metrics
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/telemetry/telemetry_step_000.json
jq '.A_scale_only | {median_cc_after, chi2_before, chi2_after, chi2_ratio}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/block_dof_results.json
```

**Regression Guard (Step 9):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/pytest_stage_a_regression.log 2>&1
```

## Pitfalls To Avoid

1. **Instrumentation overhead:** Closure diagnostics will slow LBFGS line search further. That's why we reduced from 10 steps to 2 steps for the diagnostic run. Do NOT increase back to 10 steps until fix is validated.

2. **Hash comparison precision:** Use SHA256 hash of tensor bytes, NOT just first/last element comparison. Two different tensors can have same corner elements but different internal values.

3. **LBFGS closure call count:** LBFGS line search calls closure MANY times per optimizer.step() (10-20 calls during backtracking). The diagnostic should capture ALL calls, not just the first. Use closure call counter (`closure.call_count`) to track.

4. **Device/dtype mismatches:** Ensure ALL diagnostic code uses `.cpu().numpy()` before hashing to avoid CUDA tensor → CPU conversion errors. Also ensure U_matrix and B_ideal_reciprocal are on SAME device/dtype before matmul.

5. **Zero-point check bypass:** Remember that zero-point check uses `use_mapping_zero_geometry=True`, which bypasses U @ B_ideal reconstruction entirely. The diagnostic must instrument the LBFGS OPTIMIZATION loop, not the zero-point check.

6. **Fix scope:** If fix requires changes to `dbex/nanobrag_refinement.py` (production code), regression guard MUST pass. If fix is in `stage_a_mapping_adam_debug.py` (tooling), regression guard is optional but recommended.

7. **Timeout handling:** If Step 7 revalidation times out again (even with 2400s), LBFGS on CPU is fundamentally too slow for this problem. In that case, mark Path C (partial) and recommend either: (a) switch to GPU for LBFGS, (b) try Test B2 (Adam LR tuning), (c) mark quaternion approach as non-viable.

8. **Fix validation rigor:** Do NOT proceed to Phase C unless chi² step 0 drops from 1.425B → ~1M (1000× improvement). A small improvement (e.g., 1.425B → 1.2B) is NOT success; it means the fix is incomplete.

9. **Closure instrumentation cleanup:** After diagnostics complete, REMOVE or GUARD diagnostic logging code before finalizing fix. Production code should not have hashlib/logging overhead in every closure call. Use `if os.getenv("CONVERGENCE_001_DEBUG"): ...` to conditionally enable.

10. **Commit message clarity:** Commit message should summarize ROOT CAUSE (e.g., "B_ideal tensor mutation", "device mismatch", "stale cctbx fallback") and FIX (e.g., ".clone()", "device alignment", "remove fractionalization_matrix call"), NOT just "Phase B diagnostic complete".

## If Blocked

**If Step 4 diagnostic run times out before completing 2 steps:**
- Check log: Is progress being made (HKL grid builds, closure calls)?
- If yes: Extend timeout to 1800s (30 minutes) and rerun
- If no (stuck/stalled): Add print statements to closure to identify where it's hanging; check for deadlock or infinite loop

**If Step 5 analysis shows B_ideal hash is CONSISTENT but chi² still 1.425B:**
- Root cause is NOT B_ideal value, but HOW it's used (U_matrix computation, matmul order, device mismatch)
- Add A* reconstruction logging: compare `A_star_reconstructed` hash to `A_star_mosflm` reference (from zero-point check)
- Add U_matrix logging: hash U_matrix at closure entry, check if it matches expected value from quaternion

**If Step 7 revalidation shows chi² step 0 IMPROVED but still >2M (not ~1M):**
- Fix is PARTIAL; B_ideal is closer to correct but still has residual error
- Re-review Step 6 fix: Did you clone() the tensor? Did you align device/dtype? Did you remove ALL fractionalization_matrix calls?
- Run Step 5 analysis AGAIN on revalidation artifacts to see if hash now matches or is different

**If regression guard FAILS after implementing fix:**
- Fix broke cell+misset default path
- Guard the fix with `if config.use_u_matrix_parameterization:` conditional
- Ensure bugfix 826f4c9 changes to `derive_u_matrix_from_mosflm_a_star` did not affect cell+misset callers

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start): Applicable — LBFGS proven for scale-only; extending to quaternion U-matrix test. NaN/Inf guards critical.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Relevant if chi² explodes during diagnostic due to variance denominator issues.
- **GRADIENT-001** (autograd graph preservation): Critical for closure — must NOT use `.item()` or `.numpy()` on differentiable tensors before `.backward()`.
- **CONVERGENCE-001 Phase A Bugfix (826f4c9)**: `derive_u_matrix_from_mosflm_a_star` returns `(U_matrix, B_ideal_reciprocal)`. Zero-point validation confirms it works. Deep diagnostic must identify why optimization loop doesn't use it correctly.

## Pointers

- **Prior Diagnostics:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/{phase_b1_review.md, phase_b1_decision.md} (Path B verdict, escalation rationale)
- **Bugfix Commit:** 826f4c9 (derive_u_matrix_from_mosflm_a_star signature change)
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (Phase B checklist, Phase C next steps)
- **Script:** plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py (LBFGS closure to instrument)
- **Production Code:** dbex/nanobrag_refinement.py (LBFGS infrastructure, may need fix if B_ideal passed incorrectly)
- **Bridge Code:** dbex/nanobrag_bridge.py (derive_u_matrix_from_mosflm_a_star bugfix location)
- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence requirements)
- **Spec:** docs/spec-db-runtime.md §Gradient stability (NaN/Inf checks, autograd hygiene)

## Next Up (Optional)

If Step 7 revalidation succeeds (Path A: chi² step 0 ~1M, convergence metrics meet thresholds):
- Read Phase C checklist (C1-C6 in implementation.md)
- Note Phase C deliverables:
  - C1: Make LBFGS switch permanent (default to True when use_u_matrix=True, document rationale)
  - C2: Phase 5 A_scale_only validation (full 10 steps, verify CC ≥ 0.99, chi² stable)
  - C3: Phase 5 D_full validation (multi-DoF, verify monotonic chi² improvement)
  - C4: Regression guard (already passed, just verify)
  - C5: Findings update CONVERGENCE-002 (root cause, fix, usage conventions)
  - C6: Fix-plan close (mark CONVERGENCE-001 done, unblock PARITY-003)
- Do NOT implement Phase C this loop; just prep context for next handoff

If Step 7 revalidation fails (Path B/C: chi² step 0 still catastrophic or convergence fails):
- Document EXACTLY why fix was incomplete (which Scenario A/B/C was misdiagnosed)
- Recommend deeper diagnostic (e.g., instrument U_matrix computation, add more checkpoints)
- OR recommend escalation to alternative parameterization (PARITY-003 hybrid cell+quaternion+scale)

## Doc Sync Plan

Not applicable (no tests added/renamed this loop). Deep diagnostic is validation/instrumentation only.

If Phase C is reached (after successful fix), C5 findings update will include:
- Create/extend CONVERGENCE-002 in docs/findings.md
- Document root cause (B_ideal mismatch in optimization loop, Scenario A/B/C)
- Document fix (tensor cloning, device alignment, or code path correction)
- Document usage conventions (ensure B_ideal_reciprocal is immutable, use MOSFLM-derived value consistently)
