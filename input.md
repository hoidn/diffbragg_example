# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase B1 Diagnostic Rerun

## Summary
Diagnose and fix LBFGS Test B1 premature termination; rerun with corrected telemetry paths and foreground execution.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (already passed in commit 8440df8)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/

## Do Now

**Checklist Items:** Phase B1 Diagnostic + Rerun (addressing premature termination and telemetry path duplication)

**Context:** Ralph's Phase B1 implementation (commit 8440df8) successfully added LBFGS optimizer infrastructure and regression guard PASSED. However, the LBFGS test terminated prematurely with incomplete artifacts:
- Zero-point check PASSED (chi²=989k, rel_diff=-0.017%, correlation=0.9999999843) — B_ideal bugfix IS working
- Telemetry step_000 shows catastrophic chi²=1.425B (pre-bugfix signature) and massive log_scale gradient (294k)
- Log has only 69 lines (HKL grid warmup), no block_dof_results.json, test stopped during first LBFGS line search
- Telemetry path duplicated: `plans/.../2025-11-22T165000Z/plans/.../2025-11-22T165000Z/telemetry/` (double-prepending bug)

**Diagnosis (see `phase_b1_diagnostic_analysis.md`):** Four hypotheses:
- **H1:** B_ideal mismatch persists in LBFGS closure despite bugfix (different code path than zero-point check)
- **H2:** Telemetry captures wrong timestep (exploratory line-search evaluation, not accepted step)
- **H3:** Telemetry path duplication caused data corruption or misdirection
- **H4:** LBFGS line search hit bad parameter region during backtracking

**Decision:** Quick diagnostic rerun (Option B from analysis) with:
1. Fixed telemetry paths (remove `--telemetry-dir` flag, use auto-construction from `--out-dir`)
2. Foreground execution (blocking, wait for completion, no background bash)
3. Explicit timeout monitoring (1200s, log progress every 60s if possible)
4. Capture complete artifacts: telemetry_step_{0..9}.json, block_dof_results.json, stage_a_lbfgs_test.log

If rerun STILL shows chi²=1.425B at step 0, escalate to deep diagnostic (instrument closure with B_ideal checksums).

### Step 1: Review Prior Attempt Artifacts

Read and summarize:
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/zero_point_check.json` (zero-point validation)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/plans/.../telemetry/telemetry_step_000.json` (problematic telemetry)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/stage_a_lbfgs_test.log` (truncated log)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b1_diagnostic_analysis.md` (Galph's diagnosis)

Emit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/phase_b1_review.md` with:
- Zero-point chi² values (mapping vs stage_a)
- Telemetry step 000 chi² and gradient magnitudes
- Hypothesis selection (which of H1-H4 is most likely)
- Recommended fix for rerun

### Step 2: Verify LBFGS Script Invocation

Check `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` for:
1. **Telemetry path construction:** How does script handle `--telemetry-dir` and `--out-dir` interaction?
2. **Telemetry emission timing:** Is telemetry written INSIDE closure (bad — captures line-search probes) or AFTER optimizer.step() (good — captures accepted steps)?
3. **B_ideal usage in LBFGS closure:** Confirm `components.B_ideal_reciprocal` is used for A* reconstruction at line ~436

Document findings in `phase_b1_review.md`.

### Step 3: Fix Telemetry Path Construction (If Needed)

**Option A: Remove --telemetry-dir flag entirely**
If script auto-constructs telemetry path from `--out-dir`, do:
```python
# In stage_a_mapping_adam_debug.py, find telemetry path construction (~line 150-180 or wherever RefinementConfig is built)
# Change from:
telemetry_output_dir=args.telemetry_dir if args.telemetry_dir else None
# To:
telemetry_output_dir=os.path.join(args.out_dir, "telemetry") if args.out_dir else None
```

**Option B: Fix path duplication if script double-prepends**
If script does `os.path.join(args.out_dir, args.telemetry_dir)` when `--telemetry-dir` is already an absolute or out-dir-relative path, fix the logic:
```python
# Change from:
telemetry_output_dir = os.path.join(args.out_dir, args.telemetry_dir)
# To:
if args.telemetry_dir.startswith(args.out_dir):
    telemetry_output_dir = args.telemetry_dir  # Already absolute or relative to out_dir
else:
    telemetry_output_dir = os.path.join(args.out_dir, args.telemetry_dir)
```

**Your task:** Inspect script, identify which option applies, implement fix if needed. Document in `phase_b1_review.md`.

### Step 4: Rerun LBFGS Test B1 in Foreground

Execute the test with corrected paths and FOREGROUND execution (blocking, no background):

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/stage_a_lbfgs_rerun.log
```

**Note:** Removed `--telemetry-dir` flag; let script auto-construct from `--out-dir` (per Step 3 fix).

**Expected duration:** 10-20 minutes on CPU (LBFGS line search is slow). Monitor log for progress indicators:
- HKL grid builds (expected: many, due to line search)
- "Stage A: Using LBFGS optimizer for U-matrix path" message
- Telemetry step emissions (if script logs them)
- Final "Phase 5 complete" or similar message

**Blocking behavior:** Wait for command to complete (exit code 0 = success, 124 = timeout, other = error). Do NOT use `run_in_background`.

### Step 5: Extract LBFGS Convergence Metrics

After Step 4 completes, check artifacts:

```bash
# 1. Verify telemetry path is clean (no duplication)
ls -la plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/ || echo "Telemetry dir missing"

# 2. Count telemetry steps (expect 10 files: step_000 through step_009)
ls -1 plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_*.json | wc -l

# 3. Extract chi² from step 000 (first accepted step)
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_000.json

# 4. Extract chi² from step 009 (final step)
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_009.json

# 5. Check block_dof_results.json (final convergence metrics)
jq '.A_scale_only | {median_cc_after: .cc_summary.median_after, chi2_before: .chi_squared.before, chi2_after: .chi_squared.after, chi2_ratio: (.chi_squared.after / .chi_squared.before)}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/block_dof_results.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/phase_b1_lbfgs_metrics.json
```

### Step 6: Synthesize Test B1 Decision

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/phase_b1_decision.md`:

```markdown
# Phase B1 LBFGS Test Decision

## Test Configuration
- Optimizer: torch.optim.LBFGS(lr=1.0, max_iter=20, line_search_fn='strong_wolfe')
- Parameters: q_params (quaternion, train_orientation=False for A_scale_only), log_scale
- Variant: A_scale_only (scale-only refinement, orientation fixed)
- Steps: 10 optimizer.step() calls
- Execution: Foreground, timeout=1200s

## Zero-Point Validation (Pre-Optimization)
- Chi² mapping path: [paste from zero_point_check.json .chi2.mapping]
- Chi² stage_a (U-matrix): [paste from .chi2.stage_a]
- Relative difference: [paste from .chi2.rel_diff]
- Verdict: [PASSED if abs(rel_diff) < 0.001, else FAILED]

## Telemetry Step 000 (First LBFGS Step)
- Chi²: [paste from telemetry_step_000.json .chi_squared]
- log_scale gradient: [paste from .grad_log_scale]
- Verdict: [OK if chi² ~1M, CATASTROPHIC if chi² ~1.4B]

## Convergence Metrics (A_scale_only after 10 steps)
- Chi² before: [paste from phase_b1_lbfgs_metrics.json .chi2_before]
- Chi² after: [paste from .chi2_after]
- Chi² ratio: [paste from .chi2_ratio]
- Median CC after: [paste from .median_cc_after]

## Decision Path

### Path A: LBFGS Convergence SUCCESS
**Criteria:** Chi² step 000 ~1M (not 1.4B) AND median_cc_after ≥ 0.99 AND chi2_ratio ≤ 1.005

**Verdict:** H1 CONFIRMED — Adam optimizer is incompatible with quaternion U-matrix; LBFGS resolves convergence pathology.

**Recommended Actions:**
1. Mark Phase B checklist B0-B1 complete (skip B2-B3)
2. Proceed to Phase C fix implementation (C1: make LBFGS default for U-matrix path)
3. Validate Phase C: run A_scale_only + D_full convergence tests, regression guard, findings update

### Path B: LBFGS Convergence FAILURE (Chi² Step 000 Catastrophic)
**Criteria:** Chi² step 000 ~1.4B (matches pre-bugfix signature)

**Verdict:** B_ideal mismatch persists in LBFGS closure despite bugfix 826f4c9. H1 INCONCLUSIVE.

**Recommended Actions:**
1. Implement deep diagnostic (Priority 1 from phase_b1_diagnostic_analysis.md):
   - Add B_ideal checksum logging to LBFGS closure (hash tensor, print first/last elements)
   - Add A* reconstruction logging (compare U @ B_ideal vs expected MOSFLM A*)
   - Add per-closure-call chi² logging to identify EXACT divergence point
2. Rerun diagnostic variant, analyze where chi² diverges
3. Fix root cause (likely tensor aliasing, device mismatch, or incorrect pass-by-reference)
4. Rerun Test B1 after fix

### Path C: LBFGS Convergence PARTIAL
**Criteria:** Chi² step 000 OK (~1M) BUT median_cc_after < 0.99 OR chi2_ratio > 1.005

**Verdict:** LBFGS improves upon Adam but doesn't fully resolve convergence pathology.

**Recommended Actions:**
1. Analyze telemetry trajectories (chi² and gradients across steps 0-9)
2. Check for early termination (tolerance_grad met prematurely)
3. Try LBFGS with tighter tolerances (tolerance_grad=1e-9, max_iter=50)
4. If second run still partial: proceed to Test B2 (Adam LR=1e-6 + gradient validation)

## Selected Path
[Path A / Path B / Path C]

## Confidence Level
[High / Medium / Low]

## Rationale
[2-3 sentences explaining why this path was selected based on metrics]
```

**Your task:** Fill in all bracketed placeholders with actual values from artifacts, select Path A/B/C, document confidence and rationale.

### Step 7: Conditional Deep Diagnostic (If Path B)

**Only execute if Step 6 selected Path B (chi² step 000 catastrophic).**

Edit `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` to add B_ideal checksum logging:

Find the LBFGS closure construction (~line 800-900, inside `_stage_a_adam_core`), add logging:

```python
def closure():
    optimizer.zero_grad()

    # CONVERGENCE-001 Deep Diagnostic: Log B_ideal consistency
    if step_index == 0:  # Only log first closure call
        B_ideal_hash = hash(components.B_ideal_reciprocal.data_ptr())
        B_ideal_first = components.B_ideal_reciprocal[0, 0].item()
        B_ideal_last = components.B_ideal_reciprocal[2, 2].item()
        logger.info(f"[DIAGNOSTIC] B_ideal hash={B_ideal_hash}, first={B_ideal_first:.6e}, last={B_ideal_last:.6e}")

        # Reconstruct A* and compare to MOSFLM reference
        q_norm = q_params / torch.norm(q_params)
        U_matrix = quaternion_to_matrix(q_norm)
        A_star_reconstructed = U_matrix @ components.B_ideal_reciprocal
        # Assuming MOSFLM A* is available as a reference tensor somewhere...
        # logger.info(f"[DIAGNOSTIC] A* reconstruction vs MOSFLM: max_diff={...}")

    loss = compute_loss_stage_a(...)
    loss.backward()

    # Log chi² per closure call
    if step_index == 0:
        logger.info(f"[DIAGNOSTIC] Closure call, chi²={loss.item():.3e}")

    return loss
```

**Note:** This requires access to MOSFLM A* reference. If not readily available in closure scope, skip A* comparison and just log B_ideal hash/values.

Rerun test with diagnostic logging:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 2 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/stage_a_diagnostic.log
```

**Reduced to 2 steps** to save time; we only need first closure calls to diagnose B_ideal.

Grep diagnostic log for B_ideal hash and chi² values:
```bash
grep "\[DIAGNOSTIC\]" plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/stage_a_diagnostic.log \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/b_ideal_diagnostic.txt
```

Document findings in `phase_b1_decision.md` under "Deep Diagnostic Results" section.

### Step 8: Update Implementation Plan Checklist

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:

**Mark Phase B items based on Step 6 decision:**
- [x] B0: **Test Protocol Design** — Prioritized H1 (LBFGS) → H1+H3 (LR+gradients) → H2 (variance). DONE (2025-11-22T165000Z).
- [x] B1: **Execute Test 1 (LBFGS)** — [If Path A: SUCCESS, chi²_ratio=[value], CC=[value]. If Path B: BLOCKED, B_ideal mismatch persists, deep diagnostic required. If Path C: PARTIAL, chi²_ratio=[value], CC=[value]]. DONE (2025-11-22T172000Z).
- [ ] B2: **Execute Test 2 (Adam LR tuning)** — [SKIPPED if Path A, PENDING if Path B or Path C]
- [ ] B3: **Execute Test 3 (Variance analysis)** — [SKIPPED if Path A, PENDING otherwise]
- [ ] B4: **Test Result Synthesis** — [DONE if Path A, PENDING otherwise]

**Add checklist note to B1:**
```markdown
**Test B1 Rerun (2025-11-22T172000Z):** LBFGS test executed in foreground with corrected telemetry paths. [Decision: Path A/B/C]. Chi² step 000=[value], chi²_ratio=[value], median CC after=[value]. [If Path A: Proceed to Phase C fix. If Path B: Escalate to deep diagnostic. If Path C: Rerun with tighter tolerances or proceed to Test B2.]
```

### Step 9: Summary Emission

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/summary.md`:

```markdown
# Phase B1 LBFGS Test Rerun Summary

## What Was Done
- Diagnosed Phase B1 premature termination (2025-11-22T165000Z): zero-point check PASSED (chi²=989k) but telemetry step 000 showed catastrophic chi²=1.425B
- Fixed telemetry path duplication [describe fix: removed --telemetry-dir / fixed double-prepending]
- Reran LBFGS test B1 in foreground (blocking, timeout=1200s)
- Extracted convergence metrics: chi² step 000=[value], chi²_ratio=[value], median CC=[value]
- [If Path B: Implemented deep diagnostic with B_ideal checksum logging and reran 2-step diagnostic variant]

## Results
- **Zero-Point Validation:** chi²_mapping=[value], chi²_stage_a=[value], rel_diff=[value]% → [PASSED/FAILED]
- **LBFGS Convergence:** chi² before=[value], chi² after=[value], ratio=[value], median CC after=[value]
- **Decision:** [Path A SUCCESS / Path B BLOCKED / Path C PARTIAL]

## Next Steps
- [If Path A: Proceed to Phase C fix implementation (C1-C6: make LBFGS default, validate A_scale_only + D_full, findings update)]
- [If Path B: Fix B_ideal mismatch root cause identified in deep diagnostic, rerun Test B1]
- [If Path C: Rerun LBFGS with tighter tolerances OR proceed to Test B2 (Adam LR=1e-6)]

## Artifacts
- `phase_b1_review.md` — Prior attempt review and hypothesis selection
- `phase_b1_decision.md` — Test B1 decision with full metrics and path selection
- `phase_b1_lbfgs_metrics.json` — Extracted convergence metrics (chi², CC)
- `stage_a_lbfgs_rerun.log` — Full test log (foreground execution)
- `telemetry/telemetry_step_{000..009}.json` — Per-step parameter/gradient/loss telemetry
- `block_dof_results.json` — Final DoF results for A_scale_only variant (if test completed)
- [If Path B: `diagnostic/b_ideal_diagnostic.txt` — B_ideal checksum and chi² per closure call]
```

## How-To Map

**Review Prior Artifacts (Step 1):**
```bash
# No commands; read JSON/markdown files from 2025-11-22T165000Z/ and synthesize in phase_b1_review.md
```

**Verify Script Invocation (Step 2):**
```bash
# Inspect stage_a_mapping_adam_debug.py for telemetry path construction
# Use Read tool or grep for "telemetry_dir", "out_dir", "RefinementConfig", "os.path.join"
```

**Fix Telemetry Paths (Step 3):**
```bash
# Edit plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
# Implement Option A or B per instructions above
```

**Rerun LBFGS Test (Step 4):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/stage_a_lbfgs_rerun.log
```

**Extract Metrics (Step 5):**
```bash
ls -la plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/
ls -1 plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_*.json | wc -l
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_000.json
jq '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_009.json
jq '.A_scale_only | {median_cc_after: .cc_summary.median_after, chi2_before: .chi_squared.before, chi2_after: .chi_squared.after, chi2_ratio: (.chi_squared.after / .chi_squared.before)}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/block_dof_results.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/phase_b1_lbfgs_metrics.json
```

**Deep Diagnostic (Step 7, conditional on Path B):**
```bash
# Edit stage_a_mapping_adam_debug.py to add B_ideal checksum logging per template above
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 2 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/stage_a_diagnostic.log
grep "\[DIAGNOSTIC\]" plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/stage_a_diagnostic.log \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/diagnostic/b_ideal_diagnostic.txt
```

## Pitfalls To Avoid

1. **Background execution:** Do NOT use `run_in_background` or bash `&` operator. Test must run in foreground (blocking) so you can verify completion and exit code.

2. **Telemetry path duplication:** Do NOT pass both `--telemetry-dir` and `--out-dir` if script auto-constructs paths. Remove `--telemetry-dir` flag entirely or fix double-prepending logic.

3. **Timeout interpretation:** Exit code 124 means timeout (1200s exceeded). If this occurs, LBFGS is too slow for 10 steps on CPU. Document in decision.md and consider: (a) reduce to 5 steps, (b) increase timeout to 2400s, (c) switch to Test B2 (Adam LR tuning).

4. **Incomplete artifacts:** After Step 4, verify ALL expected files exist (telemetry steps 0-9, block_dof_results.json, zero_point_check.json). If missing, test did NOT complete successfully; check log for errors/tracebacks.

5. **Chi² catastrophic vs bad:** Chi²=1.425B (1.4 billion) is CATASTROPHIC (pre-bugfix signature, Path B). Chi²=1.13M→3M (millions) is BAD but not catastrophic (Path C, partial improvement). Chi²=990k→1.005M is GOOD (Path A, stable/improving).

6. **Path C ambiguity:** If chi²_ratio=1.001 (barely within tolerance) but median_cc=0.985 (below 0.99), prioritize CC metric — this is Path C (partial), not Path A (success).

7. **Deep diagnostic scope:** Step 7 is ONLY for Path B (catastrophic chi² at step 0). Do NOT execute if Path A or Path C; it wastes time and adds complexity.

8. **Protected Assets:** Do not modify `dbex/nanobrag_refinement.py` (LBFGS infrastructure already implemented in 8440df8). Changes scoped to `stage_a_mapping_adam_debug.py` (telemetry path fix, optional diagnostic logging).

9. **Regression guard:** Already passed in commit 8440df8 (pytest_stage_a_regression.log, 13.16s). Do NOT rerun unless you modify production code (dbex/*.py).

10. **Decision document completeness:** Step 6 phase_b1_decision.md MUST include ALL metrics (chi² step 0, chi²_ratio, median CC, path selection, confidence, rationale). Do NOT leave placeholders unfilled or TBD.

## If Blocked

**If test times out (exit code 124, Step 4):**
- Check log: Is progress being made (HKL grid builds, telemetry emissions)?
- If yes: Extend timeout to 2400s and rerun
- If no (stuck/stalled): Kill test, mark Path B (escalate to deep diagnostic to find why LBFGS stalls)

**If telemetry path still duplicated after Step 3 fix:**
- Inspect script more carefully: Search for ALL `os.path.join` calls involving telemetry_dir
- Add debug print before path construction: `print(f"DEBUG: out_dir={args.out_dir}, telemetry_dir={args.telemetry_dir if hasattr(args, 'telemetry_dir') else 'NONE'}")`
- Rerun with debug print, capture output, identify where duplication originates

**If block_dof_results.json missing after Step 4 completion (exit code 0):**
- Check log for "Phase 5 complete" or equivalent message
- If message present but JSON missing: Script output path logic is buggy, check `--out-dir` handling
- If message absent: Test terminated early (silent failure), check for exceptions/warnings in log

**If Path B deep diagnostic (Step 7) shows B_ideal hash CHANGES between closure calls:**
- **Root cause:** components.B_ideal_reciprocal tensor is being mutated or reallocated during optimization
- **Fix:** In `_stage_a_adam_core` or wherever components are built, ensure B_ideal_reciprocal is cloned/copied and frozen: `components.B_ideal_reciprocal = B_ideal_reciprocal.clone().detach()`

**If Path B deep diagnostic shows B_ideal hash STABLE but chi² still catastrophic:**
- **Root cause:** The B_ideal tensor is correct but A* reconstruction `U @ B_ideal` produces wrong result due to device mismatch, dtype mismatch, or incorrect matrix multiplication
- **Fix:** Add device/dtype logging: `logger.info(f"U device={U_matrix.device}, B device={components.B_ideal_reciprocal.device}, U dtype={U_matrix.dtype}, B dtype={components.B_ideal_reciprocal.dtype}")`. Ensure both are on same device and dtype before matmul.

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start): Directly applicable — LBFGS proven for scale-only; reusing for quaternion U-matrix test. NaN/Inf guards assumed active.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Relevant if chi² explodes due to variance denominator issues. Monitor telemetry for clamp_fraction spikes.
- **GRADIENT-001** (autograd graph preservation): Critical for LBFGS closure — closure must NOT use `.item()` or `.numpy()` on differentiable tensors before `.backward()`.
- **GEOMETRY-003** (baseline misset derivation): Not applicable to U-matrix path (no misset in quaternion parameterization).
- **GEOMETRY-004** (U-matrix parameterization conventions): Directly applicable — Test B1 validates whether LBFGS resolves quaternion convergence pathology.
- **CONVERGENCE-001 Phase A Bugfix (826f4c9)**: `derive_u_matrix_from_mosflm_a_star` now returns `(U_matrix, B_ideal_reciprocal)` tuple; both call sites updated. Zero-point validation confirms bugfix works. If chi² step 000 still catastrophic, bugfix is incomplete (different code path).

## Pointers

- **Prior Attempt:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/ (premature termination, telemetry path duplication)
- **Diagnostic Analysis:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b1_diagnostic_analysis.md (4 hypotheses, decision tree)
- **Phase B Protocol:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/phase_b_test_protocol.md (LBFGS rationale, success criteria)
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (Phase B checklist B0-B4, Phase C checklist C1-C6)
- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence requirements)
- **Optimizer Code:** dbex/nanobrag_refinement.py:810-835 (LBFGS branch already implemented in 8440df8)
- **Script:** plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py (telemetry path construction to fix, LBFGS closure to instrument)

## Next Up (Optional)

If you finish Step 8 early AND Step 6 selected Path A (LBFGS success):
- Read Phase C checklist (C1-C6 in implementation.md)
- Note Phase C deliverables:
  - C1: Make LBFGS switch permanent (default to True when use_u_matrix=True, document rationale)
  - C2: Phase 5 A_scale_only validation (full 10 steps, verify CC ≥ 0.99, chi² stable)
  - C3: Phase 5 D_full validation (multi-DoF, verify monotonic chi² improvement)
  - C4: Regression guard (already passed, just verify)
  - C5: Findings update CONVERGENCE-002 (root cause, fix, usage conventions)
  - C6: Fix-plan close (mark CONVERGENCE-001 done, unblock PARITY-003)
- Do NOT implement Phase C this loop; just prep context for next handoff

If Step 6 selected Path B (LBFGS blocked):
- Focus Step 7 deep diagnostic on identifying B_ideal mismatch root cause
- Document findings thoroughly in phase_b1_decision.md
- Recommend specific fix (tensor cloning, device/dtype alignment, or alternate B_ideal derivation)

If Step 6 selected Path C (LBFGS partial):
- Analyze telemetry trajectories (plot chi² and gradients vs step if time permits)
- Identify whether LBFGS converged prematurely (tolerance_grad met) or hit plateau (no further improvement possible)
- Recommend either tighter tolerances rerun OR switch to Test B2 (Adam LR tuning)

## Doc Sync Plan

Not applicable (no tests added/renamed this loop). Test B1 is validation only; regression guard already passed in commit 8440df8.

If Phase C is reached (after successful Test B1), C5 findings update will include:
- Create/extend CONVERGENCE-002 in docs/findings.md
- Document root cause (Adam momentum vs LBFGS line search)
- Document fix (LBFGS optimizer for U-matrix path)
- Document usage conventions (`use_lbfgs_for_u_matrix=True` recommended when `use_u_matrix_parameterization=True`)
