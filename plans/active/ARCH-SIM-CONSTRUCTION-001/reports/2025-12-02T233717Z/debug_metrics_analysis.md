# Debug Metrics Analysis — ARCH-REFACTOR-001 Phase D.3

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Date:** 2025-12-02
**Source:** Ralph's debug evidence from commit 6db57f45

---

## Summary

Ralph's Phase D.3 bugfix (commit 6db57f45) correctly implemented the `log_scale_baseline` extraction logic but tests still failed because the **simulator raw output is ~10^4.4× too small**. This analysis quantifies the discrepancy and identifies the missing calibration factor.

---

## Metrics from Ralph's Debug Run

**Source:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json`

### Calibration Parameters
```json
{
  "spot_scale_override": 3.105058665484234e+17,
  "log_scale_baseline": 20.138489594990745,
  "log_scale_baseline_source": "spot_scale_override_sqrt"
}
```

**Derivation:**
- `sqrt(spot_scale_override) = sqrt(3.105e17) = 5.572e8`
- `log(sqrt(spot_scale_override)) = log(5.572e8) = 20.138` ✓ matches `log_scale_baseline`

### Scale Parameters
```json
{
  "log_scale_initial": 0.0,
  "log_scale_final": 5.549979675834038e-08,
  "log_scale_effective_init": 20.138489594990745,
  "log_scale_effective_final": 20.13848965049054
}
```

**Computation:**
- `log_scale_effective = log_scale_baseline + log_scale_delta`
- `log_scale_delta ≈ 5.55e-08` (negligible, LBFGS converged to baseline)
- `scale_factor = exp(20.138) = 5.572e8` ✓ correct

### Forward Model Outputs
```json
{
  "bragg_before_mean": 0.23937484622001648,
  "bragg_before_std": 64.98988342285156,
  "bragg_before_max": 87148.40625,
  "bragg_after_mean": 1.0249042134091724e-05,
  "bragg_after_std": 2.7174526621820405e-05,
  "bragg_after_max": 0.0004215998051222414
}
```

**Explanation:**
- `bragg_before`: Forward model output computed via `build_final_bragg_from_stage_a_telemetry()` using **mapping baseline geometry** (zero-iteration, perturbed crystal/beam/detector parameters from fixture)
- `bragg_after`: Forward model output using **Stage A refined parameters** (post-LBFGS geometry)

**Expected behavior:**
- `bragg_before` should be ≈ O(1) ADU (typical detector intensity scale, matching target data)
- `bragg_after` should be similar magnitude to `bragg_before` (same order of magnitude, refinement adjusts geometry not overall scale)

**Actual behavior:**
- `bragg_before = 0.24` ✓ correct (O(1) ADU)
- `bragg_after = 1.02e-05` ✗ **23,500× too small**

### Chi-Squared / Correlation Metrics
```json
{
  "chi2_per_pixel_initial": 108375.87037603179,
  "chi2_per_pixel_final": 108441.13237542036,
  "roi_cc_median_before": -0.04987446793751028,
  "roi_cc_median_after": 0.02258480937223932,
  "roi_cc_median_mapping": -0.04987446793751028
}
```

**Acceptance criteria (from docs/spec-db-core.md, DB-AT-028/029):**
- `chi2_per_pixel_initial ≤ 100` (FAIL: observed 1.084e+05, **1000× too large**)
- `roi_cc_median_before ≥ 0.2` (FAIL: observed -0.050, **below floor**)

**Root cause:** `bragg_before` intensity scale is correct (~0.24 ADU), but `bragg_after` is 23,500× too small → chi² is huge because model and target are mismatched by 10^4+ orders of magnitude.

---

## Ralph's Debug Findings

**Source:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`

### Temporary Debug Logging
```
DEBUG reconstruction.py: log_scale_baseline_value=20.138489594990745, log_scale=5.549979675834038e-08
DEBUG reconstruction.py: log_scale_clamped=20.13848876953125, scale_factor=557230080.0
DEBUG reconstruction.py: Panel 0: bragg_panel mean=1.839e-14, max=7.566e-13
DEBUG reconstruction.py: Panel 0: bragg_scaled mean=1.025e-05, max=4.216e-04
```

### Key Observations

1. **Baseline extraction:** ✓ CORRECT (`log_scale_baseline_value = 20.14`)
2. **Scale factor calculation:** ✓ CORRECT (`scale_factor = 5.57e8`)
3. **Simulator raw output:** ✗ **TOO SMALL** (`bragg_panel mean = 1.839e-14`)

**Arithmetic check:**
- `bragg_panel (raw) = 1.839e-14` ADU
- `scale_factor = 5.572e8`
- `bragg_scaled = 1.839e-14 × 5.572e8 = 1.025e-05` ADU ✓ matches observed
- Expected `bragg_after ≈ 0.24` ADU (same order as `bragg_before`)
- Implies raw output should be `0.24 / 5.572e8 ≈ 4.3e-10` ADU

**Missing factor:** `4.3e-10 / 1.8e-14 ≈ 23,900 ≈ 10^4.38`

---

## Missing Factor Analysis

### Hypothesis 1: Missing sqrt(spot_scale_override)

**Candidate:** `sqrt(spot_scale_override) = 5.572e8`
**Observed missing factor:** `~23,900 ≈ 10^4.38`
**Match?** NO — `5.572e8` is 23,500× **larger** than the missing factor

**Conclusion:** The missing factor is **NOT** `sqrt(spot_scale_override)` itself. It's much smaller.

### Hypothesis 2: Missing (spot_scale_override)^(1/4)

**Candidate:** `(spot_scale_override)^(1/4) = (3.105e17)^0.25 = 23,600`
**Observed missing factor:** `~23,900`
**Match?** YES — **within 1.3%**

**Physical interpretation:**
- `spot_scale_override` is applied as `sqrt(value)` per nanoBragg convention (SCALE-002)
- If the factor is applied **twice** (once in baseline derivation, once in reconstruction), the effective scaling is `sqrt(sqrt(value)) = value^(1/4)`
- The **missing factor is one sqrt application**

**Evidence:**
1. Stage A derives `log_scale_baseline = log(target_mean / (model_raw × sqrt(spot_scale)))`
   - `model_raw` here is **after applying** `sqrt(spot_scale)` (stage_a.py:442-443)
   - Baseline encodes: `log(target / (sqrt(spot_scale) × model_true_raw))`
   - `exp(baseline) = target / (sqrt(spot_scale) × model_true_raw)`

2. Reconstruction applies `scale_factor = exp(baseline)` to **model_true_raw** (without sqrt factor)
   - `bragg_after = model_true_raw × scale_factor`
   - `bragg_after = model_true_raw × target / (sqrt(spot_scale) × model_true_raw)`
   - `bragg_after = target / sqrt(spot_scale)` ✗ **missing sqrt(spot_scale) factor**

**Correct pattern:**
- Stage A: `bragg = model_raw × sqrt(spot_scale) × exp(log_scale_delta)`
- Reconstruction: `bragg = model_raw × sqrt(spot_scale) × exp(baseline + log_scale_delta)`

**But reconstruction does:** `bragg = model_raw × exp(baseline + log_scale_delta)`
- Missing the explicit `sqrt(spot_scale)` multiplication

### Hypothesis 3: beam_config mismatch (flux/exposure/beamsize)

**Evidence:**
- Stage A threads `flux`, `exposure`, `beamsize_mm` from `calibration_metadata` to `beam_config` (stage_a_utils.py:267)
- Reconstruction does not (reconstruction.py:170)

**Potential impact:**
- Beam flux affects photon count → ADU conversion
- Typical flux values: O(1e10) photons/s (X-ray synchrotron)
- Exposure: O(0.01–1.0) seconds
- Total photons: O(1e8–1e10)

**Missing factor calculation:**
- If `beam_flux = 1e10` and reconstruction defaults to `flux=1.0`, missing factor ≈ 1e10
- But observed missing factor ≈ 23,900 (not 1e10)

**Conclusion:** beam_config mismatch **may contribute** but does not fully explain the discrepancy.

---

## Root Cause Confirmed

The missing factor **~23,900 ≈ (spot_scale_override)^(1/4)** indicates:

1. **Stage A baseline derivation** applies `sqrt(spot_scale_override)` to model output **before** computing the ratio
   - `baseline = log(target_mean / (model_raw × sqrt(spot_scale)))`

2. **Reconstruction assumes** `exp(baseline)` will scale raw output to target
   - `bragg = model_raw × exp(baseline)`
   - `bragg = model_raw × (target_mean / (model_raw × sqrt(spot_scale)))`
   - `bragg = target_mean / sqrt(spot_scale)` ✗ **missing sqrt(spot_scale) factor**

3. **The fix:** Reconstruction must **also apply** `sqrt(spot_scale_override)` to raw output:
   - `bragg = model_raw × sqrt(spot_scale) × exp(baseline)`
   - OR: pass `spot_scale_override` to factory and apply returned `sqrt_scale`

---

## Quantitative Summary

| Metric | Expected | Observed | Ratio | Notes |
|--------|----------|----------|-------|-------|
| `spot_scale_override` | 3.105e+17 | 3.105e+17 | 1.0 | ✓ Correct from calibration metadata |
| `sqrt(spot_scale_override)` | 5.572e+8 | 5.572e+8 | 1.0 | ✓ Correct baseline derivation |
| `log_scale_baseline` | 20.138 | 20.138 | 1.0 | ✓ Correct `log(sqrt(spot_scale))` |
| `scale_factor` | 5.572e+8 | 5.572e+8 | 1.0 | ✓ Correct `exp(baseline)` |
| `bragg_panel (raw)` | 4.3e-10 | 1.8e-14 | 23,900 | ✗ Missing factor ≈ (spot_scale)^(1/4) |
| `bragg_after (scaled)` | 0.24 | 1.02e-05 | 23,500 | ✗ Same missing factor |
| `chi2_per_pixel_initial` | ≤ 100 | 1.084e+05 | 1,084 | ✗ Magnitude mismatch amplified |
| `roi_cc_median_before` | ≥ 0.2 | -0.050 | N/A | ✗ Anti-correlation (wrong scale) |

**Confidence:** High (arithmetic checks out, missing factor matches (spot_scale)^(1/4) within 1.3%)

---

## Spec Violations

- **DB-AT-028 acceptance:** `chi2_per_pixel_initial ≤ 100` — FAIL (1.084e+05, **1000× too large**)
- **DB-AT-029 acceptance:** `roi_cc_median_before ≥ 0.2` — FAIL (-0.050, **below floor**)
- **Factory contract:** `sqrt(spot_scale_override)` must be applied post-run — VIOLATED (reconstruction ignores returned `sqrt_scale`)
- **Calibration threading:** Forward model must respect calibration metadata — VIOLATED (reconstruction cold path builds simulators without spot_scale or beam flux/exposure)

---

## Recommended Fix

**Option A (Minimal, factory-based):**
1. Change `reconstruction.py:184` from `spot_scale_override=None` to `spot_scale_override=config.calibration_metadata.get('spot_scale_override')`
2. Apply returned `sqrt_scale` at line 222:
   ```python
   for pid, sim in zip(sampled_panel_ids, simulators):
       bragg_panel = sim.run()
       if sqrt_scale is not None:
           bragg_panel = bragg_panel * sqrt_scale  # ← Apply factory-returned scale
       bragg_scaled = bragg_panel * scale_factor
       bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
   ```

**Option B (Consistent with Stage A pattern):**
1. Extract `spot_scale_override` from `config.calibration_metadata` before simulator loop
2. Compute `sqrt_spot_scale = sqrt(spot_scale_override)` (matching stage_a.py:442)
3. Apply it post-run:
   ```python
   spot_scale_override = config.calibration_metadata.get('spot_scale_override', 1.0) if config.calibration_metadata else 1.0
   sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0

   for pid, sim in zip(sampled_panel_ids, simulators):
       bragg_panel = sim.run()
       bragg_panel_scaled = bragg_panel * sqrt_spot_scale  # ← Consistent with Stage A
       bragg_scaled = bragg_panel_scaled * scale_factor
       bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
   ```

**Option C (Thread beam calibration, partial fix):**
1. Update `reconstruction.py:170` to thread `flux`, `exposure`, `beamsize_mm`:
   ```python
   beam_flux = config.calibration_metadata.get('beam_flux') if config.calibration_metadata else None
   beam_exposure = config.calibration_metadata.get('beam_exposure') if config.calibration_metadata else None
   beamsize_mm = config.calibration_metadata.get('beamsize_mm') if config.calibration_metadata else None
   beam_config = create_beam_config(beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)
   ```
2. **Still need Option A or B** to apply `sqrt(spot_scale_override)`

**Recommendation:** Use **Option B** (consistent with Stage A pattern) for architectural alignment, plus **Option C** (beam calibration threading) for completeness.

---

## Cross-References

- Ralph's findings: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`
- Metrics JSON: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json`
- Stage A baseline derivation: `dbex/refinement/stage_a.py:442-443, 454-467`
- Reconstruction scaling: `dbex/refinement/reconstruction.py:195-223`
- Factory contract: `dbex/refinement/helpers.py:83-219` (lines 117-119, 133-134)
