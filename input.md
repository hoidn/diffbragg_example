# Input for Ralph — Phase C2.4 CPU HKL Grid Device Routing Fix

## Summary
Fix HKL grid device routing bug in Stage B CPU fallback path: use `stage_b_eval_stage_a_ctx.hkl_grid` (CPU-native) instead of transferring CUDA `hkl_grid` every closure iteration.

## Mode
none (targeted bugfix + validation)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.4: dbex Stage B CPU warm-cache HKL grid device routing fix)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (full detector, CPU fallback path)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (small detector, regression guard)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/`
- `decision.md` — Root cause analysis + fix rationale
- `pytest_stage_b_full_fixed.log` — Full detector test with fix (expected PASS)
- `pytest_stage_b_small_regression.log` — Small detector regression guard (expected PASS)
- `validation_metrics.json` — Test results + telemetry comparison
- `summary.md` — Turn Summary block

## Do Now

### Root Cause (HIGH confidence ~95%)

**Bug:** HKL grid device mismatch in Stage B CPU fallback path.

**Evidence:**
1. Loop i=220 minimal reproducer PASSED (99% Bragg coverage on CPU) → nanobrag_torch works correctly ✓
2. Loop i=219 full test FAILED (0% Bragg coverage on CPU despite 100% parameter parity) → dbex bug ✓
3. Line 2464 in `_build_stage_b_lbfgs_closure`: `hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)`
   - `hkl_grid` is the CUDA tensor from parent scope (line 3631)
   - When CPU fallback active: `eval_device='cpu'`, `device='cuda:0'` → transfers CUDA→CPU every closure call
   - **But**: CPU context already has a CPU-native `hkl_grid` stored in `stage_b_eval_stage_a_ctx.hkl_grid` (built at line 2234-2246, stored at `_build_stage_a_context` line 657)
   - **Expected**: Use `stage_b_eval_stage_a_ctx.hkl_grid` (CPU-native) when CPU fallback active
   - **Actual**: Transfers CUDA `hkl_grid` → CPU every time, creating device mismatch or data corruption

**Why reproducer worked:** Reproducer builds fresh CPU context with CPU `hkl_grid` from scratch, no CUDA→CPU transfer.

**Why full test failed:** CPU closure uses wrong `hkl_grid` source (CUDA parent scope instead of CPU context).

### Fix Strategy

**Targeted 5-line fix** at `dbex/nanobrag_refinement.py:2464`:

Replace:
```python
hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)
```

With:
```python
if use_stage_b_cpu_fallback and stage_b_eval_stage_a_ctx is not None:
    # CPU fallback: use CPU-native HKL grid from cloned Stage A context (PERF-WARM-012)
    hkl_grid_local = stage_b_eval_stage_a_ctx.hkl_grid
else:
    # Normal path: transfer to eval device if needed
    hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)
```

**Rationale:**
- When CPU fallback is active, `stage_b_eval_stage_a_ctx` is a CPU-native context built at line 2234-2246 via `_build_stage_a_context(..., device='cpu', ...)`.
- That context's `hkl_grid` (stored at line 657 in `_build_stage_a_context`) is already on CPU device and has correct dtype.
- Using it directly avoids repeated CUDA→CPU transfers and ensures device consistency throughout the closure.
- When CPU fallback is NOT active (`use_stage_b_cpu_fallback=False`), use the existing logic (transfer if devices differ).

### Steps (11 tasks)

1. **Review Phase C2.3 evidence** (5 min)
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/phase_c2_3_decision.md` (Path A: dbex cache/context bug confirmed)
   - Read reproducer result (`reproducer_result.json`: PASS, 99% Bragg, max=0.086, mean=0.0027)
   - Confirm root cause hypothesis: HKL grid device routing bug in closure

2. **Apply targeted fix** (10 min)
   - Open `dbex/nanobrag_refinement.py`
   - Locate line 2464: `hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)`
   - Replace with CPU fallback branch logic (5-line conditional per Fix Strategy above)
   - Verify line numbers after edit (shell_indices_local should be next line)

3. **Add inline comment explaining fix** (2 min)
   - Above the fix, add comment referencing ARCH-REFINE-FLOW-001 Phase C2.4 and reproducer evidence:
     ```python
     # ARCH-REFINE-FLOW-001 Phase C2.4: When CPU fallback active, use CPU-native HKL grid from
     # stage_b_eval_stage_a_ctx (built at line 2234-2246) instead of transferring CUDA hkl_grid.
     # Minimal reproducer (loop i=220) proved CPU simulator works with native CPU HKL grid;
     # CUDA→CPU transfer in closure causes device mismatch or data corruption (0% Bragg output).
     ```

4. **Remove temporary diagnostics** (5 min)
   - Delete diagnostic blocks added in loop i=219:
     - Lines 2228-2232 (`[CRYSTAL_CPU_PRE]` print statements)
     - Lines 550-558 in `_build_stage_a_context` (`[CRYSTAL_CPU_POST]` / `[CRYSTAL_CUDA_POST]` prints)
     - Lines 930-934 (`[CRYSTAL_CUDA_PRE]` if they exist)
     - Lines 2556-2558 (`[BRAGG_CPU_WARM]` diagnostic)
     - Lines 2589-2591 (`[BRAGG_CPU_COLD]` diagnostic)
     - Lines 2204-2219 (`CPU_FALLBACK_DIAGNOSTICS_PARAMS` JSON dump)
   - Keep HKL_GRAD_CHECK diagnostic at line 2479-2481 (useful for future gradient debugging)

5. **Compilation check** (1 min)
   - Run: `python -c "import dbex.nanobrag_refinement; print('OK')"`
   - Expected: `OK` (exit code 0)
   - If import error: fix syntax, rerun

6. **Run full detector test with fix** (3 min)
   - Execute:
     ```bash
     DBEX_SMOKE_DETECTOR_SIZE=full \
     DBEX_SMOKE_SIGMA_SOURCE=cli_override \
     KMP_DUPLICATE_LIB_OK=TRUE \
     NANOBRAGG_DISABLE_COMPILE=1 \
     pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
       > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/pytest_stage_b_full_fixed.log 2>&1
     echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/pytest_stage_b_full_fixed.log
     ```
   - Expected: **PASSED** (exit code 0, non-zero Bragg output on CPU, telemetry status='ok')
   - Runtime: ~120-150s (CPU fallback path)
   - Capture: Full pytest log with telemetry

7. **Run small detector regression guard** (1 min)
   - Execute:
     ```bash
     DBEX_SMOKE_DETECTOR_SIZE=small \
     DBEX_SMOKE_SIGMA_SOURCE=cli_override \
     KMP_DUPLICATE_LIB_OK=TRUE \
     NANOBRAGG_DISABLE_COMPILE=1 \
     pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
       > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/pytest_stage_b_small_regression.log 2>&1
     echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/pytest_stage_b_small_regression.log
     ```
   - Expected: PASSED (exit code 0, ROI mode unchanged)
   - Runtime: ~15s

8. **Extract validation metrics** (5 min)
   - Parse both logs for test status (PASSED/FAILED), telemetry status, Bragg stats, chi² improvement
   - Create `validation_metrics.json`:
     ```json
     {
       "full_detector_test": "PASSED"|"FAILED",
       "small_detector_test": "PASSED"|"FAILED",
       "full_detector_telemetry_status": "ok"|"error",
       "small_detector_telemetry_status": "ok"|"error",
       "full_detector_bragg_nonzero": true|false,
       "full_detector_improvement_pct": <float>,
       "small_detector_improvement_pct": <float>,
       "overall_verdict": "PASS"|"FAIL"
     }
     ```
   - Set `overall_verdict='PASS'` if both tests PASSED and full detector has non-zero Bragg

9. **Decision synthesis** (10 min)
   - Write `decision.md` with 4-path template:
     - **Path A (both tests PASS, full Bragg nonzero):** Fix successful → remove remaining diagnostics → Phase C validation (C3-C5)
     - **Path B (full test FAIL, small test PASS):** Fix incomplete → deeper investigation (HKL grid modification, simulator cache invalidation)
     - **Path C (both tests FAIL):** Fix regression → revert and escalate
     - **Path D (full test PASS but zero Bragg):** Partial success → additional diagnostics needed
   - Include confidence assessment (HIGH ~95% for Path A expected)
   - Reference reproducer evidence (loop i=220 PASS), parameter parity (loop i=219 100% match), and fix rationale (CPU-native HKL grid)

10. **Update implementation.md checklist** (3 min)
    - Mark `C2.4` (CPU HKL grid device routing fix) as COMPLETE with timestamp and commit hash
    - Add next actions: Phase C validation (C3-C5) if Path A, or debug/escalate if Path B/C/D

11. **Write summary.md with Turn Summary** (5 min)
    - Include Turn Summary block (3-5 sentences: fix applied, test results, next step)
    - Prepend to existing `summary.md` content (if file exists) or create new
    - Format per galph_memory.md:122-131 template

12. **Commit and push** (2 min)
    - `git add -A`
    - Commit message:
      ```
      ARCH-REFINE-FLOW-001 Phase C2.4: Fix CPU HKL grid device routing

      - Use stage_b_eval_stage_a_ctx.hkl_grid (CPU-native) when CPU fallback active
      - Avoids CUDA→CPU transfer of parent scope hkl_grid in closure
      - Full detector test PASS (expected), small detector regression guard PASS
      - Remove loop i=219 crystal config diagnostics (retained HKL_GRAD_CHECK)
      - Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T122329Z/

      Refs: Phase C2.3 reproducer (99% Bragg on CPU), Phase C2.2 (100% param parity)
      Tests: test_stage_b_shell_modifiers (full+small) — validation_metrics.json
      ```
    - `git push`

## How-To Map

**Compilation check:**
```bash
python -c "import dbex.nanobrag_refinement; print('OK')"
```

**Full detector test:**
```bash
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```

**Small detector regression guard:**
```bash
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```

**Expected outcomes:**
- Full detector: PASSED, telemetry status='ok', Bragg nonzero (mean ~0.001-0.01, max >0.01)
- Small detector: PASSED, telemetry status='ok' (regression guard, ROI mode unchanged)

## Pitfalls To Avoid

1. **Do NOT transfer HKL grid in closure when CPU fallback active**: Use `stage_b_eval_stage_a_ctx.hkl_grid` directly (already on CPU device from line 2234-2246 context builder).
2. **Do NOT remove HKL_GRAD_CHECK diagnostic** (lines 2479-2481): Useful for future gradient debugging; only remove crystal config diagnostics.
3. **Do NOT modify Stage A code**: This fix is Stage B-specific; Stage A unaffected.
4. **Verify `use_stage_b_cpu_fallback` is available in closure scope**: Should be accessible (passed via closure parameters at line 2329).
5. **Check `stage_b_eval_stage_a_ctx` is not None**: Guard the CPU fallback branch with `stage_b_eval_stage_a_ctx is not None` to avoid AttributeError.
6. **Ensure shell_indices_local uses same logic**: Line 2465 should also use CPU-native `stage_b_eval_stage_a_ctx.shell_indices` if it exists (but shell_indices is likely device-agnostic; verify).
7. **Do NOT modify `hkl_grid_modified` construction**: The `torch.where` out-of-place fix (lines 2473-2477) is correct; only fix the HKL grid SOURCE.
8. **Test both detectors**: Small detector (ROI mode, CUDA) and full detector (panel mode, CPU fallback) have different code paths; both must PASS.
9. **Capture telemetry**: Verify `telemetry['stage_b']['status']='ok'` and Bragg output is non-zero (check `bragg_full.min()`, `bragg_full.max()`, `bragg_full.mean()`).
10. **Environment stability**: Assume frozen per POLICY-001; no new installs, only code fix.

## If Blocked

**Scenario A: Full detector test still FAILS with zero Bragg**
- Action: Add diagnostic to print `stage_b_eval_stage_a_ctx.hkl_grid.device`, `hkl_grid_local.device`, `hkl_grid_modified.device` before line 2503
- Verify all are `device('cpu')` and have matching shapes
- Check if `shell_modifiers` are applied correctly (log modifier values)
- Log decision in `blocker.md` with diagnostic output → Galph reviews next loop

**Scenario B: Compilation error or AttributeError**
- Action: Verify `stage_b_eval_stage_a_ctx` is accessible in closure scope (check if it's in closure parameters—it should be at line 2323)
- Check `StageAContext` dataclass has `hkl_grid` attribute (it should, defined at line 657 in `_build_stage_a_context`)
- Fix imports or attribute access, rerun compilation check

**Scenario C: Small detector regression (FAIL)**
- Action: Check if small detector uses CPU fallback path (it shouldn't—small detector should use ROI mode on CUDA)
- Verify `use_stage_b_cpu_fallback` condition excludes ROI mode: `not use_stage_a_roi_mode` (line 2151)
- If regression is real: revert fix, log blocker → Galph reviews

**Scenario D: Tests PASS but Bragg output looks suspicious** (e.g., mean=0.0001, max=0.001)
- Action: Compare with reproducer Bragg stats (mean=0.0027, max=0.086)
- Check if shell modifiers are being applied (softplus transform at line 2455)
- Verify HKL hit rate is >90% (not 0% like loop i=218)
- Log metrics → Galph assesses if acceptable

## Findings Applied

- **GRADIENT-003** (CPU Fallback Path Zero Bragg Output): Root cause identified (HKL grid device routing bug), fix targets line 2464, reproducer evidence confirms nanobrag_torch works correctly on CPU.
- **POLICY-001** (Environment Freeze): No package installs, only dbex source code fix.
- **GRADIENT-002** (In-Place HKL Fix): Out-of-place `torch.where` (lines 2473-2477) is correct; do not modify.
- **PERF-WARM-011/012** (CPU Fallback Context): CPU `stage_b_eval_stage_a_ctx` built at lines 2234-2246 has CPU-native HKL grid; use it directly.
- **CONFORMANCE-001** (Environment Flags): Use `KMP_DUPLICATE_LIB_OK=TRUE` for Intel MKL compatibility.
- **RUNTIME-001** (Test Environment): Use `NANOBRAGG_DISABLE_COMPILE=1` to avoid torch.compile on CPU.
- **TESTING-003** (Collection Verification): Run pytest with `-xvs` for verbose output and immediate failure reporting.

## Pointers

- **Spec/Arch:** `docs/spec-db-runtime.md:34-39` (CPU/CUDA parity requirement), `docs/pytorch_runtime_checklist.md` (device neutrality)
- **Implementation plan:** `plans/active/ARCH-REFINE-FLOW-001/implementation.md:310-320` (Phase C2.4 scope)
- **Reproducer evidence:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/phase_c2_3_decision.md` (Path A: dbex bug confirmed)
- **Parameter parity evidence:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120000Z/crystal_config_comparison.txt` (100% match CUDA vs CPU)
- **Root cause analysis:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/phase_c2_3_decision.md:39-59` (HKL grid device mismatch hypotheses)
- **Test registry:** `docs/TESTING_GUIDE.md:§2` (test_stage_b_shell_modifiers selector), `docs/development/TEST_SUITE_INDEX.md`
- **Code locations:**
  - `dbex/nanobrag_refinement.py:2464` — HKL grid device routing bug (TARGET for fix)
  - `dbex/nanobrag_refinement.py:2234-2246` — CPU context builder (CPU-native HKL grid source)
  - `dbex/nanobrag_refinement.py:2473-2477` — Out-of-place HKL grid shell modifier (correct, do not modify)
  - `dbex/nanobrag_refinement.py:490-664` — `_build_stage_a_context` (line 547: HKL grid device transfer, line 657: context storage)

## Next Up (if Path A)

**Phase C validation (C3-C5) — next loop:**
- C3: Telemetry completeness validation (stage_type="B", mode="shell_modifiers", frozen Stage A params)
- C4: Smoke tests (small+full detectors) with telemetry structure checks
- C5: DB-AT selectors (DB-AT-024 mapping parity)

**Estimated:** 1 loop for full Phase C validation suite (all 3 tasks bundled per galph planning pattern)

## Doc Sync Plan

**Conditional:** Only if tests are added/renamed this loop (not expected—fix-only loop).

If new tests added:
1. Run `pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
2. Archive collection log to artifacts directory
3. Update `docs/TESTING_GUIDE.md:§2` with any new selectors
4. Update `docs/development/TEST_SUITE_INDEX.md` with test metadata

**Expected:** No doc sync needed (fix-only loop, no new tests).

## Mapped Tests Guardrail

**Active selectors:**
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (full detector, CPU fallback path)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (small detector, regression guard)

**Verification:**
```bash
pytest --collect-only -q tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```
Expected: 1 test collected (parameterized by detector size via env var, not pytest param)

**Hard Gate:** If test collects 0, DO NOT proceed. Check test name spelling or file path.
