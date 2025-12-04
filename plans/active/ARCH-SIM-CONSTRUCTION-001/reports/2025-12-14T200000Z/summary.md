# ARCH-SIM-CONSTRUCTION-001 Phase C.10 Implementation Summary

## Turn Summary
Implemented mask provenance tracking to enable verification that Stage A and reconstruction use identical loss masks. Baseline probe confirms mask checksum PASS (both paths use 6305df21a223636fe1f82f9c00f9041e7def78a0). DB-AT-028/029 tests still FAIL (chi²=2.1e5, ROI corr=-0.054) but mask metadata now proves the failure is NOT due to mask mismatch. Next action: escalate to supervisor with evidence that mask parity is satisfied but underlying intensity/scale issue persists.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/

## Implementation Details

### Changes Made

1. **dbex/refinement/stage_a.py**:
   - Added `hashlib` import
   - Computed mask provenance in `_build_stage_a_params` (lines 511-538):
     - Total pixel count (`loss_mask_pixel_count`)
     - Per-panel true pixel counts
     - SHA1 checksum of mask array
   - Added `mask_metadata` to `param_values` dict (line 548)
   - Extracted `mask_metadata` from `param_values` in `run` method (line 1782)
   - Attached `mask_metadata` to `RefinementTelemetry` (line 2068)

2. **dbex/refinement/stage.py**:
   - Added `mask_metadata: Optional[Dict[str, Any]] = None` field to `RefinementTelemetry` dataclass (line 160)
   - Added mask_metadata serialization to `to_dict()` method (lines 259-260)

3. **dbex/refinement/reconstruction.py**:
   - Added `hashlib` import
   - Computed reconstruction mask metadata and extracted telemetry mask metadata (lines 526-558):
     - Computed reconstruction mask checksum
     - Extracted telemetry mask metadata if available
     - Compared checksums and emitted warning if mismatch detected
   - Added `mask_metadata` section to `baseline_stats` dict (lines 584-588):
     - telemetry mask metadata
     - reconstruction mask metadata
     - checksum_mismatch boolean flag

4. **plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py**:
   - Extracted telemetry mask metadata (lines 339-342)
   - Computed reconstruction mask metadata and compared checksums (lines 344-362)
   - Added `mask_metadata` to output JSON (lines 407-411)
   - Added console table showing mask parity comparison (lines 448-470):
     - Source (Telemetry vs Reconstruction)
     - Pixel count
     - SHA1 checksum
     - PASS/FAIL verdict

### Validation Results

**Baseline Probe** (`compare_stage_a_baseline.py`):
```
Mask Provenance Comparison:
  Source               Pixel Count     Checksum (SHA1)
  -------------------- --------------- --------------------------------------------------
  Telemetry            4140            6305df21a223636fe1f82f9c00f9041e7def78a0
  Reconstruction       4140            6305df21a223636fe1f82f9c00f9041e7def78a0
  -------------------- --------------- --------------------------------------------------
  Mask Checksum Match: PASS
```

**DB-AT-028 baseline_stats.json** (first entry):
```json
{
  "mask_metadata": {
    "telemetry": {
      "loss_mask_pixel_count": 4140,
      "panel_true_pixels": [24, 24, 24, ...],
      "mask_checksum": "6305df21a223636fe1f82f9c00f9041e7def78a0"
    },
    "reconstruction": {
      "loss_mask_pixel_count": 4140,
      "mask_checksum": "6305df21a223636fe1f82f9c00f9041e7def78a0"
    },
    "checksum_mismatch": false
  }
}
```

**Test Outcomes**:
- DB-AT-028: FAILED (chi²/pixel initial=2.097e+05, exceeds 1e2 bound)
- DB-AT-029: FAILED (median ROI corr before=-0.054, below 0.2 floor)
- Mask checksums: MATCH in all cases (no mismatch warnings)

### Key Findings

1. **Mask Parity Confirmed**: Both Stage A telemetry and reconstruction use identical loss masks (checksum 6305df21a223636fe1f82f9c00f9041e7def78a0, 4140 true pixels)

2. **Test Failures Persist**: Despite mask parity, DB-AT-028/029 continue to fail with same signatures as previous loops:
   - Chi²/pixel ~2.1e5 (spec: ≤1e2)
   - ROI correlation ~-0.05 (spec: ≥0.2)

3. **Baseline Scale Discrepancy**: Reconstruction DEBUG output shows:
   - Telemetry `model_mean_masked` = 11.57 ADU
   - Reconstructed `bragg_mean_masked` (initial) = 1.24 ADU (from telemetry replay)
   - Ratio = 0.107 (10.7% of expected)
   - This suggests the scale_factor derivation or application is still incorrect

### Next Actions

Per repeat-failure guard and initiative-type constraints (architecture initiative cannot change gates/specs), recommend supervisor review:

1. **Mask parity hypothesis**: RULED OUT — checksums match exactly
2. **Remaining hypotheses**:
   - Scale_factor derivation in Stage A telemetry includes unintended factors
   - Reconstruction telemetry replay applies scale incorrectly
   - Test fixture baseline computation uses different parameters than Stage A

3. **Escalation**: Mark ARCH-SIM-CONSTRUCTION-001 for supervisor analysis with evidence:
   - Mask provenance: SATISFIED
   - Intensity parity (Phase C.5-C.8): NOT SATISFIED
   - Test gates: architecture initiative cannot adjust without spec-change
