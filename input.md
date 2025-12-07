# Input for Loop i=119 (Ralph Implementation)

## Summary
Fix baseline_alignment_factor fallback logic in reconstruction cold-path to compute alignment from ACTUAL cold-path output instead of reusing mapping's pre-computed ratio.

## Mode
none (production bug fix)

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment (Phase B.9: baseline_alignment_factor correction)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

**Expected outcome**: Both tests PASS with rel_error < 1e-6

## Artifacts
plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T053000Z/

## Findings Applied (Mandatory)
- SCALE-002 (docs/findings.md:39): DiffBragg spot_scale_override re-applied as sqrt factor
- SCALE-008 (docs/findings.md:42): Stage A warm-cache baseline authority
- SCALE-009 (docs/findings.md:43): Reconstruction scaling provenance (will be updated after this fix)
- ARCH-CONTRACT-002: Post-Run Scaling Pattern (Phase B.1-B.9 enforcement)

No relevant findings require deviation from planned implementation.

## Pointers

### ARCH Contracts
- **ARCH-CONTRACT-002** (dbex/refinement/scaling_utils.py:8-14): Post-Run Scaling Pattern
  - Owner API: `apply_sqrt_spot_scale(bragg, calibration_metadata)`
  - Consumers: Stage A (stage_a.py:442-443), reconstruction (reconstruction.py:557), mapping (simulate_forward_once)

- **Reconstruction Cold-Path Baseline Alignment** (NEW, established by Phase B.9):
  - Owner: reconstruction.py:464-503
  - Contract: When `telemetry_a.model_mean_masked` is unavailable (e.g., minimal test fixtures), compute `baseline_alignment_factor = target_mean / cold_masked_mean` from ACTUAL cold-path output
  - Forbidden: Reusing `masked_mean_ratio` from calibration_metadata (assumes simulator parity, which doesn't hold)
  - Classification: Implementation bug within architecture (not conformance failure)

### Key Spec/Arch/Testing Docs
- docs/spec-db-core.md:55 — loss_mask definition: `(background >= 0) & trusted_mask`
- docs/spec-db-core.md:60-140 — Acceptance tolerance: 1e-6 relative error for parity tests
- dbex/refinement/inputs.py:230 — loss_mask construction
- dbex/vis/mapping.py:287-300 — masked_mean_ratio computation and application
- dbex/refinement/reconstruction.py:429-543 — baseline_alignment_factor logic (lines 464-503 contain the bug)
- plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md — Phase B checklist
- plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T052400Z/phase_b8_root_cause_analysis.md — Detailed mathematical proof

## Do Now

### Context
Loop i=117 (Ralph) implemented Phase B.8 test mask contract fix correctly (using `inputs.loss_mask`), but the cold-path test now fails with **12.77% relative error** (worse than pre-fix 2.46%). Galph's analysis (loop i=118) identified the root cause: the baseline_alignment_factor fallback logic at reconstruction.py:464-484 incorrectly reuses `masked_mean_ratio` from calibration_metadata, which assumes reconstruction and mapping simulators produce identical raw outputs. They don't (~13% mismatch), causing alignment failure.

**Mathematical proof**:
Mapping computes `masked_mean_ratio = target_mean / mean((raw_mapping_sim * sqrt(spot))[loss_mask])` and applies it to mapping's output. For reconstruction cold-path to match, it needs `baseline_alignment_factor = target_mean / mean((raw_recon_sim * sqrt(spot))[loss_mask])`, which must be computed from the ACTUAL cold-path output, not reused from mapping.

### Implement
- **File**: `dbex/refinement/reconstruction.py`
- **Function**: `build_final_bragg_from_stage_a_telemetry`
- **Lines**: 464-484 (elif branch fallback logic)

**Current (incorrect) code** (lines 477-479):
```python
masked_mean_ratio = effective_calibration_metadata.get("masked_mean_ratio")
if masked_mean_ratio is not None and masked_mean_ratio > 0 and np.isfinite(masked_mean_ratio):
    baseline_alignment_factor = masked_mean_ratio  # ← WRONG: reuses mapping's ratio
```

**Replacement logic**:
```python
# ARCH-CONTRACT-002 Phase B.9 (ARCH-IMPL-CONFORMANCE-001):
# Compute baseline_alignment_factor from ACTUAL cold-path output and target
# to ensure reconstruction matches mapping's scaled intensity over loss_mask.
#
# Mapping computes: masked_mean_ratio = target_mean / bragg_mean_mapping
#                   bragg_final = bragg_mapping * masked_mean_ratio
#                   → mean(bragg_final[loss_mask]) = target_mean (by construction)
#
# Reconstruction must match: mean(bragg_recon[loss_mask]) = target_mean
# Therefore: baseline_alignment_factor = target_mean / cold_masked_mean
#           where cold_masked_mean = mean((raw_recon * sqrt(spot))[loss_mask])
#
# This differs from Phase B.7 (which reused masked_mean_ratio) because:
# - Phase B.7 assumed raw_recon = raw_mapping (simulator parity)
# - Observed: reconstruction simulator produces ~13% more intensity than mapping
# - Phase B.9 fix: compute alignment from actual cold-path output
#
# References:
# - dbex/vis/mapping.py:287-300 (mapping's masked_mean_ratio computation)
# - Phase B.8 root cause analysis (loop i=118, plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T052400Z/)

# Extract target mean over loss_mask
if hasattr(inputs, 'target') and inputs.target is not None:
    target_mean_masked = float(inputs.target[inputs.loss_mask].mean())

    # Validate: target_mean and cold_masked_mean must be finite/positive
    if (target_mean_masked > 0 and np.isfinite(target_mean_masked) and
        cold_masked_mean > 0 and np.isfinite(cold_masked_mean)):
        baseline_alignment_factor = target_mean_masked / cold_masked_mean
        alignment_source = "cold_path_actual_output"
        print(f"[ARCH-CONTRACT-002 Phase B.9] Cold-path baseline alignment from actual output:")
        print(f"  target_mean_masked: {target_mean_masked:.6e}")
        print(f"  cold_masked_mean (raw * sqrt(spot)): {cold_masked_mean:.6e}")
        print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
        print(f"  source: {alignment_source}")
    else:
        # Emit warning if alignment cannot be computed
        print(f"[ARCH-CONTRACT-002 Phase B.9 WARNING] Cannot compute baseline alignment:")
        print(f"  target_mean_masked: {target_mean_masked if hasattr(inputs, 'target') and inputs.target is not None else 'N/A'}")
        print(f"  cold_masked_mean: {cold_masked_mean}")
        baseline_alignment_factor = 1.0
        alignment_source = "default_fallback"
else:
    # No target available, cannot compute alignment
    print(f"[ARCH-CONTRACT-002 Phase B.9 WARNING] inputs.target not available; cannot compute baseline alignment")
    baseline_alignment_factor = 1.0
    alignment_source = "default_fallback"
```

**Location details**:
- Replace lines 477-484 (the inner if/else block inside the `elif effective_calibration_metadata...` branch)
- Keep the outer elif condition (line 464) unchanged
- Keep the outer else branch (lines 485-492) unchanged for the case where `effective_calibration_metadata` is None or doesn't contain masked_mean_ratio

**Import check**: Ensure `numpy as np` is imported at the top of the file (already present at line 25)

### Validation
1. Run both enforcement tests:
   - `test_stage_a_vs_reconstruction_scale` (warm-cache, expect PASS, regression check)
   - `test_stage_a_vs_reconstruction_scale_cold_path` (cold-path, expect PASS, rel_error < 1e-6)

2. Expected metrics after fix:
   - Stage A masked_mean: 87.11842 (unchanged)
   - Reconstruction cold-path masked_mean: ~87.11842 (should match Stage A within 1e-6)
   - Relative error: < 1e-6
   - Ratio (stage_a / reconstruction_cold): ~1.0

3. If tests PASS:
   - Write pytest logs to artifacts directory
   - Update implementation.md Phase B.9 status to "complete"
   - Commit with message: "[ARCH-IMPL-CONFORMANCE-001] Phase B.9 baseline_alignment_factor correction (tests: ...)"

4. If tests FAIL:
   - Capture full pytest output + debug prints to artifacts directory
   - Report failure signature (rel_error, ratio, debug values) in summary.md
   - Mark Phase B.9 blocked and recommend next action (parity localization OR architecture split)

### Artifacts to write
- pytest logs: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T053000Z/pytest_phase_b9_fix.log`
- Summary: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T053000Z/summary.md`
- Update implementation.md Phase B.9 checklist

## Forbidden This Loop
- No new probes or plan-local diagnostic scripts (enforcement: PROBE-FREEZE-001)
- No changes to simulator factory configuration (scope: baseline_alignment_factor correction only)
- No changes to test_scale_contracts.py (Phase B.8 already fixed test mask contract)
- No changes to dbex/refinement/scaling_utils.py (canonical API is correct)

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=metadata
export DBEX_SMOKE_DETECTOR_SIZE=full
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Step 1: Implement Fix
1. Read `dbex/refinement/reconstruction.py` lines 464-503
2. Identify the elif branch starting at line 464
3. Replace lines 477-484 with the new logic (see "Implement" section above)
4. Verify imports (numpy should already be present)

### Step 2: Run Tests
```bash
pytest -xvs \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T053000Z/pytest_phase_b9_fix.log 2>&1
```

### Step 3: Capture Artifacts
```bash
# Create summary.md with test outcomes
# Update implementation.md Phase B.9 status
# Commit changes if tests PASS
```

## Pitfalls To Avoid
1. **Type discipline**: This is an architecture fix (implementation bug within architecture), not a spec_change
2. **No stacking**: If this fix fails, do NOT add more probes; mark blocked and escalate per non-negotiables
3. **Parity-first**: This fix addresses the baseline_alignment_factor logic, but if tests still fail, the issue may be deeper (simulator config mismatch)
4. **No double-scaling**: The fix should only change the alignment factor computation; do NOT touch the scale_factor or apply_sqrt_spot_scale logic
5. **Evidence→Action contract**: If tests fail, capture exact failure signature (rel_error, ratio, target_mean, cold_masked_mean) and return to Galph for analysis
6. **Repeat-signature freeze**: Same selector (test_stage_a_vs_reconstruction_scale_cold_path) + same failure signature (scale mismatch) has recurred 2 loops (B.7→B.8→B.9); if this fix fails, next loop MUST either mark blocked OR open new architecture/spec_change initiative per non-negotiables
7. **Implementation floor**: This is the 5th loop on this acceptance criterion (B.5/B.6/B.7/B.8/B.9); if fix fails, we're approaching the 6-loop hard limit per loop discipline
8. **ARCH/Impl consistency gate**: This fix maintains ARCH-CONTRACT-002 (post-run scaling pattern); it corrects the fallback logic to match the contract's intent
9. **Probe saturation**: No new probes allowed (signature-level saturation rule)
10. **Environment freeze**: Do NOT modify nanobrag_torch or external dependencies; only change reconstruction.py

## If Blocked

### Scenario 1: Tests still fail after fix (rel_error > 1e-6)
**Action**: Mark Phase B.9 blocked and report to Galph with:
- Exact failure signature (rel_error, ratio, target_mean, cold_masked_mean from debug prints)
- Full pytest log
- Hypothesis: simulator configuration mismatch between mapping and reconstruction cold-path

**Next step (Galph decides)**:
- Option A: Parity localization initiative to compare simulator configs
- Option B: Architecture split to new initiative (simulator factory parity)
- Option C: Spec_change to relax DB-AT-028/029 acceptance criteria

### Scenario 2: inputs.target not available
**Action**: Report to Galph that test fixture doesn't provide `inputs.target`

**Fix**: Update test to ensure `inputs.target` is populated (should already be present from `stage_a_ctx.inputs`)

### Scenario 3: Other unexpected failure (import errors, crashes, etc.)
**Action**: Capture full traceback, write to artifacts, report to Galph with error signature

## Doc Sync Plan
Not applicable (no tests added/renamed in this loop; enforcement tests already exist from Phase A)
