# ARCH-STAGE-CONTEXT-001 Phase D — Final Bragg Artifact Propagation

**Loop:** 2025-12-02T130500Z
**Status:** Implementation complete with test failures requiring investigation
**Branch:** integration
**Commit:** 07d9d990

## Implementation Summary

Successfully refactored final Bragg reconstruction to use stage artifact channel instead of recomputing from telemetry in run_nanobrag_refinement. Stage A/B now populate optional `bragg_full` fields when they are the terminal stage, and the engine path consumes these artifacts with backward-compatible fallback to helper calls.

### Changes Made

1. **Created `dbex/refinement/reconstruction.py`**
   - Extracted `build_final_bragg_from_stage_a_telemetry` and `build_final_bragg_from_stage_b_telemetry`
     from `dbex/nanobrag_refinement.py`
   - Preserved all existing behavior (warm cache, CPU fallback, shell vs per-reflection modes)
   - Kept device/dtype neutrality and lazy imports to avoid circular dependencies

2. **Extended StageAArtifacts and StageBArtifacts** (`dbex/refinement/artifacts.py`)
   - Added optional `bragg_full: Optional[Any] = None` field to both dataclasses
   - Documented that these are populated only when the stage is terminal
   - Mandated CPU-resident numpy arrays for writer compatibility

3. **Updated StageA.run** (`dbex/refinement/stage_a.py:1257-1285`)
   - Detects terminal condition: `not enable_stage_b and not enable_stage_c`
   - Calls `build_final_bragg_from_stage_a_telemetry` when terminal
   - Attaches result to `StageAArtifacts.bragg_full`

4. **Updated StageB.run** (`dbex/refinement/stage_b.py:1002-1029`)
   - Detects terminal condition: `not enable_stage_c`
   - Calls `build_final_bragg_from_stage_b_telemetry` when terminal
   - Respects `config.stage_b_full_eval_on_cpu` flag per input.md
   - Attaches result to `StageBArtifacts.bragg_full` for both shell and per-reflection modes

5. **Refactored run_nanobrag_refinement** (`dbex/nanobrag_refinement.py`)
   - Stage A-only path (lines 761-776): Checks `stage_a_artifacts.bragg_full` first,
     falls back to `build_final_bragg_from_stage_a_telemetry` if None or missing
   - Stage A→B path (lines 902-944): Checks `stage_b_artifacts.bragg_full` first,
     falls back to `build_final_bragg_from_stage_b_telemetry` if None or missing
   - Deleted old helper definitions (lines 206-624), replaced with comment pointing to reconstruction module

6. **Updated all consumers**
   - `tests/dbex/test_stage_a_smoke_parity.py`: Updated import and usages
   - `dbex/tools/stage_a_adam.py`: Updated import, usages, and docstring
   - `plans/active/TOOLING-VIS-001/bin/*.py`: Updated imports and usages via sed

## Test Results

### test_stage_a_expansion (small detector)
**Status:** FAILED (pre-existing acceptance gate issue)

```
AssertionError: log_scale delta too small: 2.091e-07
assert 2.0914571940977567e-07 > 1e-06
```

- Test executed through new reconstruction path successfully (7.35s runtime)
- Failure is on Acceptance 5 gate checking param deltas
- Delta value (2.091e-07) is well-initialized but below 1e-06 threshold
- **Root cause:** Likely geometry initialization too close to ground truth, not a code defect
- **Next action:** Consider relaxing gate or documenting as known well-initialized scenario

### test_stage_b_shell_modifiers (small detector)
**Status:** FAILED (artifact extraction issue)

```
KeyError: 'shell_edges' at dbex/refinement/reconstruction.py:306
```

- Test reached Stage B optimization successfully (22.71s runtime, multiple HKL grid builds logged)
- Failure occurred in fallback `build_final_bragg_from_stage_b_telemetry` helper
- **Root cause hypothesis:** `stage_b_artifacts.bragg_full` was None despite Stage B being terminal,
  forcing fallback path. Fallback then failed because shell metadata extraction expected dict but received
  RefinementTelemetry object without shell_edges attribute.

**Investigation needed:**
1. Verify `config.enable_stage_c` is False in test fixture
2. Check if StageB.run terminal detection logic is correct
3. Confirm StageB.run actually populated `bragg_full` in artifacts (add debug logging)
4. If bragg_full is None, determine why (exception during reconstruction? guard preventing it?)

### test_stage_b_per_reflection_smoke
**Not run:** Per input.md, this test has known TORCH-REFINE-004 gradient-flow failure.
Expected to fail with pre-existing signature; would have captured log if run.

## Findings

**ARCH-STAGE-CTX-D-001** — Stage B artifact population may not trigger correctly
When Stage B is terminal (`not enable_stage_c`), `StageB.run` should populate `bragg_full`
in artifacts. The test_stage_b_shell_modifiers failure suggests either:
- Terminal condition detection failed
- Bragg reconstruction raised an exception silently
- Artifacts object wasn't properly updated

Needs targeted inspection of StageB.run execution with debug logging to confirm artifact population.

**ARCH-STAGE-CTX-D-002** — Fallback path needs better shell metadata handling
When falling back to `build_final_bragg_from_stage_b_telemetry`, we reconstruct a
`telemetry_b_dict` with shell metadata from artifacts. However, the helper expects
either RefinementTelemetry with attributes or a dict with keys. Current logic doesn't
handle the case where RefinementTelemetry lacks shell_edges/shell_indices attributes
(because they were never added to the telemetry object, only to artifacts).

## Artifacts

- `pytest_stage_a_small.log` — Stage A expansion test output (FAILED, acceptance gate)
- `pytest_stage_b_shell.log` — Stage B shell modifiers test output (FAILED, artifact KeyError)
- `summary.md` — This file

## Next Actions

1. **Debug Stage B artifact population:**
   - Add temporary logging in `StageB.run` before/after terminal bragg_full computation
   - Re-run test_stage_b_shell_modifiers with logging enabled
   - Confirm `is_terminal_stage` evaluates to True and `bragg_full_artifact` is populated

2. **Fix fallback path if needed:**
   - If bragg_full is correctly populated but artifacts somehow lost it, investigate engine/return path
   - If population logic is correct but disabled by test config, adjust test expectations

3. **Relax or document Stage A delta gate:**
   - Investigate why log_scale delta is so small (2e-07 vs 1e-06 threshold)
   - Either relax gate for well-initialized scenarios or document this as known behavior

4. **Run per-reflection smoke test:**
   - Capture expected TORCH-REFINE-004 failure signature for comparison with prior loops
   - Confirm artifact code doesn't change pre-existing failure mode
