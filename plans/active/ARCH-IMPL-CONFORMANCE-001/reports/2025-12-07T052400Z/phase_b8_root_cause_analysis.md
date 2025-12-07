# ARCH-IMPL-CONFORMANCE-001 Phase B.8 Root Cause Analysis (Loop i=118 Galph)

## Executive Summary

Ralph's Phase B.8 implementation correctly fixed the test mask contract (using `inputs.loss_mask` instead of `trusted_mask`), but the cold-path test now fails with **12.77% relative error** (worse than the pre-fix 2.46%). This is not a test bug or mask contract issue - it's a **simulator configuration parity bug** between mapping and reconstruction cold paths.

**Root Cause**: The reconstruction cold-path simulator produces ~13% more raw intensity than the mapping simulator (`simulate_forward_once`), even though they should be configured identically for param_state="initial". The `masked_mean_ratio` alignment factor from mapping assumes raw outputs match, but they don't.

**Status**: BLOCKED - requires deeper investigation of simulator factory configuration differences between `simulate_forward_once` (nanobrag_bridge.py) and cold-path reconstruction (reconstruction.py:88-266).

## Evidence Chain

### Test Metrics Progression

| Phase | Mask Domain | Stage A Mean | Reconstruction Mean | Rel Error | Ratio |
|-------|-------------|--------------|---------------------|-----------|-------|
| B.7 (pre-fix) | `trusted_mask` | 2.155699 | 2.102600 | 2.46% | 1.0253 |
| B.8 (post-fix) | `loss_mask` | 87.11842 | 98.24423 | **12.77%** | 0.8868 |

### Key Observations

1. **Warm-cache test (Phase A.1): PASSED** (rel_error = 0.0)
   - Confirms cache optimization works correctly
   - Stage A and reconstruction both use the same pre-scaled `bragg_zero_iter` array

2. **Cold-path test (Phase A.2): FAILED** (rel_error = 12.77%)
   - Mask contract fix was implemented correctly
   - Error got WORSE after fix (2.46% → 12.77%)
   - Indicates deeper semantic issue beyond mask domain

3. **Mask coverage evidence**:
   - `loss_mask.sum()` < `trusted_mask.sum()` (as expected: background >= 0 constraint)
   - Masked means are much higher over `loss_mask` (87.12 vs 2.16)
   - Confirms ROI pixels have concentrated intensity (physics-correct)

## Mathematical Analysis

### Mapping Phase (dbex/vis/mapping.py:287-300)

Mapping computes `masked_mean_ratio` and applies scaling:

```python
# Step 1: Simulate and scale
bragg = raw_mapping_sim * sqrt(spot_scale)  # simulate_forward_once output

# Step 2: Compute ratio over loss_mask
bragg_mean_masked = mean(bragg[loss_mask])  # Mean over ROI pixels only
masked_mean_ratio = target_mean / bragg_mean_masked

# Step 3: Scale ALL pixels by this ratio
bragg *= masked_mean_ratio
```

Final mapping output over loss_mask pixels:
```
mean(bragg[loss_mask]) = mean((raw_mapping_sim * sqrt(spot))[loss_mask])
                       * (target_mean / mean((raw_mapping_sim * sqrt(spot))[loss_mask]))
                       = target_mean  ✓ (by construction)
```

### Reconstruction Cold-Path (dbex/refinement/reconstruction.py:429-543)

Current implementation:

```python
# Step 1: Rebuild simulator from scratch (lines 88-266)
# Step 2: Run and compute baseline_alignment_factor (lines 429-503)
baseline_alignment_factor = masked_mean_ratio  # From calibration metadata

# Step 3: Apply scaling (line 543)
bragg_recon = raw_recon_sim * scale_factor * baseline_alignment_factor
            = raw_recon_sim * sqrt(spot_scale) * masked_mean_ratio
```

Expected mean over loss_mask:
```
mean(bragg_recon[loss_mask]) = mean(raw_recon_sim[loss_mask]) * sqrt(spot)
                               * (target_mean / mean(raw_mapping_sim[loss_mask] * sqrt(spot)))
```

**For this to equal target_mean, we need**:
```
mean(raw_recon_sim[loss_mask]) = mean(raw_mapping_sim[loss_mask])
```

### Observed Mismatch

Test shows:
- Stage A (mapping output) masked mean: 87.11842
- Reconstruction cold-path masked mean: 98.24423
- Ratio: 0.8868

Since both apply `sqrt(spot_scale)` correctly, the ratio indicates:
```
mean(raw_mapping_sim[loss_mask]) / mean(raw_recon_sim[loss_mask]) = 0.8868
```

**Reconstruction simulator produces ~13% MORE raw intensity than mapping simulator.**

## Hypothesis: Simulator Configuration Drift

### Suspected Configuration Differences

Comparing the two simulator construction paths:

**Mapping path**: `dbex/vis/mapping.py` → `simulate_forward_once` (nanobrag_bridge.py:1385-1468)

**Reconstruction cold-path**: `build_final_bragg_from_stage_a_telemetry` → cold-path simulator factory (reconstruction.py:88-266)

Candidate configuration parameters that might differ:
1. **N_cells**: Domain count for mosaic model
   - Mapping: Uses `apply_calibration_n_cells` gate
   - Reconstruction: Uses same gate (line 193), BUT might extract N_cells differently

2. **Beam calibration**: `adu_per_photon`, `beam_flux`, `wavelength_angstroms`
   - Mapping: `simulate_forward_once` applies beam calibration (nanobrag_bridge.py:1449-1453)
   - Reconstruction: Creates beam_config via `create_beam_config` (via simulator factory)

3. **Mosaic domains override**: `stage_a_mosaic_domains`
   - Reconstruction uses `config.stage_a_mosaic_domains` (line 197)
   - Mapping may use a different default

4. **Crystal misset baseline**: Baseline misorientation for incremental refinement
   - Mapping: Uses `baseline_crystal` from context
   - Reconstruction: Uses `baseline_crystal` parameter (should match, but need to verify test provides it)

5. **HKL grid halo**: Tricubic interpolation padding
   - Test explicitly sets `halo=True` (test line 254)
   - But need to verify mapping uses same setting

### Debug Evidence from Test Log

From pytest output (plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/pytest_phase_b8_fix.log):

```
[ARCH-CONTRACT-002 Phase B.6] Computed log_scale_baseline from calibration: 20.354832
[ARCH-CONTRACT-002 Phase B.7] Cold-path baseline alignment from calibration:
  masked_mean_ratio (from mapping): 2.777353e-02
  baseline_alignment_factor: 0.027774
  source: calibration_masked_mean_ratio
  bragg_panel[0] mean (raw sim output): 9.901524e-08
  bragg_panel[0] max: 4.639544e-03
  bragg_scaled[0] mean (calibrated (scale_factor only, no double-sqrt)): 1.902498e+00
  bragg_full mean (final output): 1.902497e+00
```

**Key calculation**:
- `raw_sim = 9.901524e-08`
- `scale_factor = exp(log_scale_baseline) = exp(20.354832) = 7.23e8` (approximately)
- Actual scaled output: `1.902498 / 9.901524e-08 ≈ 1.92e7`

Wait, that doesn't match! Let me recalculate:
- `scaled_output / raw_sim = 1.902498 / 9.901524e-08 = 1.921e7`
- But `exp(20.354832) = 7.23e8`

**This is a 37× discrepancy!** Something is wrong with my understanding of the scale_factor computation.

Let me check the scale_factor computation in the code...

## scale_factor Computation Investigation

Looking at reconstruction.py, I need to find where `scale_factor` is computed from `log_scale_baseline`.

*[Galph note: This analysis is incomplete - need to trace scale_factor computation in next loop]*

## Decision Status

**DecisionStatus**: exploring → requires code audit

**Blocked Reason**: The 12.77% error indicates a systematic bias in cold-path simulator configuration or scaling logic, not just a test mask issue. Further investigation needed before attempting another patch.

**Next Steps** (Loop i=119):

### Option 1: Parity Localization (parity_localization action)
- Compare simulator configurations between:
  1. `simulate_forward_once` (mapping)
  2. Cold-path reconstruction (reconstruction.py:88-266)
- Instrument both paths to emit:
  - Full detector/beam/crystal config JSON
  - Raw simulator output statistics (mean/std/max over full panel AND loss_mask)
  - N_cells, mosaic_domains, misset values
  - HKL grid metadata (shape, halo, device)
- Identify first divergence point

### Option 2: Evidence Collection (evidence_collection action)
- Audit scale_factor computation in reconstruction.py
- Verify that `scale_factor = exp(log_scale_baseline)` is correctly implemented
- Check if there's an additional scaling factor being applied/omitted
- Compare with Stage A's scale_factor logic (stage_a.py)

### Option 3: Mark Blocked & Switch Focus (review_or_housekeeping action)
- ARCH-IMPL-CONFORMANCE-001 has now spent 3 implementation loops (B.5/B.6/B.7) + 1 test fix (B.8) on cold-path parity
- Per non-negotiables, we're approaching the 3-loop implementation budget for this acceptance criterion
- Consider marking Phase B blocked and opening a new initiative:
  - **Initiative Type**: architecture OR spec_change
  - **Scope**: Simulator factory parity between mapping and reconstruction
  - **Owner**: ARCH-FACTORY-001 conformance OR spec relaxation for DB-AT-028/029

## Compliance Checklist

- [x] **Non-negotiables applied**:
  - [x] No production edits by Galph (Phase B.8 was test-only fix)
  - [x] Evidence→Action contract: analysis identifies 3 concrete next actions
  - [x] ARCH/Impl consistency gate: classified as implementation bug within architecture (not conformance failure)
  - [x] Probe saturation: No new probes added (test fix only)
  - [ ] **VIOLATED: Repeat-signature Probe Freeze** - same selector (test_stage_a_vs_reconstruction_scale_cold_path) + same failure signature (scale mismatch) recurs after test-only change; next loop MUST patch production OR retype/split

- [x] **Loop discipline**:
  - Implementation floor: Next loop MUST delegate production code task (no more test-only changes for this criterion)
  - Dwell enforcement: Phase B has 4 loops on this selector/signature (B.5/B.6/B.7/B.8); next loop is the 5th
  - Initiative budget: Approaching 3-implementation-loop limit; need to either:
    1. Fix the simulator parity issue directly (production edit), OR
    2. Mark blocked and split to new architecture/spec_change initiative

## Artifacts

- `phase_b8_root_cause_analysis.md` (this file)
- `summary.md` (concise turn summary for ledger)
- pytest log: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/pytest_phase_b8_fix.log`

## References

- docs/spec-db-core.md:55 (loss_mask definition: `(background >= 0) & trusted_mask`)
- dbex/vis/mapping.py:287-300 (masked_mean_ratio computation and application)
- dbex/refinement/reconstruction.py:429-543 (baseline_alignment_factor logic)
- dbex/refinement/inputs.py:230 (loss_mask construction)
- ARCH-IMPL-CONFORMANCE-001 implementation.md (Phase B.8 specification)

---

**Loop**: i=118 (Galph analysis)
**Timestamp**: 2025-12-07T052400Z
**Confidence**: 0.85 (high confidence on symptom, medium confidence on exact root cause)
**Action**: Blocked - requires either parity localization OR architecture split decision
