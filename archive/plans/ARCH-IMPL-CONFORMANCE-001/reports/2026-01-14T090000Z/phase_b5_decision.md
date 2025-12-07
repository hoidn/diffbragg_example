# Phase B.5 Decision — Calibration Threading Root Cause

**Loop**: i=114
**Phase**: B.5 (evidence collection)
**Initiative**: ARCH-IMPL-CONFORMANCE-001
**Timestamp**: 2025-12-06T19:53:00Z

## Executive Summary

Calibration threading is **WORKING CORRECTLY**. The trace log proves:
1. Test passes `calibration_metadata` to `RefinementConfig` ✓
2. `config.calibration_metadata` preserves `spot_scale_override` ✓
3. `effective_calibration_metadata` receives the dict ✓
4. `apply_sqrt_spot_scale` receives calibration_metadata and executes sqrt scaling ✓

**Root cause is NOT threading break** — it's **double-scaling or baseline mismatch**.

## Trace Evidence

### Hop 1: test_scale_contracts.py:262 → RefinementConfig created
```
Line 173-175:
  config.calibration_metadata: {'spot_scale_override': 4.786110784894759e+17, ...}
  spot_scale_override: 4.786110784894759e+17
```
✓ Test correctly passes calibration_metadata to config.

### Hop 2: reconstruction.py:221 → effective_calibration_metadata resolved
```
Line 177-181:
  calibration_metadata (param): None
  config.calibration_metadata: {'spot_scale_override': 4.786110784894759e+17, ...}
  effective_calibration_metadata: {'spot_scale_override': 4.786110784894759e+17, ...}
  spot_scale_override: 4.786110784894759e+17
```
✓ Defaulting logic works: `calibration_metadata or config.calibration_metadata` resolves correctly.

### Hop 3: scaling_utils.py:88 → apply_sqrt_spot_scale entry
```
Line 189-191:
  calibration_metadata: {'spot_scale_override': 4.786110784894759e+17, ...}
  spot_scale_override: 4.786110784894759e+17
```
✓ apply_sqrt_spot_scale receives calibration_metadata with spot_scale_override.

### Hop 4: scaling_utils.py:111 → applying sqrt_spot_scale
```
Line 193-195:
  applying sqrt_spot_scale=6.918172e+08
  bragg.mean() BEFORE: 9.901521e-08
  bragg.mean() AFTER: 6.850046e+01
```
✓ Scaling executes: sqrt(4.786e17) ≈ 6.918e8, multiplication succeeds.

### Hop 5: reconstruction.py:509 → apply_sqrt_spot_scale returned
```
Line 197-200:
  bragg_prescaled_np.mean(): 9.901521e-08
  bragg_scaled_np.mean(): 6.850046e+01
  ratio (scaled/prescaled): 691817536.000000
```
✓ Scaling ratio = 6.918e8 matches sqrt_spot_scale exactly.

### Final Metrics
```
Line 216-220:
  masked_mean_stage_a            = 2.151288e+00
  masked_mean_reconstruction_cold = 7.574263e+01
  rel_error                       = 3.420804e+01
  ratio (stage_a/reconstruction_cold) = 0.028403
```

**Problem**: Stage A mean = 2.15, reconstruction cold = 75.74.
**Ratio**: 0.028403 ≈ 1/35.2

## Analysis

### Threading Status: ✓ COMPLETE
All 4 hops show calibration_metadata present with correct spot_scale_override value.

### Scaling Execution: ✓ CORRECT
apply_sqrt_spot_scale:
- Received: spot_scale_override = 4.786e17
- Computed: sqrt_spot_scale = 6.918e8
- Applied: 9.90e-08 → 68.5 (ratio 6.918e8)

### Mismatch Source: DIFFERENT BASELINE or DOUBLE-SCALING

**Two hypotheses**:

#### Hypothesis 1: Stage A is ALSO applying sqrt_spot_scale (double scaling)
If Stage A already incorporated sqrt scaling in bragg_zero_iter, then reconstruction cold path re-applying it would produce:
- Stage A: raw × sqrt = X
- Reconstruction: raw × sqrt × sqrt = X × sqrt

Expected ratio: `1 / sqrt(4.786e17) = 1 / 6.918e8 ≈ 1.45e-9`

Observed ratio: `1 / 35.2 ≈ 0.028`

**This does NOT match double-scaling hypothesis.**

#### Hypothesis 2: Stage A uses DIFFERENT raw simulator output scale
Stage A and reconstruction cold path may be using different:
- N_cells (unit cell count calibration)
- beam_flux or beam_exposure
- baseline_alignment_factor

Line 182-187 WARNING:
```
[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:
  telemetry_model_mean_masked: None
  cold_masked_mean: 5.113107818033313e-06
  bragg_panel[0] mean (raw sim output): 9.901524e-08
```

This shows reconstruction cold path has DIFFERENT raw simulator output than Stage A.

Stage A bragg_zero_iter mean (masked) = 2.15
Reconstruction raw mean = 9.90e-08

**Ratio Stage A / reconstruction raw = 2.15 / 9.90e-08 ≈ 2.17e7**

After reconstruction applies sqrt_spot_scale = 6.918e8:
- reconstruction final = 9.90e-08 × 6.918e8 = 68.5

Stage A final = 2.15

**Ratio Stage A / reconstruction final = 2.15 / 68.5 = 0.0314 ≈ 1/31.8**

This matches observed 0.028 ≈ 1/35.2 (within 10% error).

### Root Cause Determination

**Scenario E (not in planning doc)**: Stage A and reconstruction cold path use **different simulator construction parameters**, causing raw simulator output to differ by ~2e7×.

Specifically:
1. Stage A raw output incorporates DIFFERENT calibration scaling (possibly N_cells, beam_flux)
2. Reconstruction cold path raw output is ~2e7× smaller
3. When reconstruction applies sqrt_spot_scale, it becomes ~32× larger than Stage A
4. This violates ARCH-CONTRACT-001 parity requirement

**Contributing factor**: Line 182 shows reconstruction cold path cannot compute `log_scale_effective` from telemetry (falls back to legacy computation). This may apply DIFFERENT scaling semantics than Stage A.

## Next Actions (Phase B.6)

### Blocked: Out of scope for `bugfix` initiative type

This is NOT a simple threading fix. The root cause is:
- **Stage A simulator construction** incorporates calibration scaling differently than **reconstruction cold path simulator construction**
- The difference is ~2e7× in raw output scale
- This requires auditing:
  1. `build_mapping_stage_a_context` → `simulate_forward_once` calibration application
  2. `build_final_bragg_from_stage_a_telemetry` cold path simulator construction (lines 88-223)
  3. Baseline alignment factor computation (reconstruction.py:C.14 warning)
  4. Legacy log_scale fallback semantics (line 182)

### Escalation Required

**Decision**: Mark ARCH-IMPL-CONFORMANCE-001 Phase B.5 as **BLOCKED** with escalation to Galph.

**Reason**:
- InitiativeType = architecture
- ActionType = evidence_collection → next must be arch_conformance
- But conformance fix requires comparing Stage A vs cold-path simulator factories
- This exceeds single-loop scope; needs supervisor decision on whether to:
  1. Split into sub-initiatives (Stage A audit, cold-path audit, convergence)
  2. Change to spec_change initiative (if Stage A semantics are normative)
  3. Deep-dive into legacy log_scale fallback removal

### Immediate Artifacts

1. ✓ `pytest_phase_b5_trace.log` — full trace with calibration threading proof
2. ✓ `phase_b5_decision.md` — this document
3. PENDING: Revert diagnostic logging (do not commit)
4. PENDING: Run warm-cache regression to confirm no breakage

## ARCH Contracts Status

### ARCH-CONTRACT-002: Post-Run Scaling Pattern ✓
- Owner API: `apply_sqrt_spot_scale` ✓
- Calibration threading: ✓ CONFIRMED WORKING
- Execution: ✓ CONFIRMED sqrt_spot_scale applied

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment ✗
- **VIOLATED**: 3420% relative error (ratio 1:35)
- Root cause: **Simulator construction parity break**, NOT threading
- Required fix: Align raw simulator output semantics (Phase B.6+)

## Evidence Files

- `pytest_phase_b5_trace.log` (this loop, 261 lines)
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/pytest_phase_a2_extended_timeout.log` (loop i=113, baseline)

## Findings to Update

- **SCALE-009** (docs/findings.md:43): Update with "Threading confirmed working; mismatch is simulator construction parity break"
- **NEW FINDING**: Stage A vs cold-path simulator construction use different calibration semantics (N_cells, baseline_alignment, log_scale_effective fallback)
