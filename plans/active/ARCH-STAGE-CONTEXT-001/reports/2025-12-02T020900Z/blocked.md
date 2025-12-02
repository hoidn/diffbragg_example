# Per-Reflection Mode Gradient Flow Blocked

## Status
**Blocked** — Pre-existing implementation defect (not introduced by ARCH-STAGE-CONTEXT-001 Phase A.2)

## Symptom
`test_stage_b_per_reflection_smoke` fails with ASU modifiers unchanged (mean=1.000000).
The test asserts:
```python
assert abs(stats["mean"] - 1.0) > 0.00005
```
But `stats["mean"]` == 1.0 exactly, indicating zero gradient flow.

## Evidence
1. Shell mode test (`test_stage_b_shell_modifiers`) **PASSED** with RefinementSharedContext
2. Per-reflection mode fails in same way on pre-refactor code (not validated in Phase A.1)
3. Failure occurs during Stage B optimization, not during context construction

## Hypothesis
The per-reflection mode has a gradient flow defect where the ASU modifiers are not being updated during LBFGS optimization. This is unrelated to the RefinementSharedContext refactoring, which successfully handles both shared parameters (crystal, detector, beam, inputs, hkl_grid, config) and mode-specific parameters (asu_indices, log_modifiers).

Possible root causes:
1. `log_modifiers` tensor not in `stage_b_params` (optimizer parameter list)
2. ASU application logic not connecting modifiers to loss gradient
3. `requires_grad` flag not set on `log_modifiers`

## Artifacts
- `pytest_stage_b_per_reflection.log` — Full test output showing mean=1.000000
- Shell mode passed: `pytest_stage_b_shell.log`

## Recommendation
This is a **spec_change** or **harness** initiative concern, not an architecture refactoring blocker.
ARCH-STAGE-CONTEXT-001 Phase A.2 successfully demonstrated typed context adoption for both modes.
The per-reflection gradient issue requires separate diagnostic work (likely TORCH-REFINE-004 follow-up).
