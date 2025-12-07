# Input for Ralph — Loop i=116

## Summary
Fix double-sqrt scaling bug in reconstruction cold path by making `apply_sqrt_spot_scale` conditional on `log_scale_baseline` absence.

## Mode
`none` (production bugfix, not test-first)

## ActionType
`implementation_ready`

## DecisionStatus
`patch_ready`

## InitiativeType
`architecture` (ARCH-CONTRACT enforcement)

## Focus
`ARCH-IMPL-CONFORMANCE-001` — Architecture / Implementation Contract Alignment (Phase B.6)

## Branch
`integration`

## Mapped Tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/`

## Findings Applied (Mandatory)
- **SCALE-008**: Stage A warm-cache authority and masked-intensity baseline
- **SCALE-009**: Reconstruction scaling provenance (to be updated post-fix with double-scaling root cause)
- **ARCH-CONTRACT-001**: Stage A vs reconstruction scaling alignment (enforced via conditional sqrt application)
- **ARCH-CONTRACT-002**: Post-run scaling pattern (canonical `apply_sqrt_spot_scale` API, conditional usage)

## Pointers
- Planning doc: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/phase_b6_planning.md`
- Evidence: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_decision.md`
- Stage A scaling logic: `dbex/refinement/stage_a.py:172-177, 500-514, 1275-1290`
- Reconstruction cold path: `dbex/refinement/reconstruction.py:88-223, 373-395, 499-513`
- Canonical API: `dbex/refinement/scaling_utils.py:35-111`
- Enforcement tests: `tests/architecture/test_scale_contracts.py:24-302`

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment
- **Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- **Owner Module**: `dbex/refinement/scaling_utils.py`
- **Duplicates Being Removed**: Unconditional `apply_sqrt_spot_scale` call in reconstruction.py:506 (will be conditional)
- **Failure Classification**: **Implementation bug within architecture** (reconstruction cold path incorrectly applies sqrt twice when log_scale_baseline present)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- **Owner Module**: `dbex/refinement/scaling_utils.py`
- **Usage Rule**: Apply ONLY when `log_scale_baseline` is absent (uncalibrated path); skip when `log_scale_baseline` present (calibrated path already includes sqrt in `scale_factor`)
- **Failure Classification**: **Implementation bug** (conditional logic missing)

## Do Now (hard validity contract)

### Focus Item
ARCH-IMPL-CONFORMANCE-001 Phase B.6 — Fix double-sqrt scaling in reconstruction cold path

### Implement
**File**: `dbex/refinement/reconstruction.py`
**Function**: `build_final_bragg_from_stage_a_telemetry` (lines 501-513)

**Change**: Wrap `apply_sqrt_spot_scale` call in conditional to prevent double-scaling when `log_scale_baseline` is present.

**Before** (lines 501-513):
```python
# ARCH-CONTRACT-002 (Phase B.4, ARCH-IMPL-CONFORMANCE-001):
# Apply canonical spot_scale_override sqrt scaling
# For warm-path with full telemetry, log_scale_baseline incorporates sqrt_spot_scale,
# so this becomes identity (scale=1.0). For cold-path, this applies the missing sqrt factor.
bragg_prescaled_np = bragg_prescaled.cpu().numpy()
bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, effective_calibration_metadata)
bragg_scaled = torch.from_numpy(bragg_scaled_np).to(
    device=bragg_panel.device, dtype=bragg_panel.dtype
)

if pid == 0:
    print(f"  bragg_scaled[0] mean (after scale_factor × baseline_alignment × sqrt_spot_scale): {bragg_scaled.mean().item():.6e}")
bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**After** (lines 501-520, expanded):
```python
# ARCH-CONTRACT-002 (Phase B.6, ARCH-IMPL-CONFORMANCE-001):
# Apply canonical spot_scale_override sqrt scaling ONLY when log_scale_baseline is absent.
# When log_scale_baseline is present (calibrated path), scale_factor already incorporates
# sqrt(spot_scale) per stage_a.py:173, so applying it again would double-scale.
#
# Root cause (Phase B.5 analysis): Reconstruction cold path was applying sqrt twice:
#   1. scale_factor = exp(log_scale_baseline) = exp(log(sqrt(spot_scale))) = sqrt(spot_scale)
#   2. apply_sqrt_spot_scale multiplies by sqrt(spot_scale) again
#   Result: raw * sqrt * sqrt = raw * spot_scale (2× correct scaling, ~35× mismatch)
if log_scale_baseline_value is None:
    # Uncalibrated path: scale_factor doesn't include sqrt, apply it separately
    bragg_prescaled_np = bragg_prescaled.cpu().numpy()
    bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, effective_calibration_metadata)
    bragg_scaled = torch.from_numpy(bragg_scaled_np).to(
        device=bragg_panel.device, dtype=bragg_panel.dtype
    )
    scaling_path = "uncalibrated (scale_factor + apply_sqrt_spot_scale)"
else:
    # Calibrated path: scale_factor = exp(log_scale_baseline) already includes sqrt(spot_scale)
    # Do not apply sqrt scaling again to avoid double-scaling
    bragg_scaled = bragg_prescaled
    scaling_path = "calibrated (scale_factor only, no double-sqrt)"

if pid == 0:
    print(f"  bragg_scaled[0] mean ({scaling_path}): {bragg_scaled.mean().item():.6e}")
bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

### Validating Pytest Nodes
```
tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale
tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

### Artifacts Path
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/`

### Initiative Type Consistency
✓ `architecture` initiative requesting implementation of ARCH-CONTRACT conditional logic (fixing implementation bug within architecture)

## Forbidden This Loop
- No new probes or diagnostic scripts
- Do not extend plan-local helpers
- Do not modify `apply_sqrt_spot_scale` API (already correct, just misused)
- Do not change Stage A scaling logic (already correct)
- Do not modify warm-cache fast-path (lines 96-99, already correct)

## How-To Map

### Step 1: Edit reconstruction.py
Apply the code change described above to `dbex/refinement/reconstruction.py` lines 501-520.

### Step 2: Run enforcement tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/pytest_phase_b6_fix.log 2>&1
```

### Step 3: Expected outcomes
- **Phase A.1** (warm-cache): PASS (regression check, no code changes)
- **Phase A.2** (cold-path): PASS with rel_error < 1e-6 (currently FAILING with 3420% error)

### Step 4: Commit artifacts
```bash
git add plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/pytest_phase_b6_fix.log
git add plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/phase_b6_summary.md
```

Write `phase_b6_summary.md` with:
- Test results (both PASS expected)
- Metrics: Phase A.2 rel_error before (64.6%) vs after (<0.0001%)
- Next phase: B.7 (findings update) then C.1 (DB-AT-027/028/029 alignment)

## Pitfalls To Avoid

1. **Type Discipline**: This is `architecture` initiative (ARCH-CONTRACT enforcement), not `bugfix`. The bug is an implementation failure to follow the architecture contract.

2. **No Stacking**: Phase B.5 proved calibration threading works. Do not add more threading code.

3. **Parity-First**: Warm-cache path already has parity (Phase A.1 PASS). This fix brings cold-path into parity with it.

4. **Shadow-Pipeline Guard**: Do not create new diagnostic scripts. Use existing enforcement tests only.

5. **Evidence→Action**: Phase B.5 evidence identified exact root cause (double-sqrt) and exact fix location (conditional at line 506). Implement exactly that.

6. **Dominant-Hypothesis Lock**: Confidence=0.9 for double-sqrt hypothesis. No additional probes allowed.

7. **ARCH Conformance Enforcement**: Phase B.6 fix must bring both enforcement tests to PASS. Next loop will add enforcement for uncalibrated path if needed.

8. **No Environment Changes**: All changes to dbex code only, no nanobrag_torch patches.

9. **Preserve Debug Logs**: Keep existing debug logging but update messages to reflect conditional logic.

10. **Test Both Paths**: Run both warm-cache and cold-path tests to ensure no regressions.

## If Blocked

If Phase A.2 test still fails after fix:
1. Capture exact metrics: `masked_mean_stage_a`, `masked_mean_reconstruction_cold`, `rel_error`, `ratio`
2. Check pytest log for which scaling path was used (calibrated vs uncalibrated)
3. Verify `log_scale_baseline_value` is NOT None for refGeom fixture (should be ~20.14)
4. Write `blocked_analysis.md` with evidence and hypothesis for next root cause
5. Do NOT attempt more fixes this loop; return to Galph for re-planning

## Doc Sync Plan (Conditional)
Not applicable (no new tests added this loop; enforcement tests already exist from Phase A.0-A.2)

---

**Galph's Assessment**: Phase B.5 evidence is conclusive. This is a straightforward conditional fix with high confidence. Ralph should implement exactly as specified and expect both tests to PASS. If not, escalate with detailed metrics rather than debugging further.
