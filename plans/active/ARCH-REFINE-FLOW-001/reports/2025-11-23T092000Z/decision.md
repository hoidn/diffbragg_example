# Phase C2.2 Complete CPU Fallback Fix Decision — BLOCKED

## Test Results
- Stage B full detector: **FAIL** (exit code 1, runtime ~118s)
  - Error: `torch.OutOfMemoryError: CUDA out of memory` at `physics.py:79`
  - Same failure signature as loop i=212 (OOM during closure execution)
- Stage B small detector regression: **NOT RUN** (blocked by full detector failure)

## Root Cause Analysis (Updated)

### Initial Hypothesis (From input.md)
Engine delegation path missing `use_stage_b_cpu_fallback` and `stage_b_eval_stage_a_ctx` keys in `engine_inputs` dict → StageB.run() cannot switch to CPU.

### Investigation Result (Loop i=213)
**Hypothesis REJECTED**. The CPU fallback logic already exists in `_build_stage_b_params` (lines 2174-2205) and is called by StageB.run(). However, the test still fails with CUDA OOM, indicating the CPU fallback is NOT activating.

### Verified Facts
1. `_build_stage_b_params` contains CPU fallback logic that computes `use_stage_b_cpu_fallback` based on:
   - `config.stage_b_full_eval_on_cpu` (default: `True` ✓)
   - `str(device).startswith("cuda")` (test uses `device="cuda:0"` ✓)
   - `not use_stage_a_roi_mode` (full detector → panel mode → `use_stage_a_roi_mode=False` ✓)
2. `_build_stage_b_lbfgs_closure` computes `eval_device = torch.device("cpu") if use_stage_b_cpu_fallback else device` (line 2368)
3. StageA.run() returns `stage_a_ctx` in telemetry (line 370 in stage_a.py)
4. RefinementEngine caches and propagates `stage_a_ctx` to StageB (lines 114-115, 120-122 in engine.py)
5. Test STILL fails with CUDA OOM at physics.py:79 (closure execution), same as loop i=212

### Suspected Root Cause (NEW Hypothesis)
The CPU fallback conditions in `_build_stage_b_params` (line 2178-2182) are evaluating to `False` despite all three sub-conditions appearing to be `True`. Possible causes:
1. **Config propagation bug**: `config` parameter passed to `_build_stage_b_params` might have `stage_b_full_eval_on_cpu=False` due to engine/stage configuration handoff issue
2. **Device string mismatch**: `device` parameter might not be a `torch.device` object, causing `str(device).startswith("cuda")` to fail
3. **ROI mode detection bug**: `use_stage_a_roi_mode` might be `True` despite panel mode configuration
4. **Context availability bug**: `stage_a_ctx` might be `None`, causing the clone branch (line 2187) to be skipped

## Decision Path
**Path D** (investigation required) — Need to add telemetry/logging to verify which condition is failing:
1. Instrument `_build_stage_b_params` to log all three CPU fallback conditions
2. Instrument `_build_stage_b_lbfgs_closure` to log `eval_device` value
3. Rerun test with instrumentation to identify which condition fails
4. Fix condition evaluation bug OR escalate to shared implementation layer if bug is in engine/config propagation

## Code Changes (Loop i=213)
All changes reverted — no net production code changes in this loop.

**Attempted Fix (Reverted)**:
- Tried pre-computing CPU fallback in engine delegation path (line 3047-3088)
- Tried overriding device in StageB.run() (line 116-129)
- Reverted both approaches after analysis showed `_build_stage_b_params` already has CPU fallback logic

**Current State**: Code is back to loop i=212 state (Ralph's partial fix: final Bragg device only)

## Next Actions
1. **Add instrumentation**: Insert debug logging in `_build_stage_b_params` and `_build_stage_b_lbfgs_closure` to capture:
   - `config.stage_b_full_eval_on_cpu` value
   - `str(device)` value and type
   - `use_stage_a_roi_mode` value
   - `stage_a_ctx is not None` boolean
   - Final `use_stage_b_cpu_fallback` value
   - `eval_device` value in closure
2. **Rerun test** with instrumentation to identify failing condition
3. **Fix condition bug** based on telemetry
4. **Escalate** if bug is in engine/stage/config architecture (outside `_build_stage_b_params` scope)

## Artifacts
- `pytest_stage_b_full_complete_fix.log` — Failed attempt with engine_inputs plumbing (exit code 1, OOM at physics.py:79)
- `pytest_stage_b_full_final_attempt.log` — Failed attempt with reverted code (exit code 1, same OOM signature)
- `decision.md` — This document

## Blocker
**Phase C2.2 BLOCKED** — CPU fallback logic exists but is not activating. Need diagnostic instrumentation to identify which condition fails.
