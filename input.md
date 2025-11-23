# Input for Ralph (Loop i=213)

## Summary
Complete CPU fallback fix for ARCH-REFINE-FLOW-001 Phase C2.2: populate engine_inputs with use_stage_b_cpu_fallback + CPU-cloned Stage A context.

## Mode
None (targeted bugfix - complete CPU fallback implementation)

## Focus
ARCH-REFINE-FLOW-001 Phase C2.2 — Protocol-based Refinement Engine (Complete CPU fallback fix with engine_inputs plumbing)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` with `DBEX_SMOKE_DETECTOR_SIZE=full` (MUST PASS after complete fix)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` with `DBEX_SMOKE_DETECTOR_SIZE=small` (regression guard)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/`

---

## Do Now

### Context (Refined Root Cause Analysis)

**Ralph's loop i=212 partial fix:**
- Fixed final Bragg reconstruction device (line 3110: `device=final_device`)
- **Result**: OOM moved from crystal.py:356 → physics.py:79, but still FAILS
- **Why**: Final Bragg device doesn't affect Stage B closure execution

**Root Cause (HIGH confidence ~98%)**:
- Engine delegation path (lines 3036-3050) builds `engine_inputs` dict but **does NOT populate** `use_stage_b_cpu_fallback` or `stage_b_eval_stage_a_ctx` keys
- StageB.run() line 249 expects `use_stage_b_cpu_fallback` in inputs → param_values
- When missing, StageB defaults to CUDA execution → exhausts GPU memory during closure

**Complete Fix Location:**
- Insert ~30 lines at line 3047 (AFTER `engine_inputs = {...}` block, BEFORE `engine = RefinementEngine(...)`)
- Must match inline path pattern (lines 2171-2205): compute use_stage_a_roi_mode, compute use_stage_b_cpu_fallback, clone Stage A context to CPU if needed

### Tasks (6 steps)

1. **Review loop i=212 evidence**:
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/summary.md` (Ralph's partial fix)
   - Review `pytest_stage_b_full_after_fix2.log` (FAILED at physics.py:79 - CUDA OOM during closure execution)
   - Confirm root cause: engine_inputs missing CPU fallback keys

2. **Implement complete CPU fallback logic in engine delegation path**:
   - **Location**: `dbex/nanobrag_refinement.py` line 3047 (AFTER `engine_inputs = {...}` ending line 3045, BEFORE `engine = RefinementEngine(...)` line 3050)
   - **Insert ~30 lines** following reference pattern (inline path lines 2171-2205):

   ```python
   # PERF-WARM-011 + PERF-WARM-012: CPU fallback logic for engine delegation path
   # Must match inline path (lines 2171-2205) to avoid CUDA OOM on full detector

   # Step 1: Compute use_stage_a_roi_mode (matching inline path lines 2171-2173)
   panel_slices = inputs.panel_slices
   canonical_roi_count = len(panel_slices)
   use_stage_a_roi_mode = bool(
       config.enable_stage_a_roi_mode
       and canonical_roi_count > 0
       and (config.enable_stage_a_warm_cache or config.allow_cold_stage_a_roi_mode)
   )

   # Step 2: Compute use_stage_b_cpu_fallback (matching inline path lines 2178-2182)
   use_stage_b_cpu_fallback = (
       config.stage_b_full_eval_on_cpu
       and str(device).startswith("cuda")
       and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
   )

   # Step 3: Clone Stage A context to CPU if fallback active (matching inline path lines 2186-2205)
   stage_b_eval_stage_a_ctx = None
   if use_stage_b_cpu_fallback and config.enable_stage_a_warm_cache:
       # Build fresh Stage A context on CPU device
       # NOTE: We clone BEFORE engine.run() because StageB needs it during execution
       cpu_device = torch.device("cpu")
       stage_b_eval_stage_a_ctx = _build_stage_a_context(
           detector=detector,
           beam=beam,
           crystal=crystal,
           trusted_mask=inputs.trusted_mask,
           hkl_grid=hkl_grid,
           hkl_metadata=hkl_metadata,
           enable_hkl_interpolation=config.enable_hkl_interpolation,
           device=cpu_device,
           dtype=dtype,
           panel_slices=panel_slices,
           enable_roi_mode=False,  # CPU fallback is panel-mode only
       )

   # Step 4: Add CPU fallback keys to engine_inputs (CRITICAL - this is what was missing!)
   engine_inputs['use_stage_b_cpu_fallback'] = use_stage_b_cpu_fallback
   engine_inputs['stage_b_eval_stage_a_ctx'] = stage_b_eval_stage_a_ctx
   ```

   - **CRITICAL**: The two new keys (`use_stage_b_cpu_fallback`, `stage_b_eval_stage_a_ctx`) will be consumed by StageB.run() and passed to `_build_stage_b_params` which switches device to CPU
   - **Keep Ralph's loop i=212 fix**: Leave final Bragg device fix at line 3110 (it's correct, just incomplete)

3. **Rerun Stage B full detector smoke test**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_stage_b_full_complete_fix.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_stage_b_full_complete_fix.log
   ```
   - **MUST PASS** - this is the decisive validation
   - Expected runtime: ~60-90s (CPU execution slower than GPU, full detector is 92 ROIs)
   - Expected output: Test PASSES without CUDA OOM

4. **Rerun regression guard (Stage B small detector)**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_stage_b_small_regression.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_stage_b_small_regression.log
   ```
   - **MUST PASS** - confirms complete fix doesn't regress small detector path

5. **Decision synthesis per 4-path template**:
   - Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/decision.md` with:
     ```markdown
     # Phase C2.2 Complete CPU Fallback Fix Decision

     ## Test Results
     - Stage B full detector: [PASS/FAIL] (exit code X, runtime Ys)
     - Stage B small detector regression: [PASS/FAIL] (exit code X, runtime Ys)

     ## Decision Path
     [Path A|B|C|D - see decision tree below]

     ## Next Actions
     - Path A (both PASS): Run DB-AT-024 mapping parity → Phase C validation complete
     - Path B (full FAIL): Debug device propagation inside StageB/helpers → escalate to shared layer
     - Path C (small FAIL): Debug regression from CPU fallback conditional logic
     - Path D (both FAIL): Escalate to shared implementation bug in _build_stage_b_params
     ```

6. **Commit and push**:
   ```bash
   git add -A
   git commit -m "ARCH-REFINE-FLOW-001 Phase C2.2: Complete CPU fallback fix (engine_inputs plumbing) — tests: [PASS/FAIL verdict]"
   git push
   ```
   - If both tests PASS: Continue to DB-AT-024 validation (deferred from loop i=211)
   - If any test FAILS: Document blocker in decision.md, commit evidence, return to Galph

---

## How-To Map

### Environment
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Code Fix Location
- **File**: `dbex/nanobrag_refinement.py`
- **Insert at line 3047** (AFTER `engine_inputs = {...}` block ending line 3045, BEFORE `engine = RefinementEngine(...)` line 3050)
- **Reference pattern**: Lines 2171-2205 (inline path CPU fallback + context cloning)
- **Key insight**: Must populate `engine_inputs['use_stage_b_cpu_fallback']` and `engine_inputs['stage_b_eval_stage_a_ctx']` so StageB.run() can consume them

### Test Commands
```bash
# Stage B full detector (primary validation - MUST PASS)
DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_stage_b_full_complete_fix.log 2>&1

# Stage B small detector (regression guard - MUST PASS)
DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_stage_b_small_regression.log 2>&1
```

### Decision Tree
```
┌─ Both tests PASS (full detector + small detector regression)?
│  ├─ YES → Path A: Complete CPU fallback SUCCESS → run DB-AT-024, Phase C validation complete
│  └─ NO  → Check which failed:
│     ├─ Full FAIL, small PASS → Path B: Debug device propagation in StageB.run() or _build_stage_b_params
│     ├─ Full PASS, small FAIL → Path C: Regression from CPU fallback conditional (review branching logic)
│     └─ Both FAIL → Path D: Escalate to shared implementation bug (device neutrality violation)
```

---

## Pitfalls To Avoid

1. **Engine_inputs plumbing is CRITICAL**: StageB.run() cannot switch to CPU without `use_stage_b_cpu_fallback` key in inputs
2. **Clone context BEFORE engine.run()**: StageB needs CPU context during execution, not after
3. **Match inline path exactly**: use_stage_a_roi_mode computation must be identical (lines 2171-2173)
4. **Device/dtype neutrality**: CPU context must use `torch.device("cpu")`, not string "cpu"
5. **Protected Assets**: Do NOT modify inline path logic (lines 2171-2205) - it's the reference implementation
6. **Keep partial fix**: Do NOT revert Ralph's loop i=212 final Bragg device fix (line 3110) - it's correct
7. **Context timing**: `_build_stage_a_context()` call happens BEFORE `engine.run()`, not inside StageB.run()
8. **No new helpers**: Insert code directly at line 3047, do not extract new helper functions

---

## If Blocked

If any test FAILS after complete CPU fallback fix:

1. **Capture exact error**: Save full pytest log with traceback
2. **Document in decision.md**:
   - Which test failed (full detector? small detector? both?)
   - Error signature (CUDA OOM still? Different error? Line number?)
   - Device propagation trace (check if StageB.run() received correct inputs)
3. **Debug device propagation**:
   - Add print statement at dbex/refinement/stage_b.py:249 to verify `use_stage_b_cpu_fallback` value
   - Check if `_build_stage_b_params` receives correct device parameter
   - Verify closure execution uses CPU device (not CUDA)
4. **Update docs/fix_plan.md**: Mark Phase C2.2 `blocked`, document specific device propagation failure
5. **Commit evidence**: `git add plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/ && git commit -m "ARCH-REFINE-FLOW-001 Phase C2.2: Complete CPU fallback BLOCKED - <error signature>"`
6. **Return control to Galph**: Push commit, let Galph escalate to shared implementation layer if needed

---

## Findings Applied

**Mandatory cross-references** (from `docs/findings.md`):

- **PERF-WARM-011**: Stage B full-panel runs on canonical detector MUST fall back to CPU to avoid GPU OOM when `config.stage_b_full_eval_on_cpu=True` (default). Inline path implements at lines 2178-2182; engine delegation path MUST replicate via engine_inputs plumbing.
- **PERF-WARM-012**: When CPU fallback active, clone Stage A warm cache to CPU device so Stage B panel-mode closures reuse cached detectors/HKL/masks (maintaining `cache_mode="warm"`). Inline path implements at lines 2186-2205; engine delegation path MUST replicate by populating `engine_inputs['stage_b_eval_stage_a_ctx']` with CPU-cloned context.
- **REFINE-008**: Stage B shell modifier refinement improvement gate calibrated to ≥3% masked-MSE improvement. Full detector test MUST meet this gate after complete CPU fallback fix.
- **PHYSICS-LOSS-001**: Variance-weighted loss function with sigma_floor guard. Stage B telemetry MUST include chi-squared and variance stats.
- **PHYSICS-LOSS-002**: Sigma floor guard prevents division by zero. Ensure telemetry shows `sigma_floor` applied.

**No relevant findings for**: engine_inputs plumbing patterns (this is a first implementation for engine delegation path).

---

## Pointers

### Spec/Arch
- `docs/spec-db-workflow.md:7` — Refinement Protocol Architecture (Stage A/B/C contracts, engine orchestration)
- `docs/spec-db-runtime.md:18-28` — PyTorch device/dtype neutrality, warm cache reuse

### Fix Plan
- `docs/fix_plan.md:[ARCH-REFINE-FLOW-001]` — Initiative definition, exit criteria, Phase C checklist

### Implementation Plan
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:179-211` — Phase C tasks (C3 telemetry, C4 validation, C5 DB-AT selectors)

### Testing Guide
- `docs/TESTING_GUIDE.md:135-145` — Stage B smoke test selectors, environment flags, acceptance criteria

### Galph's Evidence
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/` — This loop's artifacts directory (create decision.md here)

### Ralph's Loop i=212 Evidence
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/summary.md` — Partial fix (final Bragg device)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_full_after_fix2.log` — OOM at physics.py:79

### Reference Implementation (AUTHORITATIVE)
- `dbex/nanobrag_refinement.py:2171-2205` — Inline path CPU fallback + context cloning (EXACT pattern to replicate)
- `dbex/nanobrag_refinement.py:3036-3050` — Engine delegation path (MISSING CPU fallback, needs fix at line 3047)
- `dbex/refinement/stage_b.py:249` — StageB.run() expects `use_stage_b_cpu_fallback` in param_values

---

## Next Up (If both tests PASS)

Continue Phase C validation with DB-AT-024 mapping parity test (deferred from loop i=211):

1. **Run DB-AT-024 mapping parity**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_db_at_024_mapping_parity.py::test_mapping_parity \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_db_at_024.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/pytest_db_at_024.log
   ```
   - Expected: PASS (median correlation ≥0.2, localization ≥90%)
   - Confirms Stage B extraction + CPU fallback didn't regress mapping forward model

2. **Update docs/fix_plan.md Attempts History**:
   - Add new entry documenting Phase C2.2 complete fix, all 3 tests PASSED
   - Mark Phase C COMPLETE (exit criteria C3/C4/C5 met)

3. **Write Turn Summary** in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/summary.md`

4. **Commit**: `ARCH-REFINE-FLOW-001 Phase C2.2 COMPLETE: CPU fallback + DB-AT-024 PASSED`

---

## Doc Sync Plan
**NOT APPLICABLE** - No new tests added this loop, only bugfix validation of existing tests.

---

## Normative Math/Physics
**NOT APPLICABLE** - This is a device placement / engine_inputs plumbing fix, not a physics/math change.

See `docs/spec-db-core.md` §Variance Model for normative variance-weighted loss equations (already implemented in PHYSICS-LOSS-001/002).
