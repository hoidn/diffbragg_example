# ARCH-SIM-CONSTRUCTION-001 — 2025-12-12T010000Z Evidence Collection

## Purpose

This loop collects comprehensive scale diagnostics for DB-AT-028/029 failures after the mask fix. Despite raw simulator parity being achieved in prior loops, the acceptance tests continue to fail with chi²/pixel ≈ 2.1e5 and ROI correlation ≈ -0.05.

## Evidence Collected

### 1. Scale Probe (`scale_probe/`)

**Script:** `probe_stage_a_scale_alignment.py`
**Output:** `scale_probe/stage_a_scale_alignment.json`, `scale_probe/scale_probe_summary.md`

**Key Findings:**
- Mapping path Bragg (zero-iteration):
  - Masked mean: **1.8453 ADU**
  - Unmasked mean: 1.6689 ADU
  - Mask coverage: 90.4%
- Calibration metadata (config_torch_smoke_small.json):
  - `spot_scale_override`: **4.7861e+17**
  - `sqrt(spot_scale)`: **6.9182e+08**
  - `N_cells`: [41, 29, 32]
  - `log_scale_baseline`: None (not present in config)
  - `beam_flux`: 1.0e+12
  - `beam_exposure`: 1.0
  - `beamsize_mm`: 1.0
- RefinementInputs.global_scale_hint: 1.4357

### 2. Simulator Raw Output Parity (`simulator_intensity_metrics.json`)

**Script:** `compare_simulator_outputs.py`
**Output:** `simulator_intensity_metrics.json`, `compare_simulator_outputs.log`

**Key Findings:**
- All three paths produce **identical raw outputs**:
  - Stage A warm-cache: 1.713925e-09 ADU (mean, first panel)
  - Reconstruction cold-path: 1.713925e-09 ADU
  - simulate_forward_once (mapping): 1.713925e-09 ADU
- Raw output ratios:
  - stage_a/recon: **1.000000** ✅
  - stage_a/mapping: **1.000000** ✅
  - recon/mapping: **1.000000** ✅
- After sqrt(spot_scale) scaling, all paths produce ~0.955 ADU

**Interpretation:** Exit criterion #1 (raw intensity parity) remains **SATISFIED**. The construction alignment issue is resolved; remaining DB-AT failures must be due to post-scaling logic, loss computation, or test gate calibration.

### 3. DB-AT-028/029 Test Run (`pytest_db_at_028_029.log`, `db_at_028/`, `db_at_029/`)

**Selectors:** `test_db_at_028_loss_scale_sanity`, `test_db_at_029_structure_parity`
**Artifacts:** `db_at_028_metrics.json`, `db_at_029_metrics.json`, `mapping_context_fixture.json`, `mask_coverage.json`

**Results:**
- **DB-AT-028:** FAILED
  - chi²/pixel initial: **2.098e+05** (spec: ≤ 1e2, FAIL by 2096×)
  - Reconstruction DEBUG output:
    - Raw sim output (first panel): 1.865559e-09 ADU
    - scale_factor (exp(log_scale_baseline + delta)): **1.3896e+10**
    - Scaled output: **25.92 ADU** (vs expected ~1.84 ADU from mapping)
    - Missing factor: 25.92 / 1.84 ≈ **14× too large**

- **DB-AT-029:** FAILED
  - Median ROI correlation before refinement: **-0.053** (spec: ≥ 0.2, FAIL)
  - Same reconstruction output magnitude issue as DB-AT-028

**Key Observation:**
The reconstruction helper produces outputs ~14× too large compared to the mapping baseline (25.92 vs 1.84 ADU). This discrepancy directly explains the chi² and correlation failures.

### 4. Mask Coverage Confirmation

**Artifact:** `db_at_028/mask_coverage.json`, `db_at_029/mask_coverage.json`

- Panel 0 coverage: **90.4%** (well above 50% threshold)
- Mask was injected successfully (no fallback)
- Confirms that prior mask-related fixes are working as intended

### 5. Calibration N_cells Application

**DEBUG output:** `[ARCH-SIM-CONSTRUCTION-001 N_CELLS] N_cells=(41, 29, 32), status=applied`

- N_cells threading is working correctly
- Confirms Phase C.7 fix is intact

## Root Cause Analysis

### Discrepancy Source: `scale_factor` Magnitude

From DEBUG telemetry:
```
log_scale_baseline_value: 20.354832358908794
log_scale (param_deltas_a): 6.890026092529297
scale_factor (after exp): 13895512064.0  # ≈ 1.39e+10
sqrt_spot_scale: 691817229.1071362      # ≈ 6.92e+08
```

Expected scale_factor (from calibration):
- If log_scale_baseline should encode sqrt(spot_scale): exp(20.3548) ≈ 6.92e+08 ✅
- But actual `log_scale + delta` = 20.3548 + 6.89 = **27.245** → exp(27.245) ≈ **6.0e+11** ❌

The **log_scale delta (+6.89)** is incorrectly inflating the scale_factor by ~20× beyond what calibration metadata specifies.

### Suspected Issue

The reconstruction helper's `scale_factor = exp(log_scale_baseline + log_scale_delta)` formula appears to be double-applying or mis-deriving the delta. Possibilities:
1. **log_scale_baseline mismatch:** The baseline value (20.3548) in the reconstruction context does not match what the mapping path would produce (mapping uses zero delta).
2. **Delta derivation bug:** The `log_scale_delta` (+6.89) from Stage-A telemetry may be incorrectly computed or inappropriately added during reconstruction cold-path startup.
3. **Missing delta clamp:** The `delta_bound=3.0` should limit log_scale perturbations to ±3, but observed delta (+6.89) exceeds this by 2.3×.

## Recommendations

1. **Investigate log_scale derivation in Stage-A telemetry:**
   Check `dbex/refinement/stage_a_impl.py` (or wherever Stage-A telemetry is generated) to understand how `log_scale_baseline` and `log_scale_delta` are computed. Verify they align with the calibration metadata (`spot_scale_override`).

2. **Compare mapping vs reconstruction scale paths:**
   The mapping path produces correct outputs (~1.84 ADU); the reconstruction path produces ~14× larger. Add instrumentation to capture the exact `log_scale` values used in both paths at simulation time.

3. **Audit delta_bound enforcement:**
   The `delta_bound=3.0` gate should prevent +6.89 deltas. Check whether the bound is enforced before or after telemetry capture, or if the delta is being accumulated incorrectly across multiple sources.

4. **Consider spec-change initiative:**
   If investigation reveals that the test gates (chi² ≤ 1e2, ROI ≥ 0.2) were derived from miscalibrated baselines or incompatible physics assumptions, this may require a spec-change initiative rather than implementation fixes.

## Files Modified This Loop

- `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py` (new)
- `dbex/refinement/reconstruction.py:350-358` (bugfix: artifact_dir parent-directory logic removed)

## Artifacts

All artifacts live under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T010000Z/`:
- `scale_probe/stage_a_scale_alignment.json`
- `scale_probe/scale_probe_summary.md`
- `scale_probe.log`
- `simulator_intensity_metrics.json`
- `compare_simulator_outputs.log`
- `summary.md` (this file)
- `pytest_db_at_028_029.log`
- `db_at_028/{db_at_028_metrics.json, mapping_context_fixture.json, mask_coverage.json}`
- `db_at_029/{db_at_029_metrics.json, mapping_context_fixture.json}`

## Status

**Exit Criteria:**
1. ✅ Raw simulator parity achieved (1.000000 ratio across all paths)
2. ❌ DB-AT-028: chi²/pixel = 2.098e+05 (spec ≤ 1e2, FAIL)
3. ❌ DB-AT-029: median ROI corr = -0.053 (spec ≥ 0.2, FAIL)

**Next Action:**
Escalate to supervisor (Galph) with root-cause hypothesis: reconstruction helper's `log_scale_delta` derivation or application is inflating outputs by ~14× beyond calibration-specified scale. Recommend either:
- Diagnostics initiative to instrument log_scale telemetry paths and trace delta sources, or
- Spec-change initiative if gates themselves are inconsistent with current calibration/physics model.
