### Turn Summary
Extended Stage B and Stage C smoke tests to assert chi-squared and masked-MSE telemetry so the variance-weighted loss plumbing is validated; Stage A passed but Stage B/C both hit GPU divergence with the detached variance denominator.
**Blocker:** Stage B chi-squared LBFGS immediately hits NaN/Inf gradients on both CPU and CUDA (chi2~2.46e11), and Stage C diverges on CUDA (chi2: 8.08e3 → 3.02e8), blocking telemetry validation.
The underlying issue is spec-db-core.md:67 sigma_floor guard (V = max(I_model + sigma_readout^2, sigma_floor^2)) is not yet implemented in any stage closure, so predictions near zero cause infinite weights; need to land variance flooring before resuming this loop.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/ (pytest_stage_{a,b,c}.log)

---

## Loop Report: PHYSICS-LOSS-001 Telemetry Validation

**Timestamp:** 2025-11-20T235741Z
**Focus:** Validate chi-squared telemetry rollout by upgrading Stage B/C smokes
**Mode:** Parity
**Status:** Blocked (variance flooring not implemented)

### Problem Statement

Per `input.md`, this loop was tasked with extending Stage B (`test_stage_b_shell_modifiers`) and Stage C (`test_stage_c_detector_microslip`) smoke tests to assert the new chi-squared and masked-MSE telemetry fields introduced in PHYSICS-LOSS-001 Phase B, ensuring regressions in the variance-weighted loss plumbing are caught immediately.

**SPEC lines implemented:**
- `docs/spec-db-core.md:57-68` — Variance-weighted loss function (chi-squared) with detached IRLS denominator
- `docs/spec-db-core.md:67` — Variance flooring requirement (NOT YET IMPLEMENTED — blocker root cause)

**ADR/ARCH alignment:**
- `docs/findings.md` PHYSICS-LOSS-001:19 — Stage B/C must emit chi-squared + masked-MSE telemetry
- `docs/findings.md` REFINE-007 — Stage C improvement gate ~0.002%
- `docs/findings.md` REFINE-008 — Stage B improvement ceiling ~1e-8%

### Test Results

#### Stage A: PASSED (204.90s)
#### Stage B: BLOCKED — NaN/Inf gradients on CPU (chi2~2.46e11)
#### Stage C: BLOCKED — GPU divergence (chi2: 8.08e3 → 3.02e8)

**Blocker Root Cause:** spec-db-core.md:67 variance flooring not implemented

### Next Actions
1. Implement sigma_floor guard in compute_weighted_loss
2. Add sigma_floor to RefinementConfig and telemetry
3. Re-run Stage B/C with flooring enabled
