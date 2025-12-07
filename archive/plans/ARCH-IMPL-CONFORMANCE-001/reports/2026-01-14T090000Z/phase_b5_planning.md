# Phase B.5 Planning — Calibration Threading Audit

**Loop**: i=114 (planning)
**Phase**: B.5 (evidence collection + diagnosis)
**Initiative**: ARCH-IMPL-CONFORMANCE-001
**Timestamp**: 2026-01-14T090000Z

## Problem Statement

Phase A.2 cold-path enforcement test FAILS with 64.6% relative error (ratio 2.83:1) even after:
1. Loop i=111 (Phase B.1-B.2): Created canonical `apply_sqrt_spot_scale` API + threaded `calibration_metadata` parameter to `build_final_bragg_from_stage_a_telemetry` signature
2. Loop i=112 (Phase B.3-B.4): Refactored Stage A + reconstruction to delegate sqrt scaling to canonical API
3. Loop i=113 (diagnostic): Extended pytest timeout revealed test completes in 49.8s, not hung; Ralph threaded `calibration_metadata=stage_a_ctx.calibration` to `RefinementConfig` constructor

**Evidence that threading is incomplete**:

From `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/pytest_phase_a2_extended_timeout.log`:

```
Line 13: bragg_panel[0] mean (raw sim output): 6.897007e-01
Line 15: bragg_scaled[0] mean (after scale_factor × baseline_alignment × sqrt_spot_scale): 6.897007e-01
```

Raw output == Scaled output → `apply_sqrt_spot_scale` saw `calibration_metadata=None`.

Expected behavior:
- `spot_scale_override ≈ 3.2e17` (from refGeom calibration metadata)
- `sqrt(spot_scale_override) ≈ 5.66e8`
- Scaled output should be ~5.66e8× larger than raw

**Current status**: Raw and scaled outputs are IDENTICAL, proving the sqrt_spot_scale multiplication was a no-op.

## Hypothesis

The `effective_calibration_metadata` defaulting logic at reconstruction.py:219 is failing:

```python
effective_calibration_metadata = calibration_metadata or config.calibration_metadata
```

Two possible causes:
1. **Signature threading issue**: `calibration_metadata` parameter not passed through full call chain (test → build_final_bragg_from_stage_a_telemetry → apply_sqrt_spot_scale)
2. **Config hydration issue**: `config.calibration_metadata` not correctly set even though test passes `calibration_metadata=stage_a_ctx.calibration` to `RefinementConfig` constructor

## Phase B.5 Objectives

1. **Trace calibration_metadata threading** through 4 hops:
   - test_scale_contracts.py:258-262 → RefinementConfig constructor
   - test_scale_contracts.py:267 → build_final_bragg_from_stage_a_telemetry call
   - reconstruction.py:219 → effective_calibration_metadata assignment
   - reconstruction.py:506 → apply_sqrt_spot_scale call

2. **Add diagnostic logging** at each hop to capture:
   - Whether calibration_metadata is None or dict
   - If dict, emit `spot_scale_override` value
   - Emit caller file:line for forensics

3. **Confirm apply_sqrt_spot_scale execution** by instrumenting scaling_utils.py:83-111 to log:
   - Input: `calibration_metadata` (None vs dict keys)
   - Computed: `sqrt_spot_scale` value
   - Output: `bragg.mean()` before and after multiplication

## Expected Outcomes

### Scenario A: Config hydration bug
If logs show:
- test passes `calibration_metadata={'spot_scale_override': 3.2e17, ...}`
- `config.calibration_metadata` is None or missing key
→ **Root cause**: RefinementConfig constructor not preserving calibration_metadata parameter

**Fix**: Ensure RefinementConfig.__init__ assigns `self.calibration_metadata = calibration_metadata`.

### Scenario B: Signature threading bug
If logs show:
- `config.calibration_metadata` is correctly set
- BUT `effective_calibration_metadata` at reconstruction.py:219 is None
→ **Root cause**: `calibration_metadata` parameter not passed to build_final_bragg_from_stage_a_telemetry

**Fix**: Ensure test passes `calibration_metadata=stage_a_ctx.calibration` explicitly (not just via config).

### Scenario C: Default parameter bug
If logs show:
- Both `calibration_metadata` parameter and `config.calibration_metadata` are None
→ **Root cause**: Test not threading calibration at all; Ralph's fix didn't actually apply

**Fix**: Review test_scale_contracts.py lines 254-262 to confirm calibration threading actually exists in git HEAD.

## Validation Criteria

Once logging is added and test re-run, we must see:

```
[CALIBRATION TRACE] test_scale_contracts.py:261 → RefinementConfig: calibration_metadata={'spot_scale_override': 3.2e17, ...}
[CALIBRATION TRACE] reconstruction.py:219 → effective_calibration_metadata: spot_scale_override=3.2e17
[CALIBRATION TRACE] scaling_utils.py:102 → sqrt_spot_scale=5.66e8
[CALIBRATION TRACE] scaling_utils.py:111 → bragg.mean() BEFORE=6.9e-01, AFTER=3.9e8
```

If any hop shows None, we've localized the break in the chain.

## Artifacts to Emit

1. `phase_b5_calibration_trace.log` — pytest output with instrumented logging
2. `phase_b5_decision.md` — Root cause determination (Scenario A/B/C) + fix path
3. Updated test file (if threading fix needed)
4. Updated reconstruction.py with logging (temporary, remove after diagnosis)

## Next Steps (Phase B.6)

Depending on diagnosis:
- **If Scenario A**: Fix RefinementConfig constructor, rerun test (expect PASS)
- **If Scenario B**: Fix test call site, rerun test (expect PASS)
- **If Scenario C**: Fix test to actually thread calibration, rerun test (expect PASS)

After fix, Phase A.2 test should PASS with:
```
masked_mean_stage_a ≈ 2.16e+00
masked_mean_reconstruction_cold ≈ 2.16e+00
rel_error ≈ 1e-07
```

## ARCH Constraints

- **ARCH-CONTRACT-002**: Single owner API for sqrt scaling (scaling_utils.py:apply_sqrt_spot_scale)
- **SCALE-008**: Stage A warm-cache baseline authority (simulate_forward_once)
- **SCALE-009**: Reconstruction must match Stage A scaling when param_state="initial"

## Finding References

- SCALE-002 (docs/findings.md:39): Post-simulation sqrt scaling requirement
- SCALE-008 (docs/findings.md:42): Baseline authority and threading requirements
- SCALE-009 (docs/findings.md:43): Reconstruction scaling provenance (UPDATED by this initiative)
