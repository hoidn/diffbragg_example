### Turn Summary (Loop i=117 — Galph Planning)

**Timestamp**: 2025-12-06T20:40:00Z
**Initiative**: ARCH-IMPL-CONFORMANCE-001 Phase B.7 (Implementation Ready)
**Status**: Planning complete, patch-ready for Ralph i=117

## Problem Analysis

Loop i=116 (Ralph) executed Phase B.6 conditional sqrt fix per Galph i=115 planning, achieving **significant improvement** but still failing tolerance:
- **Before (Phase B.5)**: 3520% rel_error, ratio 1/35.7 (double-sqrt bug)
- **After (Phase B.6)**: 738% rel_error, ratio 1/8.4 (sqrt fixed, **4.17× improvement**)
- **Target**: <0.0001% rel_error, ratio ≈ 1.0

Ralph's Phase B.6 implementation correctly eliminated double-sqrt scaling by making `apply_sqrt_spot_scale` conditional on `log_scale_baseline` absence. However, residual 8.4× mismatch persists.

## Root Cause Determination (Phase B.7)

**The problem is NOT a second sqrt bug—it's missing masked_mean_ratio adjustment from the mapping phase.**

### Evidence Trail

1. **Mapping phase** (`dbex/vis/mapping.py:297-312`):
   - Computes `masked_mean_ratio = target_mean_masked / bragg_mean_masked`
   - Applies to `bragg_zero_iter` in place: `bragg_zero_iter *= masked_mean_ratio`
   - Stores ratio in `calibration_metadata["masked_mean_ratio"]`

2. **Stage A warm-cache path**:
   - Uses cached `bragg_zero_iter` from `build_mapping_stage_a_context`
   - `bragg_zero_iter` **already includes** `masked_mean_ratio` adjustment
   - Test Phase A.1 PASSES with rel_error=0.0 (perfect warm-cache parity)

3. **Reconstruction cold path** (`dbex/refinement/reconstruction.py:418-471`):
   - Computes `baseline_alignment_factor` from `telemetry_a.model_mean_masked / cold_masked_mean`
   - But test provides **minimal telemetry** without `model_mean_masked` field (test_scale_contracts.py:226-239)
   - When `telemetry_model_mean_masked` is None, `baseline_alignment_factor` defaults to 1.0
   - **Result**: reconstruction skips the masked_mean_ratio adjustment that Stage A already has baked in

4. **Phase B.6 test evidence** (pytest_phase_b6_fix.log:37-40):
   - `masked_mean_stage_a = 0.999` (includes masked_mean_ratio from mapping)
   - `masked_mean_reconstruction_cold = 8.377` (missing masked_mean_ratio adjustment)
   - `rel_error = 7.38`, `ratio = 0.119` (1/8.4 mismatch)

## Architecture Insight

The `baseline_alignment_factor` mechanism (reconstruction.py:418-471) was designed to align reconstruction cold path with Stage A's telemetry-recorded `model_mean_masked`. But it has **no fallback** to the original `masked_mean_ratio` from calibration_metadata when telemetry is incomplete.

This is an **architectural coupling issue**: reconstruction cold path should fall back to `calibration_metadata["masked_mean_ratio"]` when telemetry doesn't provide `model_mean_masked`, ensuring consistency with the mapping phase's target-to-bragg alignment.

## The Fix (Phase B.7)

Add elif branch to `baseline_alignment_factor` computation (reconstruction.py:454-467):

```python
elif effective_calibration_metadata is not None and "masked_mean_ratio" in effective_calibration_metadata:
    # ARCH-CONTRACT-002 Phase B.7: Use masked_mean_ratio from mapping phase as fallback
    masked_mean_ratio = effective_calibration_metadata.get("masked_mean_ratio")
    if masked_mean_ratio is not None and masked_mean_ratio > 0 and np.isfinite(masked_mean_ratio):
        baseline_alignment_factor = masked_mean_ratio
        alignment_source = "calibration_masked_mean_ratio"
        print(f"[ARCH-CONTRACT-002 Phase B.7] Cold-path baseline alignment from calibration:")
        print(f"  masked_mean_ratio (from mapping): {masked_mean_ratio:.6e}")
        print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
        print(f"  source: {alignment_source}")
```

**Rationale**: When telemetry doesn't provide `model_mean_masked` (minimal test fixtures, warm-start scenarios with partial telemetry), fall back to the original masked_mean_ratio from `build_mapping_stage_a_context` to maintain target-to-bragg alignment consistency.

## Expected Outcome (Loop i=117)

After Ralph implements the masked_mean_ratio fallback:
- **Warm-cache regression** (Phase A.1): PASS (no code changes, early return still works, rel_error=0.0)
- **Cold-path enforcement** (Phase A.2): PASS with rel_error < 1e-6, ratio ≈ 1.0 (currently 738% error, 8.4× ratio)

**Metrics progression**:
- Phase B.5: 3520% rel_error (double-sqrt bug)
- Phase B.6: 738% rel_error (sqrt fixed, masked_mean_ratio missing)
- Phase B.7: <0.0001% rel_error (full parity achieved)

## Planning Artifacts

- `phase_b7_planning.md` — Full analysis with evidence trail, fix strategy, and ARCH-CONTRACT-002 update
- `input.md` — Detailed implementation instructions for Ralph (lines 454-467 change with elif branch)
- `galph_memory.md` — Loop i=117 state update (DecisionStatus=patch_ready, confidence=0.95)

## Next Steps

- **Loop i=117** (Ralph): Implement masked_mean_ratio fallback, run both enforcement tests, commit artifacts
- **Phase B.8**: Update `docs/findings.md` (SCALE-009 correction documenting Phase B.6-B.7 fixes)
- **Phase C.1**: Run DB-AT-027/028/029 with fixed reconstruction cold path to validate acceptance alignment

## ARCH Contracts Enforced

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment
- **Status**: Phase B.6 partial fix (sqrt), Phase B.7 final fix (masked_mean_ratio)
- **Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (conditional usage established Phase B.6)
- **Enforcement**: `tests/architecture/test_scale_contracts.py` (both warm/cold paths must PASS Phase B.7)

### ARCH-CONTRACT-002: Calibration Metadata Threading & Scaling Pattern
- **Status**: Extended in Phase B.7 with masked_mean_ratio fallback semantics
- **Contract Extension**: masked_mean_ratio from mapping phase must be available as fallback when telemetry lacks complete scaling provenance
- **Owner API**: `dbex.vis.mapping.build_mapping_stage_a_context` (produces and stores masked_mean_ratio)
- **Consumer requirement**: Reconstruction cold path must check `calibration_metadata["masked_mean_ratio"]` when `telemetry.model_mean_masked` unavailable

## Compliance

- ✓ No production edits by Galph (planning only)
- ✓ Evidence→Action contract satisfied (Phase B.6 evidence → exact fix at lines 454-467)
- ✓ Dominant-hypothesis lock enforced (confidence=0.95, no more probes)
- ✓ ARCH conformance remediation planned (masked_mean_ratio fallback pattern documented)
- ✓ Enforcement tests exist and mapped (Phase A.1/A.2 both required to PASS)
- ✓ Findings paydown deferred to Phase B.8 (SCALE-009 update after tests validate)

---

**Commit**: (to be created by Galph after input.md handoff)
**Artifacts**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/`
**Next Actor**: Ralph (loop i=117)
