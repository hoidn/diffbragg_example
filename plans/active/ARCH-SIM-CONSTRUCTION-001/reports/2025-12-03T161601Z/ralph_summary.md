# ARCH-SIM-CONSTRUCTION-001 Loop 2025-12-03T161601Z — Trusted Mask Threading + Escalation

## Implementation

**Change:** Threaded `inputs.trusted_mask[pid]` into reconstruction cold-path detector config construction (dbex/refinement/reconstruction.py:190-202).

```python
# Thread trusted mask into cold-path detector config (ARCH-SIM-CONSTRUCTION-001)
# When inputs.trusted_mask exists, pass per-panel mask so reconstruction zeros
# untrusted pixels the same way Stage A warm cache does (spec-db-core.md:34,109)
panel_trusted_mask = None
if inputs.trusted_mask is not None:
    panel_trusted_mask = inputs.trusted_mask[pid]

detector_config = create_detector_config(
    detector[pid],
    beam=beam,
    trusted_mask=panel_trusted_mask,
    oversample=3  # Force 3-fold oversampling matching simulate_forward_once
)
```

**Rationale:** Phase C.5 evidence (2025-12-09T210000Z) showed 18% raw output discrepancy between Stage A (1.71e-09) and reconstruction (2.02e-09). Hypothesis: reconstruction cold path doesn't pass trusted masks to simulator factory, causing untrusted pixels to contribute signal.

## Results

### Simulator Comparison Probe

**Command:**
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py \
--detector-size small --device cpu \
--output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/simulator_intensity_metrics.json
```

**Outcome:** **UNCHANGED** — Raw ratios still show 18% discrepancy:
- Stage A / Reconstruction: 0.846821
- Reconstruction / Mapping: 1.180887

**Analysis:** Probe script doesn't exercise the fix. It builds its own `detector_config` at line 250 WITHOUT calling `build_final_bragg_from_stage_a_telemetry`, so the trusted_mask threading code path is never hit.

### DB-AT-028/029 Acceptance Tests

**Command:**
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/db_at_028 \
DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T161601Z/db_at_029 \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
```

**Outcome:** **CATASTROPHIC FAILURE**
- DB-AT-028: chi²/pixel = 2.098e+05 (spec: ≤ 1e2)
- DB-AT-029: median ROI correlation = -0.053 (spec: ≥ 0.2)

**Debug Evidence:**
```
[ARCH-SIM-CONSTRUCTION-001 DEBUG]
  bragg_panel[0] mean (raw sim output): 3.408123e-14
  bragg_scaled[0] mean (after scale_factor): 4.735761e-04
  bragg_full mean (final output): 4.735761e-04
  scale_factor (after exp): 13895512064.0
  sqrt_spot_scale: 691817229.1071362
  spot_scale_override: 4.786110784894759e+17
[END DEBUG]
```

**Analysis:** Raw simulator output is **3.4e-14**, which is ~60,000× smaller than the expected ~2e-9 from prior investigations. This produces:
- Chi² proportional to (model error)², so 10^5 magnitude error → 10^10 chi² error
- Negative correlations due to catastrophically wrong Bragg predictions

## Root Cause Hypotheses

1. **Mask format issue:** If `inputs.trusted_mask[pid]` has wrong shape or dtype, `create_detector_config` may reject it or apply it incorrectly, causing the simulator to zero all pixels or apply wrong masking logic.

2. **Warm vs cold path confusion:** DB-AT-028/029 may be exercising the **warm cache path** (line 156-172), not the cold path where I added mask threading. If so, my change is not being tested.

3. **Trusted mask hypothesis wrong:** The 18% discrepancy may NOT be due to missing masks. Other candidates:
   - HKL grid alignment issues
   - Beam calibration threading mismatch
   - Crystal N_cells application difference
   - Device/dtype mismatch

4. **Factory masking bug:** `create_detector_config` may misinterpret the mask parameter when it's not None, causing simulator construction failure.

## Escalation Rationale

Per Ralph prompt repeat-failure guard:
- Same acceptance criteria (DB-AT-028/029) failed in prior loop (skipped) and this loop (catastrophic failure)
- Failure signature is WORSE (chi² 2e5 vs prior ~1e5, raw output 10^5× smaller)
- Implementation change (trusted mask threading) did not improve situation and may have regressed it

Per initiative type (`architecture`):
- This level of failure suggests spec/design mismatch, not just implementation bug
- Need Galph to reassess root cause hypothesis before further implementation attempts

## Recommended Next Steps (for Galph)

1. **Verify test path:** Confirm whether DB-AT-028/029 use warm cache (line 156) or cold path (line 174). If warm cache, the mask threading at line 193 is never executed.

2. **Inspect mask format:** Check that `inputs.trusted_mask` shape/dtype matches `create_detector_config` expectations (should be [slow, fast] bool array per spec-db-core.md:34).

3. **Revert and probe alternatives:** Consider reverting reconstruction.py:190-202 and testing alternative hypotheses (HKL bounds, beam threading, N_cells) before pursuing mask fix.

4. **Add targeted probe:** Create a probe that actually calls `build_final_bragg_from_stage_a_telemetry` with and without trusted_mask parameter to isolate the effect.

5. **Check factory behavior:** Instrument `create_detector_config` to log when `trusted_mask` parameter is non-None and confirm it's being applied correctly to DetectorConfig.

## Artifacts

- `simulator_intensity_metrics.json` — Probe raw/scaled outputs (unchanged from prior loop)
- `summary.md` — Probe cross-path ratios
- `pytest_db_at_028_029.log` — Full test output with debug instrumentation
- `db_at_028/db_at_028_metrics.json` — DB-AT-028 telemetry and chi² metrics
- `db_at_029/db_at_029_metrics.json` — DB-AT-029 correlation and scale metrics
- `ralph_summary.md` — This document

## Status

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Loop:** 2025-12-03T161601Z
**Outcome:** Blocked — Implementation regression, escalating to Galph for root cause reassessment
**Next:** Galph to investigate warm/cold path usage and mask format compliance before next implementation attempt
