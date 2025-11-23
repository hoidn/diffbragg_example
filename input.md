# Loop i=218 — ARCH-REFINE-FLOW-001 Phase C2.2 Out-of-Place HKL Grid Fix

## Summary
Fix gradient-breaking in-place HKL modification by replacing with out-of-place `torch.where` construction.

## Mode
TDD (minimal diagnostic to confirm gradient flow)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2: Stage B CPU fallback gradient fix v2)

## Branch
integration

## Mapped Tests
- Active: `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (Stage B full+small detector smokes)
  - Full detector: CPU fallback path (CUDA OOM forces panel-mode CPU evaluation)
  - Small detector: CUDA warm cache path (regression guard)

Selector command:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full -v
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small -v
```

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/`
- `root_cause_analysis_v2.md` (this analysis)
- `pytest_stage_b_full_fixed.log` (full detector with out-of-place fix)
- `pytest_stage_b_small_fixed.log` (small detector regression guard)
- `decision.md` (4-path synthesis)
- `summary.md` (Turn Summary)

## Do Now

**Context:** Loop i=217 DISPROVED warm cache hypothesis — both warm AND cold paths fail with identical gradient error. Root cause (85% confidence): in-place HKL modification at lines 2441-2447 breaks PyTorch autograd graph because `hkl_grid_modified[mask] = ...` on a non-gradient tensor doesn't propagate `requires_grad=True` from the RHS, even though `shell_modifiers` has gradients.

**Implementation:** ONE focused fix (7 lines) replacing in-place loop with out-of-place `torch.where` construction.

### Step-by-Step Protocol

1. **Review RCA v2** (`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/root_cause_analysis_v2.md`)
   - Read the evidence from loop i=217: diagnostic line 157 shows `shell_modifiers_grad_fn` exists
   - Understand why in-place assignment breaks gradients (PyTorch autograd semantics)

2. **REVERT warm cache fix** (ONE line, dbex/nanobrag_refinement.py:2451)
   ```python
   # BEFORE (loop i=217 fix):
   use_warm_eval = stage_b_use_warm_cache and not use_stage_b_cpu_fallback

   # AFTER (revert):
   use_warm_eval = stage_b_use_warm_cache
   ```

3. **Apply out-of-place HKL grid fix** (SEVEN lines, dbex/nanobrag_refinement.py:2441-2447)
   ```python
   # BEFORE (in-place modification):
   hkl_grid_modified = hkl_grid_local.clone()
   for shell_idx in range(config.stage_b_n_shells):
       mask = (shell_indices_local == shell_idx)
       modifier_value = shell_modifiers[shell_idx]
       if modifier_value.device != eval_device:
           modifier_value = modifier_value.to(device=eval_device)
       hkl_grid_modified[mask] = hkl_grid_local[mask] * modifier_value

   # AFTER (out-of-place construction):
   hkl_grid_modified = hkl_grid_local.clone()
   for shell_idx in range(config.stage_b_n_shells):
       mask = (shell_indices_local == shell_idx)
       modifier_value = shell_modifiers[shell_idx]
       if modifier_value.device != eval_device:
           modifier_value = modifier_value.to(device=eval_device)
       # Out-of-place: creates NEW tensor with gradient graph
       hkl_grid_modified = torch.where(
           mask.unsqueeze(-1),  # Broadcast mask to [panels, slow, fast, 1] → [panels, slow, fast, 4]
           hkl_grid_local * modifier_value,  # Gradient-enabled operation
           hkl_grid_modified  # Keep existing values for non-matching shells
       )
   ```

   **Key change:** Replace `hkl_grid_modified[mask] = hkl_grid_local[mask] * modifier_value` with `torch.where` that creates a NEW tensor each iteration, preserving gradient connections from `modifier_value`.

4. **Add minimal HKL gradient diagnostic** (TWO lines, dbex/nanobrag_refinement.py after line 2447)
   ```python
   # Right after the for-loop, before warm/cold path decision
   print(f"[HKL_GRAD_CHECK] hkl_grid_modified.requires_grad={hkl_grid_modified.requires_grad}, "
         f"grad_fn={hkl_grid_modified.grad_fn}, device={hkl_grid_modified.device}")
   ```

5. **Run full detector test** (CPU fallback path)
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   --smoke-detector-size=full -v 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/pytest_stage_b_full_fixed.log
   ```

6. **Run small detector test** (CUDA warm cache regression guard)
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   --smoke-detector-size=small -v 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/pytest_stage_b_small_fixed.log
   ```

7. **Extract validation metrics** (T0 inline probe)
   ```bash
   python3 -c "
   import re, json

   # Parse both logs
   with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/pytest_stage_b_full_fixed.log') as f:
       full_log = f.read()
   with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/pytest_stage_b_small_fixed.log') as f:
       small_log = f.read()

   # Extract HKL_GRAD_CHECK diagnostic
   hkl_grad_full = re.search(r'\[HKL_GRAD_CHECK\] (.+)', full_log)
   hkl_grad_small = re.search(r'\[HKL_GRAD_CHECK\] (.+)', small_log)

   # Extract test outcomes
   full_pass = 'PASSED' in full_log and 'FAILED' not in full_log
   small_pass = 'PASSED' in small_log and 'FAILED' not in small_log

   # Extract telemetry status
   full_status = re.search(r\"status='([^']+)'\", full_log)
   small_status = re.search(r\"status='([^']+)'\", small_log)

   result = {
       'full_detector': {
           'test_passed': full_pass,
           'hkl_grad_diagnostic': hkl_grad_full.group(1) if hkl_grad_full else 'NOT FOUND',
           'telemetry_status': full_status.group(1) if full_status else 'UNKNOWN'
       },
       'small_detector': {
           'test_passed': small_pass,
           'hkl_grad_diagnostic': hkl_grad_small.group(1) if hkl_grad_small else 'NOT FOUND',
           'telemetry_status': small_status.group(1) if small_status else 'UNKNOWN'
       }
   }

   print(json.dumps(result, indent=2))
   " | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/validation_metrics.json
   ```

8. **Decision synthesis** (4-path protocol)

   **Path A (both PASS):** Both tests PASS, HKL diagnostic shows `requires_grad=True` and non-None `grad_fn`
   - Action: REMOVE diagnostics (lines 2185-2201, 2389-2405, HKL_GRAD_CHECK diagnostic added in step 4)
   - Action: Update `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase C2.2 status → COMPLETE
   - Action: Write `decision.md` documenting Path A outcome with validation metrics
   - Action: Commit message: "ARCH-REFINE-FLOW-001 Phase C2.2: fix gradient-breaking in-place HKL modification — tests: pass"
   - Next loop: Galph plans Phase C validation suite (C3-C6: telemetry completeness + DB-AT-024 parity + doc sync)

   **Path B (full FAIL, small PASS):** Full detector still fails, small detector passes
   - Action: HKL diagnostic shows `requires_grad=True` on both? If YES → escalate to Hypothesis B (nanobrag_torch internal issue)
   - Action: Write `blocker_hypothesis_b.md` documenting nanobrag_torch inspection requirements
   - Action: DO NOT remove diagnostics
   - Action: Commit message: "ARCH-REFINE-FLOW-001 Phase C2.2: out-of-place HKL fix applied, full detector still fails — tests: fail"
   - Next loop: Galph reviews Hypothesis B escalation and decides investigation path

   **Path C (full PASS, small FAIL):** Full detector passes, small detector regresses
   - Action: REVERT out-of-place fix
   - Action: Write `regression_analysis.md` investigating why small detector broke
   - Action: Commit message: "ARCH-REFINE-FLOW-001 Phase C2.2: revert out-of-place HKL fix (small detector regression) — tests: fail"
   - Next loop: Galph reviews regression and decides alternative approach

   **Path D (both FAIL):** Both tests fail with same or different errors
   - Action: Check HKL diagnostic — if `requires_grad=True` appears → Hypothesis B escalation
   - Action: If `requires_grad=False` still → out-of-place fix didn't work, deeper autograd issue
   - Action: Write `blocker_both_fail.md` with diagnostic evidence
   - Action: Commit message: "ARCH-REFINE-FLOW-001 Phase C2.2: out-of-place HKL fix insufficient — tests: fail"
   - Next loop: Galph reviews and decides escalation to nanobrag_torch inspection or alternative architecture

9. **Conditional instrumentation removal** (ONLY if Path A)
   - Remove CPU_FALLBACK_DIAGNOSTICS blocks (lines 2185-2201, dbex/nanobrag_refinement.py)
   - Remove CPU_FALLBACK_DIAGNOSTICS_CLOSURE blocks (lines 2389-2405, dbex/nanobrag_refinement.py)
   - Remove CACHE_MODE_DECISION diagnostic (line 2453, dbex/nanobrag_refinement.py)
   - Remove HKL_GRAD_CHECK diagnostic (added in step 4)

10. **Update implementation.md** (ONLY if Path A)
    - Mark Phase C2.2 status: COMPLETE
    - Note root cause: in-place HKL modification broke gradients
    - Note fix: out-of-place `torch.where` construction preserved gradient graph

11. **Write summary.md** (ALL paths)
    - Turn Summary format (3-5 sentences + Artifacts line)
    - Document which path was taken (A/B/C/D)
    - Note validation metrics from step 7

12. **Commit and push**
    ```bash
    git add -A
    git commit -m "ARCH-REFINE-FLOW-001 Phase C2.2: [PATH X outcome] — tests: [pass|fail]

    Root cause: In-place HKL grid modification (lines 2441-2447) broke PyTorch autograd
    graph because hkl_grid_modified[mask] = ... on non-gradient tensor doesn't propagate
    requires_grad=True from RHS, even though shell_modifiers has gradients.

    Fix: Replaced in-place assignment with out-of-place torch.where construction that
    creates NEW tensor each iteration, preserving gradient connections.

    [Path-specific notes]

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>"
    git push
    ```

## How-To Map

**Commands:**
```bash
# Full detector test (CPU fallback path)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
--smoke-detector-size=full -v

# Small detector test (CUDA regression guard)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
--smoke-detector-size=small -v

# Extract validation metrics
python3 -c "[inline probe from step 7]"
```

**Artifacts destinations:**
- All test logs → `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/`
- Validation metrics JSON → same directory
- Decision/blocker docs → same directory
- Turn Summary → `summary.md` in same directory

**ROI/Thresholds:**
- Path A success: Both tests PASSED, `hkl_grid_modified.requires_grad=True`, `grad_fn` non-None, telemetry `status='converged'` or `'minloss'`
- Any FAIL → follow Path B/C/D decision tree

## Pitfalls To Avoid

1. **In-Place Operations Break Gradients:**
   - NEVER use `tensor[mask] = rhs` on tensors without `requires_grad=True` when RHS has gradients
   - ALWAYS use out-of-place operations (`torch.where`, `torch.cat`, `torch.stack`) to build gradient-enabled tensors
   - Key principle: New tensor = new gradient graph node

2. **Device/Dtype Neutrality:**
   - `torch.where` preserves device/dtype from inputs
   - Verify `mask.unsqueeze(-1)` broadcasts correctly to HKL grid shape `[panels, slow, fast, 4]`
   - Device transfers via `.to()` should preserve gradients (PyTorch standard behavior)

3. **Protected Assets:**
   - DO NOT modify warm cache logic beyond the revert in step 2
   - DO NOT change test selectors or acceptance gates
   - DO NOT remove diagnostics unless Path A (both PASS)

4. **Vectorization Rules:**
   - `torch.where` is fully vectorized and differentiable
   - Broadcasting via `mask.unsqueeze(-1)` is standard PyTorch pattern
   - No manual loops over panels/pixels needed

5. **Environment Freeze:**
   - ASSUME frozen runtime — no pip installs, no CUDA toolkit changes
   - If torch.where fails → document exact error signature in blocker, don't guess alternatives

6. **Diagnostic Hygiene:**
   - Keep HKL_GRAD_CHECK minimal (one print statement)
   - Remove diagnostics ONLY if Path A
   - Preserve diagnostic output in pytest logs for Galph review

7. **Commit Message Structure:**
   - First line: initiative ID + phase + outcome
   - Body: root cause + fix + path taken
   - Tests line: pass|fail (not "not run" — these are execution tests)

8. **Normative Math/Physics:**
   - This fix doesn't change physics/math — just preserves gradient graph
   - Shell modifier logic (softplus + clamp + element-wise multiply) unchanged
   - Loss function (variance-weighted chi-squared) unchanged

## If Blocked

1. **torch.where fails with shape error:**
   - Check `mask.shape` vs `hkl_grid_local.shape` — mask should be `[panels, slow, fast]` and unsqueeze to `[panels, slow, fast, 1]`
   - Log exact shapes and error message
   - Write `blocker_shape_mismatch.md` with diagnostic output

2. **Both tests still fail after fix:**
   - Extract HKL_GRAD_CHECK diagnostic from logs
   - If `requires_grad=False` → out-of-place fix didn't work, document why
   - If `requires_grad=True` but still fails → escalate to Hypothesis B (nanobrag_torch internal)

3. **Small detector regresses:**
   - Check if warm cache path also uses the new HKL grid construction
   - Verify device/dtype consistency between CUDA and CPU paths
   - Write `regression_analysis.md` with comparative diagnostics

4. **Update Attempts History:**
   ```
   * 2025-11-23T111500Z (ready_for_implementation, Loop i=218) — Applied out-of-place HKL grid fix
     (torch.where construction) to preserve gradient graph, reverted warm cache hypothesis fix
     (loop i=217 disproven). [Outcome: Path X]. Artifacts: plans/.../2025-11-23T111500Z/.
   ```

## Findings Applied

- **PERF-WARM-011:** CPU fallback requirement for canonical Stage B (CUDA OOM) — preserved
- **PERF-WARM-012:** CPU context cloning for warm cache — preserved (revert doesn't affect this)
- **POLICY-001:** Environment Freeze — no external installs, targeted bugfix to local source
- **RUNTIME-001:** `NANOBRAGG_DISABLE_COMPILE=1` required for gradient tests
- **CONFORMANCE-001:** `KMP_DUPLICATE_LIB_OK=TRUE` required for test execution
- **REFINE-008:** ±1% shell modifier gate for canonical runs — validation criteria unchanged
- **GRADIENT-002 (DRAFT):** In-place tensor modification breaks autograd — this fix implements the remedy

## Pointers

- **Root Cause Analysis:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/root_cause_analysis_v2.md`
- **Loop i=217 Blocker:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/blocker_hypothesis_disproven.md`
- **Implementation Plan:** `plans/active/ARCH-REFINE-FLOW-001/implementation.md` (Phase C2.2)
- **Fix Plan Entry:** `docs/fix_plan.md` [ARCH-REFINE-FLOW-001]
- **Spec Reference:** `docs/spec-db-workflow.md` §7 (Stage B physics and tricubic interpolation)
- **Testing Guide:** `docs/TESTING_GUIDE.md` §2 (Stage B smoke selectors)

## Next Up

**If Path A (both PASS):**
- Galph plans Phase C validation suite (next loop i=219):
  - C3: Telemetry completeness validation
  - C4: Full Stage B/C smoke suite (canonical + small detector)
  - C5: DB-AT-024 mapping consistency guard
  - C6: Documentation sync (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)

**If Path B/C/D (any FAIL):**
- Galph reviews blocker and decides escalation path:
  - Hypothesis B: Inspect nanobrag_torch.Simulator.run() for gradient-breaking operations
  - Alternative: Different HKL grid construction approach
  - Architectural: Rethink Stage B parameter-to-HKL mapping

## Doc Sync Plan

**Not applicable this loop** — No tests added/renamed, no selector changes. Documentation sync deferred to Phase C validation suite (after Path A success).
