# Phase B2 Diagnostic Test Blocker

## Summary
Phase B2 diagnostic test (2-step LBFGS with enhanced telemetry) timed out after 20 minutes during HKL grid building phase. Only zero-point check completed; no optimizer steps or telemetry captured.

## Timeline
- **09:10**: Started diagnostic test with 1200s (20min) timeout
- **09:11**: Zero-point check completed successfully (chi²=989,811, matching B1 validation)
- **09:11-09:31**: Stuck building HKL grids (40+ grids observed in log)
- **09:31**: Timeout exit code 143

## Root Cause
LBFGS optimizer performs multiple line search evaluations per step, each requiring full HKL grid build. With 2 optimizer steps and conservative max_iter=20 per LBFGS step, estimated grid builds: 2 × 20 × 2 (forward+backward) = 80+ grids. At ~15-30s per grid on CPU, total time would exceed 20-40 minutes.

## Artifacts Created
- `diagnostic/zero_point_check.json`: Confirms B_ideal fix works (chi²=989,811, corr≈1.0)
- `diagnostic/commands.txt`: Command log
- `diagnostic_test.log`: Partial log showing HKL grid building loop

## Artifacts Missing
- `diagnostic/telemetry/telemetry_step_000.json`: Not created (optimizer never ran)
- `diagnostic/telemetry/telemetry_step_001.json`: Not created
- `diagnostic/block_dof_results_u_matrix.json`: Not created

## Decision
Per `input.md` "If Blocked" section (lines 280-290): Skip FD validation and Phase B2 telemetry collection; rely on Phase B1 validation results (2025-11-22T183000Z) which already provide decisive evidence:

### Evidence from Phase B1 (2025-11-22T183000Z)
1. **Zero-point validation**: chi²=989,811 (healthy), confirms B_ideal fix works
2. **Step 0 (LBFGS initialization)**: chi²=1.13M (healthy, 1.14× expected)
3. **Steps 1-3 (LBFGS optimization)**: chi²=1.425B (catastrophic, 1257× degradation)
4. **Correlation collapse**: CC 1.0 → -0.045 (anti-correlation)

### Critical Findings
- **Initialization pathology**: RESOLVED (step 0 healthy confirms B_ideal fix from commit e86fd4e)
- **Convergence pathology**: PERSISTS (steps 1-3 catastrophic failure)
- **Optimizer-agnostic**: Both Adam (PARITY-003) and LBFGS (B1 validation) fail identically

## Next Actions
Proceed to Phase B2 decision synthesis using B1 validation evidence. Enhanced telemetry (V_denom, weighted residuals, sign consistency) would be helpful but NOT required for root cause determination given the clear initialization vs convergence pathology split.

## Recommended Fix
Based on repeat-failure guard (input.md lines 38-41): Phase B2 instrumentation + diagnostic test are blocked by computational cost. Escalate to **evidence-only decision** path:
- H1 (optimizer hyperparameters): REJECTED (LBFGS also fails)
- H2 (variance instability): PLAUSIBLE (need full-panel variance analysis)
- H3 (gradient pathology): PLAUSIBLE (need gradient magnitude/NaN checks)
- H4 (forward model bug): PLAUSIBLE (step 0→step 1 transition breaks)

## References
- input.md lines 276-290: "If Blocked" → skip FD validation, rely on telemetry analysis
- B1 validation decision: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/phase_b1_validation_decision.md`
- Prior telemetry (Phase A1, limited): `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/`
