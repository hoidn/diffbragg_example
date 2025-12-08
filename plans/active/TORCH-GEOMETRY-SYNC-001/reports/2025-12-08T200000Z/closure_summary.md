# TORCH-GEOMETRY-SYNC-001 Closure Summary

## Executive Summary

The TORCH-GEOMETRY-SYNC-001 roll-up initiative has achieved its primary objective: geometry convergence and parity alignment for Stage A refinement. All exit criteria are satisfied through the completion of 2 member plans and the supersession of 2 additional member plans whose goals were absorbed by the incremental UB approach.

## Member Plan Status Table

| Plan ID | Title | Status | Exit Criteria |
|---------|-------|--------|---------------|
| TORCH-GEOMETRY-CONVERGENCE-001 | Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure | **done** | 5/5 complete |
| TORCH-GEOMETRY-UB-REALIGN-001 | Stage A UB Parameterization Realignment | **done** | 5/5 complete |
| TORCH-GEOMETRY-PARITY-002 | Direct U-Matrix Parameterization for Stage A Geometry Refinement | **superseded** | Absorbed by UB-REALIGN-001 |
| TORCH-GEOMETRY-PARITY-003 | Investigate det(U)≠1 Root Cause & Hybrid Parameterization | **superseded** | Absorbed by UB-REALIGN-001 |

## Key Accomplishments

### TORCH-GEOMETRY-CONVERGENCE-001

- **Root Cause Identified:** Diagnosed quaternion catastrophic failure (CC→-0.045, χ²→1.43B) as a diagnostic script bug, NOT fundamental optimizer/quaternion incompatibility
- **Fix Pattern:** Zero-check bypass detection + conditional code path selection
- **Convergence Achieved:** chi² drift +0.0083% over 10 steps (well below 1% threshold), CC ≈1.0 throughout
- **Systematic Offset:** 14.5% offset between zero-point and closure init is ACCEPTABLE (reproducible, doesn't affect convergence stability)

### TORCH-GEOMETRY-UB-REALIGN-001

- **Spec-Compliant Parameterization:** Implemented incremental UB approach treating dxtbx U₀/B₀ as authoritative baseline
- **Orientation:** Quaternion-based ΔR, `U(params) = ΔR(q_delta) @ U₀`
- **Cell:** Log-perturbations for lengths, unbounded deltas for angles, Busing-Levy B-matrix derivation
- **Zero-Point Invariant:** `q_delta = [1,0,0,0]` (identity), all deltas = 0 → `U(0) = U₀`, `B(0) = B₀`
- **DB-AT-026 Tests:** 4/4 tests PASS (U zero-point, B zero-point, A* parity, gradient flow)

### Superseded Plans (PARITY-002, PARITY-003)

- **Original Goal:** Investigate det(U)≠1 and implement hybrid cell+U+scale parameterization
- **Supersession Rationale:** The incremental UB approach using dxtbx U₀/B₀ as baseline with quaternion ΔR increments bypassed the det(U)≠1 issue entirely without requiring det(U)=1 enforcement or hybrid parameterization

## Test Coverage Summary

| Test ID | Description | Status |
|---------|-------------|--------|
| DB-AT-024 | Mapping parity | PASS |
| DB-AT-026 | UB parameterization round-trip (4 tests) | PASS |
| test_stage_a_expansion | Regression guard | PASS |

6 geometry-related tests available and passing.

## Lessons Learned

1. **Incremental Parameterization Approach:** Treating the dxtbx/DIALS crystal state as authoritative baseline (U₀, B₀) and parameterizing as increments proved more robust than attempting to decompose A* into U and B.

2. **Diagnostic Script Bugs vs Production Code:** The catastrophic convergence failure was traced to code path divergence in diagnostic scripts, not production refinement code. This highlights the importance of validating diagnostic tools against production behavior.

3. **Zero-Point Validation:** Strict zero-point invariant tests (DB-AT-026) provide essential regression guards for geometry parameterization changes.

4. **Supersession as Valid Outcome:** When investigation reveals a simpler solution path, formally superseding exploratory plans (PARITY-002, PARITY-003) rather than completing them prevents wasted effort.

## Artifacts

- Phase A artifacts: `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/`
- Phase B closure: `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/`
- CONVERGENCE-001 evidence: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/`
- UB-REALIGN-001 evidence: `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/`

## Closure Date

2025-12-08T200000Z
