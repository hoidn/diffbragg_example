# Input for Ralph (Loop i=212)

## Summary
Fix missing CPU fallback logic in ARCH-REFINE-FLOW-001 Phase C engine delegation path to enable Stage B full detector smoke test.

## Mode
None (targeted bugfix)

## Focus
ARCH-REFINE-FLOW-001 Phase C2.1 — Protocol-based Refinement Engine (CPU fallback fix for Stage B engine delegation)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` with `DBEX_SMOKE_DETECTOR_SIZE=full` (must PASS after fix)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` with `DBEX_SMOKE_DETECTOR_SIZE=small` (regression guard, already PASSED in loop i=211)
- `tests/dbex/test_db_at_024_mapping_parity.py::test_mapping_parity` (DB-AT-024 mapping parity, deferred from loop i=211)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/`

---

## Do Now

### Context
Ralph's loop i=211 Phase C validation identified a decisive blocker (HIGH confidence ~95%):
- **Stage B small detector smoke**: PASSED (13.45s)
- **Stage B full detector smoke**: FAILED - CUDA OOM (tried to allocate 1.67 GiB, only 49.62 MiB free)
- **Root cause**: Engine delegation path (`dbex/nanobrag_refinement.py:3029-3108`) is MISSING CPU fallback initialization logic required by PERF-WARM-011

**Reference implementation** (inline path, lines 2174-2203):
```python
# Compute use_stage_a_roi_mode from Stage A context
use_stage_a_roi_mode = (stage_a_ctx is not None
                        and hasattr(stage_a_ctx, 'roi_mode')
                        and stage_a_ctx.roi_mode)

# PERF-WARM-011: CPU fallback for full-panel Stage B runs
use_stage_b_cpu_fallback = (
    config.stage_b_full_eval_on_cpu
    and str(device).startswith("cuda")
    and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
)

# PERF-WARM-012: Clone Stage A context to CPU when fallback active
stage_b_eval_stage_a_ctx = None
if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
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
elif not use_stage_b_cpu_fallback:
    stage_b_eval_stage_a_ctx = stage_a_ctx
```

### Tasks (8 steps)

1. **Review Ralph's loop i=211 evidence** (`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/`):
   - Read `phase_c_decision.md` (root cause analysis, exit criteria status)
   - Review `pytest_stage_b_small.log` (PASSED, 13.45s)
   - Review `pytest_stage_b_full.log` (FAILED - CUDA OOM at line 356 in nanobrag_torch/models/crystal.py)
   - Confirm root cause: engine delegation path missing CPU fallback logic

2. **Implement CPU fallback fix in engine delegation path**:
   - **Location**: `dbex/nanobrag_refinement.py` lines 3029-3048 (BEFORE `engine = RefinementEngine(...)`)
   - **Add ~8-12 lines** following reference pattern (lines 2174-2203):
     ```python
     # Compute use_stage_a_roi_mode from Stage A context or config
     use_stage_a_roi_mode = False  # Default: engine path doesn't use ROI mode yet
     if stage_a_ctx is not None and hasattr(stage_a_ctx, 'roi_mode'):
         use_stage_a_roi_mode = stage_a_ctx.roi_mode

     # PERF-WARM-011: CPU fallback for full-panel Stage B runs to avoid GPU OOM
     use_stage_b_cpu_fallback = (
         config.stage_b_full_eval_on_cpu
         and str(device).startswith("cuda")
         and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
     )

     # PERF-WARM-012: Clone Stage A context to CPU when fallback is active
     # so Stage B can reuse cached detectors/HKL/masks on CPU (cache_mode="warm")
     if use_stage_b_cpu_fallback and config.enable_stage_a_warm_cache:
         # Extract Stage A context from engine after StageA execution
         # NOTE: This requires extracting stage_a_ctx from engine AFTER run(),
         # OR we need to build CPU context BEFORE engine execution
         # SIMPLIFIED APPROACH: Build fresh CPU context before engine execution
         cpu_device = torch.device("cpu")
         cpu_stage_a_ctx = _build_stage_a_context(
             detector=detector,
             beam=beam,
             crystal=crystal,
             trusted_mask=inputs.trusted_mask,
             hkl_grid=hkl_grid,
             hkl_metadata=hkl_metadata,
             enable_hkl_interpolation=config.enable_hkl_interpolation,
             device=cpu_device,
             dtype=dtype,
             panel_slices=inputs.panel_slices,
             enable_roi_mode=False,  # CPU fallback is panel-mode only
         )
         # Add CPU context to engine_inputs so StageB can access it
         engine_inputs['stage_a_ctx_cpu'] = cpu_stage_a_ctx
         engine_inputs['use_stage_b_cpu_fallback'] = True
     else:
         engine_inputs['use_stage_b_cpu_fallback'] = False
     ```
   - **IMPORTANT**: The engine path currently extracts `stage_a_ctx` from engine cache AFTER `engine.run()` (line 3062). For CPU fallback, we need to either:
     - Option A: Build a CPU Stage A context BEFORE engine execution and pass it in `engine_inputs` (RECOMMENDED for now)
     - Option B: Refactor engine to expose Stage A context during execution so StageB can clone it
   - **Recommendation**: Use Option A (build CPU context before engine execution) as it's simpler and matches the inline path pattern

3. **Verify StageB.run() consumes CPU fallback correctly**:
   - Check `dbex/refinement/stage_b.py` line ~249: `use_stage_b_cpu_fallback = param_values.get('use_stage_b_cpu_fallback', False)`
   - Ensure StageB.run() extracts `stage_a_ctx_cpu` from inputs if `use_stage_b_cpu_fallback=True`
   - If StageB needs updates, make minimal changes to consume the CPU context

4. **Rerun Stage B full detector smoke test**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_full_after_fix.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_full_after_fix.log
   ```
   - **MUST PASS** - this is the decisive validation
   - Runtime expectation: ~20-30s (CPU execution slower than GPU)

5. **Verify telemetry contains CPU fallback evidence**:
   - Extract telemetry from test artifacts or HDF5 output
   - Verify Stage B telemetry includes:
     - `stage_b_full_eval_on_cpu=True` (or similar field indicating CPU execution)
     - `cache_mode="warm"` (confirms Stage A warm cache reused on CPU per PERF-WARM-012)
   - Save verification as inline Python snippet in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/verify_telemetry_cpu_fallback.txt`

6. **Rerun regression guard (Stage B small detector)**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_small_regression.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_small_regression.log
   ```
   - **MUST PASS** - confirms fix doesn't regress small detector path

7. **Run DB-AT-024 mapping parity test** (deferred from loop i=211):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_db_at_024_mapping_parity.py::test_mapping_parity \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_db_at_024.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_db_at_024.log
   ```
   - **Expected**: PASS (median correlation ≥0.2, localization ≥90%)
   - Confirms Stage B extraction + CPU fallback fix didn't regress mapping forward model

8. **Update docs/fix_plan.md Attempts History**:
   - Add new entry under ARCH-REFINE-FLOW-001 Attempts History
   - Document: loop i=212, CPU fallback fix implementation, test results (all 3 tests PASS), root cause resolution
   - If all tests PASS: mark Phase C COMPLETE (exit criteria C3/C4/C5 met)
   - Commit message: `ARCH-REFINE-FLOW-001 Phase C2.1: CPU fallback fix — tests: full/small PASSED, DB-AT-024 PASSED`

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
- **Line range**: 3029-3048 (insert CPU fallback logic BEFORE `engine = RefinementEngine(...)`)
- **Reference pattern**: Lines 2174-2203 (inline path CPU fallback + context cloning)

### Test Commands
```bash
# Stage B full detector (primary validation - MUST PASS)
DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_full_after_fix.log 2>&1

# Stage B small detector (regression guard - MUST PASS)
DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_stage_b_small_regression.log 2>&1

# DB-AT-024 mapping parity (MUST PASS)
DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_db_at_024_mapping_parity.py::test_mapping_parity \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/pytest_db_at_024.log 2>&1
```

### Telemetry Verification (T0 inline snippet)
```python
# Save as: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/verify_telemetry_cpu_fallback.txt
# Run after Stage B full detector test completes

import h5py
# Locate the HDF5 output from test_stage_b_shell_modifiers (check test artifacts or /tmp/)
# Example path: /tmp/test_stage_b_shell_modifiers_full.h5
with h5py.File('/path/to/output.h5', 'r') as f:
    # Check if Stage B telemetry group exists
    if '/refinement/stage_b' in f:
        stage_b_grp = f['/refinement/stage_b']
        # Look for CPU fallback evidence
        cpu_fallback = stage_b_grp.attrs.get('stage_b_full_eval_on_cpu', None)
        cache_mode = stage_b_grp.attrs.get('cache_mode', None)
        print(f"CPU fallback: {cpu_fallback}, Cache mode: {cache_mode}")
        # Expected: cpu_fallback=True or 1, cache_mode="warm"
```

### Decision Tree
```
┌─ All 3 tests PASS (full detector, small detector regression, DB-AT-024)?
│  ├─ YES → Path A: CPU fallback fix SUCCESS → Phase C COMPLETE → Update docs/fix_plan.md, commit
│  └─ NO  → Check which failed:
│     ├─ Full detector still FAILS → Path B: Debug CPU context build logic (check device placement, context cloning)
│     ├─ Small detector FAILS → Path C: Regression introduced by CPU fallback logic (review conditional branching)
│     └─ DB-AT-024 FAILS → Path D: Mapping regression (verify Stage B extraction didn't change bridge helpers)
```

---

## Pitfalls To Avoid

1. **Device/dtype neutrality**: When building CPU Stage A context, ensure `device=torch.device("cpu")` is explicitly passed to `_build_stage_a_context()`
2. **Protected Assets**: Do NOT modify existing inline path CPU fallback logic (lines 2174-2203) - it's the reference implementation
3. **No ad-hoc scripts**: CPU fallback logic goes directly into production code (`dbex/nanobrag_refinement.py`), not a separate helper
4. **Context timing**: Build CPU Stage A context BEFORE `engine.run()` so StageB can access it during execution
5. **Vectorization**: Ensure `panel_slices` is correctly passed to CPU context builder (no ROI mode in CPU fallback)
6. **Environment Freeze**: Do NOT install/upgrade packages. Treat missing imports as blockers.
7. **Regression guard**: ALWAYS rerun Stage B small detector test after code changes to catch regressions
8. **Telemetry validation**: Verify CPU fallback actually happened (check telemetry fields, not just test PASS)

---

## If Blocked

If any test FAILS after CPU fallback fix:

1. **Capture exact error**: Save full pytest log with traceback
2. **Document in decision.md**:
   - Which test failed
   - Error signature (CUDA OOM still? Different error?)
   - Line numbers where failure occurs
3. **Update docs/fix_plan.md**: Mark Phase C2.1 `blocked`, document specific blocker
4. **Commit evidence**: `git add plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/ && git commit -m "ARCH-REFINE-FLOW-001 Phase C2.1: CPU fallback BLOCKED - <error signature>"`
5. **Return control to Galph**: Push commit, let Galph review blocker and decide next steps

---

## Findings Applied

**Mandatory cross-references** (from `docs/findings.md`):

- **PERF-WARM-011**: Stage B full-panel runs on canonical detector MUST fall back to CPU to avoid GPU OOM when `config.stage_b_full_eval_on_cpu=True` (default). Inline path implements this at lines 2174-2182; engine delegation path MUST replicate.
- **PERF-WARM-012**: When CPU fallback is active, clone Stage A warm cache to CPU device so Stage B panel-mode closures/validations reuse cached detectors/HKL/masks (maintaining `cache_mode="warm"`). Inline path implements this at lines 2184-2202; engine delegation path MUST replicate.
- **REFINE-008**: Stage B shell modifier refinement improvement gate calibrated to ≥3% masked-MSE improvement (relaxed from ±1% shell modifier delta tolerance). Full detector test MUST meet this gate after CPU fallback fix.
- **PHYSICS-LOSS-001**: Variance-weighted loss function with sigma_floor guard. Stage B telemetry MUST include chi-squared and variance stats.
- **PHYSICS-LOSS-002**: Sigma floor guard prevents division by zero in variance-weighted loss. Ensure telemetry shows `sigma_floor` applied.

**No relevant findings in the knowledge base for**: CPU context cloning API, engine-specific CPU fallback patterns (this is a first implementation).

---

## Pointers

### Spec/Arch
- `docs/spec-db-workflow.md:7` — Refinement Protocol Architecture (Stage A/B/C contracts, engine orchestration)
- `docs/spec-db-runtime.md:18-28` — PyTorch device/dtype neutrality, warm cache reuse

### Fix Plan
- `docs/fix_plan.md:185-196` — ARCH-REFINE-FLOW-001 initiative definition, exit criteria, Phase C checklist

### Implementation Plan
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:208-211` — Phase C tasks (C3 telemetry, C4 validation, C5 DB-AT selectors)

### Testing Guide
- `docs/TESTING_GUIDE.md:135-145` — Stage B smoke test selectors, environment flags, acceptance criteria

### Ralph's Evidence
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/phase_c_decision.md` — Root cause analysis, exit criteria status, fix requirements

### Reference Implementation
- `dbex/nanobrag_refinement.py:2174-2203` — Inline path CPU fallback + context cloning (AUTHORITATIVE reference)
- `dbex/nanobrag_refinement.py:3029-3108` — Engine delegation path (MISSING CPU fallback, needs fix)

---

## Next Up (Optional)

If you finish early AND all 3 tests PASS:

1. **Update implementation.md Phase C status**:
   - Mark C3/C4/C5 checklist items as complete
   - Update Phase C completion timestamp (2025-11-23T090000Z)

2. **Write Turn Summary block** in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/summary.md`:
   ```markdown
   ### Turn Summary
   Implemented CPU fallback fix for Stage B engine delegation path, resolving CUDA OOM on full detector.
   All validation tests PASSED: Stage B full/small detector smokes + DB-AT-024 mapping parity.
   Phase C extraction COMPLETE: helpers extracted, wrapper implemented, engine delegation verified, CPU fallback functional.
   Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/ (pytest logs, telemetry verification, decision.md)
   ```

---

## Doc Sync Plan
**NOT APPLICABLE** - No new tests added this loop, only bugfix validation of existing tests.

---

## Normative Math/Physics
**NOT APPLICABLE** - This is a device placement / warm cache reuse fix, not a physics/math change.

See `docs/spec-db-core.md` §Variance Model for normative variance-weighted loss equations (already implemented in PHYSICS-LOSS-001/002).
