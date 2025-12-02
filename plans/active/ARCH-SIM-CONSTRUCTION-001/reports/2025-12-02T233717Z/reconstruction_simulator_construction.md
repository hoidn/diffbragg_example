# Reconstruction Simulator Construction Analysis

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Date:** 2025-12-02
**Focus:** How `build_final_bragg_from_stage_a_telemetry` constructs simulators and applies calibration

---

## Summary

The reconstruction helper `build_final_bragg_from_stage_a_telemetry()` supports **both warm and cold paths** for simulator construction. When warm cache is available (`stage_a_ctx` is not None), it reuses Stage A's cached simulators via retargeting. When cold, it builds fresh simulators via `create_unified_simulator()` factory.

**Critical finding:** In the cold path (lines 167-190), the factory is called with **`spot_scale_override=None`** (line 184), and the returned `sqrt_scale` value is **ignored** (the factory computes it but reconstruction does not use it). Instead, scaling is handled entirely via the `log_scale` parameter extracted from Stage A telemetry (lines 195-217).

This differs from Stage A's pattern, where `sqrt(spot_scale_override)` is directly multiplied against raw simulator output. Reconstruction assumes the factory will "handle" scaling internally, but the factory **returns sqrt_scale for the caller to apply** — and reconstruction doesn't apply it.

---

## Factory Call Site (Cold Path)

**Function:** `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry()`
**Lines:** 167-190 (cold path simulator construction)
**Called from:** Test fixtures / mapping helpers when `stage_a_ctx=None`

### Cold Path Factory Call

```python
# Lines 167-190
else:
    # Cold path: build simulators via unified factory (ARCH-FACTORY-001 Phase B.4)
    from dbex.refinement.config_factories import create_beam_config
    from dbex.refinement.helpers import create_unified_simulator
    beam_config = create_beam_config(beam)
    simulators = []
    for pid in sampled_panel_ids:
        detector_config = create_detector_config(detector[pid], beam=beam)
        # Use unified factory for forward-only reconstruction (ARCH-FACTORY-001)
        # Note: spot_scale_override is NOT passed here - it's handled via log_scale baseline
        # in the scale_factor calculation below (see lines 195-217)
        simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(
            detector_config=detector_config,
            crystal_config=crystal_config,
            beam_config=beam_config,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            mask_array=None,  # mask already in detector_config if needed
            spot_scale_override=None,  # ← CRITICAL: Scale handled via log_scale parameter
            device=device,
            dtype=dtype,
            calibration_metadata=getattr(config, 'calibration_metadata', None),
        )
        simulator.interpolate = config.enable_hkl_interpolation
        simulators.append(simulator)
```

**Arguments passed to `create_unified_simulator`:**
- `detector_config`: per-panel DetectorConfig
- `crystal_config`: CrystalConfig with refined parameters from Stage A telemetry
- `beam_config`: BeamConfig (no flux/exposure/beamsize threaded from calibration_metadata)
- `hkl_grid`, `hkl_metadata`: structure factor grid
- `mask_array=None` (mask already in detector_config)
- **`spot_scale_override=None`** ← **BUG: Should pass `calibration_metadata['spot_scale_override']`**
- `device`, `dtype`: target device/dtype
- `calibration_metadata`: threaded from config (contains `spot_scale_override`, but **not used by factory for scaling**)

**Return value:**
```python
simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(...)
```

- `simulator`: nanobrag_torch.Simulator instance (raw, no scaling applied internally)
- `normalized_mask`: mask tensor (not used in this code path)
- `sqrt_scale`: **sqrt(spot_scale_override)** if it were provided, else **None** ← **IGNORED by reconstruction**
- `metadata`: dict with factory validation info (not used)

---

## Factory Contract (What Should Happen)

**File:** `dbex/refinement/helpers.py::create_unified_simulator()`
**Lines:** 83-219

### Factory Logic for `spot_scale_override`

```python
# Lines 183-187
# Compute sqrt_scale for post-run application (per SCALE-004)
sqrt_scale = None
if spot_scale_override is not None:
    import math
    sqrt_scale = math.sqrt(spot_scale_override)
```

**Factory does NOT apply scaling to simulator:** It computes `sqrt_scale` and **returns it for the caller to apply post-run** (line 142 docstring: "sqrt_scale is computed here but applied by CALLER after simulator.run()").

**Factory contract (lines 117-119):**
```
spot_scale_override : Optional[float]
    Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)
    per SCALE-004 finding.
```

**Return value (lines 133-134):**
```
sqrt_scale : Optional[float]
    sqrt(spot_scale_override) to apply post-run, else None.
```

---

## Post-Run Scaling Application (Reconstruction)

**File:** `dbex/refinement/reconstruction.py`
**Lines:** 195-223

```python
# Lines 195-217: Extract log_scale_baseline and compute scale_factor
log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')

max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal

if log_scale_baseline_value is not None:
    # Calibrated path: add baseline to clamped delta
    log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
    log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
    log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
else:
    # Uncalibrated path: clamp absolute log_scale (legacy behavior)
    log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

scale_factor = torch.exp(log_scale_clamped)

# Lines 220-223: Apply scale_factor to raw simulator output
for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()
    bragg_scaled = bragg_panel * scale_factor  # ← ONLY SCALE FACTOR APPLIED
    bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**Scaling logic:**
1. Extract `log_scale_baseline_value` from Stage A telemetry (`param_deltas_a`)
2. If baseline exists (calibrated run):
   - `scale_factor = exp(log_scale_baseline + log_scale_delta)`
   - Where `log_scale_baseline ≈ log(sqrt(spot_scale_override))` (from Stage A)
3. Multiply raw simulator output by `scale_factor`

**Problem:** This pattern assumes:
- `log_scale_baseline = log(sqrt(spot_scale_override))`
- `scale_factor = exp(log(sqrt(spot_scale_override))) = sqrt(spot_scale_override)`

But this only holds if **Stage A stored the correct baseline** and **the simulator output already has the correct raw magnitude**. If the simulator was built with `spot_scale_override=None`, the raw output will be ~10^4.4× too small (missing the `sqrt(spot_scale_override)` factor that Stage A applies during training).

---

## Warm Path (Reuse Stage A Simulators)

**Lines:** 149-165

```python
# Warm cache path: retarget existing simulators with refined crystal
if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
    crystal_model = Crystal(
        crystal_config,
        beam_config=stage_a_ctx.beam_config,  # FIXED: pass beam_config at construction time
        device=device,
        dtype=dtype,
    )
    crystal_model.interpolate = config.enable_hkl_interpolation
    crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
    crystal_model.hkl_metadata = hkl_metadata

    from dbex.refinement.stage_a_utils import _retarget_stage_a_simulators
    _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
    simulators = stage_a_ctx.simulators
```

**Pattern:** Reuse the same `Simulator` objects that Stage A built (with the same `detector`, `beam_config`, device/dtype). Update only the `crystal` parameters via retargeting.

**Key observation:** If Stage A simulators were built **without spot_scale_override embedded**, then warm-path reconstruction will also have raw outputs that are ~10^4.4× too small — **but Stage A training compensates by applying `sqrt(spot_scale_override)` post-run**. Reconstruction applies `scale_factor = exp(log_scale_baseline)` post-run, which **should be equivalent** to `sqrt(spot_scale_override)` if the baseline was derived correctly.

**Hypothesis:** Warm path **should work correctly** if Stage A telemetry stores the right `log_scale_baseline`. The issue is in the **cold path**, where simulators are built fresh without `spot_scale_override` and the factory-returned `sqrt_scale` is ignored.

---

## Telemetry Structure (Stage A → Reconstruction)

**Input:** `param_deltas_a` dict from Stage A telemetry

**Expected structure:**
```python
param_deltas_a = {
    'log_scale_baseline': {'final': 20.138489594990745},  # ← log(sqrt(3.1e17)) ≈ 20.14
    'log_scale': {'final': 5.55e-08},  # ← small delta (~0)
    'orientation_vec': {'final': [...]},
    'log_cell_a_delta': {'final': ...},
    # ...
}
```

**Actual usage in reconstruction:**
```python
log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')
# Result: 20.138489594990745 ✓ CORRECT
```

**Problem:** `log_scale_baseline` is derived from `sqrt(spot_scale_override)` in Stage A, but the reconstruction helper **does not verify that the simulators were built consistently**. If reconstruction builds simulators with `spot_scale_override=None`, the raw output will not match Stage A's expectation.

---

## Key Findings

1. **Cold path bug:** `create_unified_simulator(..., spot_scale_override=None, ...)` is called at line 184, but the factory expects the **caller to apply** the returned `sqrt_scale` post-run. Reconstruction ignores this return value.

2. **Factory contract violation:** The factory docstring (lines 117-119) explicitly states:
   > "Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)"

   But reconstruction does not apply the returned `sqrt_scale`. Instead, it relies on `scale_factor = exp(log_scale_baseline)`, which **assumes the baseline was derived from the same simulator raw output magnitude**.

3. **Missing calibration threading:** The factory receives `calibration_metadata` (line 187) but **does not extract `spot_scale_override` from it**. The caller must pass `spot_scale_override` explicitly (line 184), which reconstruction does not do.

4. **Warm path likely correct:** When `stage_a_ctx` is provided, reconstruction reuses Stage A's simulators (which were built the same way — no `spot_scale_override` at construction). Both paths apply post-run scaling via `exp(log_scale)`, so parity should hold **if the baseline is correct**.

5. **Test fixture issue:** The failing tests (`DB-AT-028`, `DB-AT-029`) likely build `bragg_before` via the **cold path** (no `stage_a_ctx` available in fixture), hitting the bug where `spot_scale_override=None` produces raw output ~10^4.4× too small.

---

## Root Cause Confirmed

The reconstruction helper violates the factory contract:
- **What it does:** Pass `spot_scale_override=None`, ignore returned `sqrt_scale`, rely on `scale_factor = exp(log_scale_baseline)`
- **What it should do:** Pass `spot_scale_override=calibration_metadata['spot_scale_override']`, OR apply returned `sqrt_scale` post-run

The missing factor (~23,900 ≈ 10^4.38) does **not match** `sqrt(spot_scale_override) = 5.57e8`. This suggests the issue is **NOT simply missing sqrt_scale application**, but rather a **double-baseline problem**:
- Stage A derives `log_scale_baseline = log(sqrt(spot_scale_override))` from raw simulator output (which is ~1e-14 ADU)
- Reconstruction assumes `exp(log_scale_baseline)` will scale raw output (~1e-14 ADU) to match target (~0.24 ADU)
- But the baseline is stored as ~20.14, and `exp(20.14) ≈ 5.57e8`, which would give `1e-14 × 5.57e8 = 5.6e-6` (still 40× too small!)

**Wait, the metrics show:**
- `bragg_after_mean = 1.02e-05` (reconstruction output after scaling)
- `bragg_before_mean = 0.24` (mapping baseline, expected target)
- Missing factor: `0.24 / 1.02e-05 ≈ 23,500` ≈ 10^4.37

So the issue is that reconstruction produces outputs ~23,500× too small even **after** applying `scale_factor = exp(20.14)`.

**Revised hypothesis:** Stage A's `log_scale_baseline` is computed from **scaled** simulator output (after applying `sqrt(spot_scale_override)`), not from **raw** output. So:
- Stage A: `baseline = log(target_mean / (model_raw × sqrt(spot_scale)))` — includes the sqrt factor
- Reconstruction: `scale = exp(baseline) = target_mean / (model_raw × sqrt(spot_scale))`
- But reconstruction's `model_raw` is from a simulator built **without** `sqrt(spot_scale)` applied during construction

**The fix:** Pass `spot_scale_override` to the factory so the simulator knows to apply it, OR manually apply `sqrt_scale` after `simulator.run()` in reconstruction.

---

## Spec Citations

- **docs/spec-db-core.md §§20-40:** Calibration contracts — forward model helpers must reproduce Stage A's intensity scale
- **docs/architecture/calibration_scaling.md:** Factory contract — `create_unified_simulator` returns `sqrt_scale` for caller to apply
- **SCALE-004 (findings):** Post-run application pattern — `sqrt(spot_scale_override)` must be multiplied against raw Bragg intensities
- **ARCH-FACTORY-001:** Unified factory adoption — reconstruction should use factory consistently with Stage A conventions

---

## Cross-References

- Factory implementation: `dbex/refinement/helpers.py::create_unified_simulator()` lines 83-219
- Stage A simulator construction: `dbex/refinement/stage_a_utils.py::_build_stage_a_context()` lines 177-376 (does NOT use factory, builds Simulator directly)
- Reconstruction helper: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry()` lines 25-225
- Ralph's debug evidence: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`
