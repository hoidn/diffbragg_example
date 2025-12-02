# Factory Call Comparison: Stage A vs Reconstruction

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Date:** 2025-12-02
**Focus:** Side-by-side comparison of simulator construction conventions

---

## Summary

Stage A and reconstruction use **different patterns** for building simulators:
- **Stage A:** Directly instantiates `Simulator` class (no factory), applies `sqrt(spot_scale_override)` post-run
- **Reconstruction (cold path):** Uses `create_unified_simulator()` factory with `spot_scale_override=None`, ignores returned `sqrt_scale`, relies on `exp(log_scale_baseline)` scaling

**Key mismatch:** Neither path passes `spot_scale_override` to the simulator constructor (because the `Simulator` class doesn't accept it), but Stage A **consistently applies** `sqrt(spot_scale_override)` post-run during training, while reconstruction assumes the factory or `log_scale_baseline` handles it — leading to a magnitude discrepancy.

---

## Comparison Table

| Aspect | Stage A (Training) | Reconstruction Helper (Cold Path) |
|--------|-------------------|----------------------------------|
| **File:Line** | `stage_a_utils.py:309-316` | `reconstruction.py:177-190` |
| **Factory used?** | No — direct `Simulator(...)` instantiation | Yes — `create_unified_simulator(...)` |
| **spot_scale_override arg** | N/A (not a Simulator parameter) | `spot_scale_override=None` (line 184) |
| **calibration_metadata arg** | Threaded to `_build_stage_a_context()` but **not used in Simulator construction** | Threaded to factory (line 187) but **not extracted for `spot_scale_override` parameter** |
| **gain arg** | Not used (Simulator doesn't accept it) | Not used (Simulator doesn't accept it) |
| **sigma arg** | Not used (Simulator doesn't accept it) | Not used (Simulator doesn't accept it) |
| **beam_config** | Created from dxtbx Beam + optional `flux`, `beamsize_mm`, `exposure` from `calibration_metadata` (stage_a_utils.py:267) | Created from dxtbx Beam **without** flux/beamsize/exposure (reconstruction.py:170) |
| **Warm/Cold path** | Warm cache (default): simulators built once, reused | Cold path: simulators rebuilt per call (no cache) |
| **Post-run scaling** | `bragg_stack * sqrt(spot_scale_override)` applied **every time** simulator.run() is called (stage_a.py:442-443, 1422+) | `bragg_panel * scale_factor` where `scale_factor = exp(log_scale_baseline)` (reconstruction.py:222) |
| **Factory return value** | N/A (no factory used) | Returns `(simulator, mask, sqrt_scale, metadata)` but **`sqrt_scale` is ignored** |
| **Baseline derivation** | Computed from `log(sqrt(spot_scale_override))` or from ratio of target/model means after applying sqrt factor (stage_a.py:255-262, 454-467) | **Assumed to exist** in Stage A telemetry; no independent derivation |

---

## Detailed Findings

### 1. Simulator Constructor Arguments

**Stage A (direct instantiation):**
```python
# dbex/refinement/stage_a_utils.py:309-316
simulator = Simulator(
    detector=detector_model,      # per-panel Detector model
    crystal=base_crystal_model,   # shared Crystal model with HKL grid
    beam_config=beam_config,      # from create_beam_config(beam, flux=..., exposure=..., beamsize_mm=...)
    device=device,
    dtype=dtype,
)
```

**Reconstruction (factory call):**
```python
# dbex/refinement/reconstruction.py:177-190
simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(
    detector_config=detector_config,   # per-panel DetectorConfig
    crystal_config=crystal_config,     # CrystalConfig with refined params
    beam_config=beam_config,           # from create_beam_config(beam) — NO flux/exposure/beamsize
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    mask_array=None,
    spot_scale_override=None,          # ← BUG: Should be calibration_metadata['spot_scale_override']
    device=device,
    dtype=dtype,
    calibration_metadata=getattr(config, 'calibration_metadata', None),  # ← Present but not used for spot_scale
)
```

**Factory implementation:**
```python
# dbex/refinement/helpers.py:183-204
# Compute sqrt_scale for post-run application
sqrt_scale = None
if spot_scale_override is not None:
    import math
    sqrt_scale = math.sqrt(spot_scale_override)

# Build Detector and Crystal models
detector = Detector(detector_config)
crystal = Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)
crystal.hkl_data = hkl_grid
crystal.hkl_metadata = hkl_metadata

# Construct Simulator
simulator = Simulator(
    detector=detector,
    crystal=crystal,
    beam_config=beam_config,
    device=device,
    dtype=dtype
)
# ... return simulator, normalized_mask, sqrt_scale, metadata
```

**Observation:** Both paths ultimately call `Simulator(detector, crystal, beam_config, device, dtype)` with **no `spot_scale_override` parameter**. The factory computes `sqrt_scale` separately and returns it for the caller to apply, but reconstruction **does not apply it**.

---

### 2. beam_config Threading

**Stage A:**
```python
# dbex/refinement/stage_a_utils.py:236-267
beam_flux = None
beam_exposure = None
beamsize_mm = None
if calibration_metadata is not None:
    beam_flux = calibration_metadata.get("beam_flux")
    beam_exposure = calibration_metadata.get("beam_exposure")
    beamsize_mm = calibration_metadata.get("beamsize_mm")

beam_config = create_beam_config(beam, flux=beam_flux, beamsize_mm=beamsize_mm, exposure=beam_exposure)
```

**Reconstruction:**
```python
# dbex/refinement/reconstruction.py:170
beam_config = create_beam_config(beam)  # ← NO flux/exposure/beamsize from calibration_metadata
```

**Impact:** Flux/exposure/beamsize affect the forward model's photon count → ADU conversion. Missing these values may contribute to the magnitude mismatch, but the primary issue is the missing `sqrt(spot_scale_override)` factor (10^4.4× discrepancy is too large to be explained by flux/exposure alone).

---

### 3. Post-Run Scaling

**Stage A (baseline derivation):**
```python
# dbex/refinement/stage_a.py:431-453
# Compute model mean from Stage A warmed simulators at delta=0
bragg_samples = [simulator.run() for simulator in stage_a_ctx.simulators]
bragg_stack = torch.stack(bragg_samples, dim=0)
# Apply spot_scale_override per SCALE-002 (sqrt factor)
spot_scale_override = config.calibration_metadata.get("spot_scale_override", 1.0)
sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # ← POST-RUN APPLICATION
model_mean_masked = float(bragg_stack_scaled[loss_mask_t].mean().item())
```

**Stage A (LBFGS closure / validation):**
- Same pattern: `sim.run()` → multiply by `exp(log_scale)` where `log_scale = log_scale_baseline + delta`
- `log_scale_baseline = log(sqrt(spot_scale_override))` (derived above or from config)
- Effective scale: `exp(log_scale_baseline) × exp(delta) = sqrt(spot_scale_override) × exp(delta)`

**Reconstruction:**
```python
# dbex/refinement/reconstruction.py:195-223
# Extract log_scale_baseline from Stage A telemetry
log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')  # ≈ 20.14

if log_scale_baseline_value is not None:
    log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
    log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
    log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
else:
    log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

scale_factor = torch.exp(log_scale_clamped)  # ≈ exp(20.14) ≈ 5.57e8

for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()                       # ← RAW OUTPUT ~1.8e-14 (TOO SMALL)
    bragg_scaled = bragg_panel * scale_factor     # ← 1.8e-14 × 5.57e8 = 1.0e-05 (STILL TOO SMALL)
    bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**Expected:** `scale_factor` should bring raw output (~1.8e-14) to target scale (~0.24 ADU)
**Actual:** `1.8e-14 × 5.57e8 = 1.0e-05` (23,500× too small)

**Root cause:** The raw simulator output is ~10^4.4× smaller than Stage A's raw output because:
1. Stage A builds simulators with `beam_config` including `flux`/`exposure`/`beamsize_mm` (from calibration_metadata)
2. Reconstruction builds simulators with `beam_config` **without** those fields (line 170)
3. **OR:** Stage A's baseline derivation already accounts for `sqrt(spot_scale_override)` in the **model** mean (line 443), but reconstruction's baseline comes from telemetry **after** Stage A scaled the output

**Revised analysis:** Looking at the numbers:
- `spot_scale_override = 3.1e17`
- `sqrt(spot_scale_override) = 5.57e8` ≈ `exp(20.14)`
- Missing factor ≈ 23,500 ≈ 10^4.38 ≈ `sqrt(5.57e8)` ≈ `(spot_scale_override)^(1/4)`

**Hypothesis:** The missing factor is approximately **another sqrt** of the already-applied sqrt factor. This suggests:
- Stage A applies `sqrt(spot_scale_override)` to raw output → scaled output
- Stage A derives baseline from `log(target / scaled_output)` — which **already includes** the sqrt factor
- Reconstruction applies `exp(baseline)` to **raw output** (not scaled output) → result is missing one sqrt factor

**Correct fix:** Reconstruction must also apply `sqrt(spot_scale_override)` to raw output **before** computing the ratio, or extract the **original raw output** from Stage A (without sqrt scaling) to match telemetry assumptions.

---

### 4. Warm Path Comparison

**Stage A warm cache:**
- Build simulators once via `_build_stage_a_context()` (no `spot_scale_override` at construction)
- Reuse same simulators across all LBFGS iterations
- Apply `sqrt(spot_scale_override)` post-run every iteration

**Reconstruction warm cache:**
- Reuse Stage A's simulators via `_retarget_stage_a_simulators()` (lines 149-165)
- Apply `scale_factor = exp(log_scale_baseline)` post-run (lines 220-223)
- **Should work correctly** if Stage A telemetry encodes the right baseline

**Observation:** Warm path should have magnitude parity **if** `exp(log_scale_baseline) == sqrt(spot_scale_override)`. But the failing tests use **cold path** (no `stage_a_ctx` available), hitting the bug where `beam_config` lacks flux/exposure and `sqrt_scale` is ignored.

---

## Root Cause Summary

1. **Simulator construction parity:** Both Stage A and reconstruction build `Simulator(...)` **without** `spot_scale_override` parameter (it doesn't exist). Post-run scaling is the only mechanism.

2. **beam_config mismatch:** Stage A threads `flux`, `exposure`, `beamsize_mm` from `calibration_metadata` into `beam_config` (stage_a_utils.py:267). Reconstruction does not (reconstruction.py:170). This may affect photon counts, but the 10^4.4× discrepancy is too large.

3. **sqrt_scale ignored:** Factory computes `sqrt_scale = sqrt(spot_scale_override)` and returns it (helpers.py:183-187), but reconstruction does not apply it (reconstruction.py:177-190 unpacks it but doesn't use it).

4. **Baseline assumption mismatch:** Stage A derives `log_scale_baseline` from **sqrt-scaled** model output. Reconstruction assumes `exp(baseline)` will scale **raw** output to target, but the raw output from cold-path simulators is missing the sqrt factor.

**The fix:** Reconstruction must either:
- **Option A:** Pass `spot_scale_override=calibration_metadata['spot_scale_override']` to factory and apply returned `sqrt_scale` post-run
- **Option B:** Extract `spot_scale_override` from config.calibration_metadata and manually apply `sqrt(spot_scale)` to raw output (matching Stage A pattern)
- **Option C:** Thread `flux`, `exposure`, `beamsize_mm` from calibration_metadata to `beam_config` (may partially address, but not the full factor)

---

## Spec Violations

- **Factory contract (dbex/refinement/helpers.py:117-119):** "Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)" — reconstruction violates this by passing `None` and ignoring returned `sqrt_scale`
- **Calibration threading (docs/spec-db-core.md §§20-40):** Simulators must produce outputs consistent with calibration metadata — reconstruction cold path does not thread beam flux/exposure/spot_scale
- **Post-run scaling pattern (SCALE-004 finding):** `sqrt(spot_scale_override)` must be applied to raw Bragg intensities — reconstruction assumes `exp(log_scale_baseline)` handles this, but baseline is derived from **already-scaled** output

---

## Cross-References

- Stage A simulator construction: `dbex/refinement/stage_a_utils.py::_build_stage_a_context()` lines 177-376
- Stage A post-run scaling: `dbex/refinement/stage_a.py` lines 442-443 (baseline derivation), 1194-1202 (closure scaling)
- Reconstruction simulator construction: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry()` lines 167-190 (cold path), 149-165 (warm path)
- Factory implementation: `dbex/refinement/helpers.py::create_unified_simulator()` lines 83-219
- Ralph's debug evidence: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`
