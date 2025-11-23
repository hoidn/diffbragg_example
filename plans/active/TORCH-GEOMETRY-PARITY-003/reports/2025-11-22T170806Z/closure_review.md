# PARITY-003 Closure Review

## Context
TORCH-GEOMETRY-CONVERGENCE-001 completed successfully (2025-11-22T252000Z) with a zero-check bypass fix that achieves stable convergence (chi² drift +0.0083%, CC≈1.0 over 10 steps).

## Key Findings from CONVERGENCE-001
1. **Root Cause:** Code path divergence in diagnostic script parameter reconstruction, NOT a fundamental issue with quaternion U-matrix parameterization or det(U)≠1
2. **Fix Applied:** Zero-check bypass logic detects when all parameter deltas are zero and forces direct MOSFLM injection
3. **Production Code:** dbex/nanobrag_refinement.py does NOT exhibit this pathology
4. **Det(U) Investigation:** The 0.06% offset (det(U)=1.000565) is a nanobrag_torch/dxtbx parity artifact from different computation paths, NOT a physics blocker

## PARITY-003 Status Assessment

### Original Goals (from implementation.md)
- Investigate why `det(U₀)=1.000557`
- Design hybrid cell+U+scale parameterization
- Restore Stage A convergence

### Current State
- **det(U) investigation:** RESOLVED - artifact from computation path difference, not a physical/calibration issue
- **Convergence:** RESOLVED - zero-check bypass enables stable convergence
- **Hybrid parameterization:** NO LONGER NEEDED for convergence (quaternion works with bypass)

## Recommendation

### Option A: Close PARITY-003 as RESOLVED
**Rationale:**
- Primary goal (investigate det(U)≠1 convergence failure) is RESOLVED
- Quaternion approach works with bypass fix
- No evidence that hybrid parameterization is needed for convergence

**Action:** Mark PARITY-003 as `done` with note that convergence was resolved via CONVERGENCE-001 bypass fix

### Option B: Archive PARITY-003 as SUPERSEDED
**Rationale:**
- UB-REALIGN-001 was created to implement incremental UB/A* parameterization per updated specs
- This represents a different design approach (incremental around baseline) vs PARITY-003 (hybrid factorization)
- Forward path is UB-REALIGN-001, not PARITY-003

**Action:** Mark PARITY-003 as `archived` with note "Superseded by UB-REALIGN-001; convergence issue resolved via CONVERGENCE-001"

## Chosen Recommendation: Option B (Archive as Superseded)

**Reasoning:**
1. UB-REALIGN-001 explicitly depends on "TORCH-GEOMETRY-CONVERGENCE-001 (verdict/requirements)"
2. The updated specs (spec-db-core.md, spec-db-workflow.md) specify incremental UB parameterization as the normative approach
3. PARITY-003's hybrid factorization investigation is no longer needed given CONVERGENCE-001 verdict
4. Clean separation: PARITY-003 investigated a hypothesis (det(U)≠1 causes convergence failure), CONVERGENCE-001 disproved it, UB-REALIGN-001 implements the spec-compliant forward path

## Actions
1. Update docs/fix_plan.md: Change PARITY-003 status from `blocked` to `archived`
2. Add Attempts History entry documenting closure rationale
3. Update Execution Roadmap to remove PARITY-003 from active Tier 1 items
4. Focus next loop on UB-REALIGN-001 Phase A (Design & Spec Alignment)
