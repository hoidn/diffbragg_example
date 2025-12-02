# Stage A Simulator Construction Analysis

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Date:** 2025-12-02
**Focus:** How Stage A constructs simulators and applies calibration metadata

---

## Summary

Stage A builds simulators via the **warm cache path** when `config.enable_stage_a_warm_cache=True` (default). Simulators are constructed once at the beginning of Stage A via `_build_stage_a_context()` helper and then **reused** across all LBFGS iterations. Calibration metadata (including `spot_scale_override`) is **not passed to the simulator constructor** but is instead **applied post-run** by multiplying raw simulator output by `sqrt(spot_scale_override)`.

---

## Factory Call Site

**Function:** `dbex/refinement/stage_a_utils.py::_build_stage_a_context()`
**Lines:** 177-376 (simulator construction at 309-316)
**Called from:** `dbex/refinement/stage_a.py::_build_stage_a_params()` line 384

### Warm Path (Default)

```python
# dbex/refinement/stage_a.py:382-398
stage_a_ctx = None
if config.enable_stage_a_warm_cache:
    stage_a_ctx = _build_stage_a_context(
        detector=detector,
        beam=beam,
        crystal=crystal,
        trusted_mask=trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=config.enable_hkl_interpolation,
        device=device,
        dtype=dtype,
        panel_slices=panel_slices,
        enable_roi_mode=config.enable_roi_mode,
        calibration_metadata=config.calibration_metadata,  # ← THREADED BUT NOT USED IN SIMULATOR CONSTRUCTION
        log_scale_baseline=None,
        apply_calibration_n_cells=True,
    )
```

**Key observation:** `calibration_metadata` is passed to `_build_stage_a_context()` but **only used for deriving `log_scale_baseline`** (lines 246-262), **not for simulator construction**.

---

## Simulator Construction Logic

**File:** `dbex/refinement/stage_a_utils.py`
**Lines:** 309-316 (per-panel loop at 279-316, ROI loop at 322-358)

### Per-Panel Simulators

```python
# Lines 309-316
simulator = Simulator(
    detector=detector_model,
    crystal=base_crystal_model,
    beam_config=beam_config,
    device=device,
    dtype=dtype,
)
simulators.append(simulator)
```

**Arguments passed to Simulator constructor:**
- `detector`: per-panel Detector model (built from panel geometry)
- `crystal`: shared Crystal model (with beam_config, HKL grid)
- `beam_config`: created from dxtbx Beam + optional flux/beamsize/exposure (lines 267, 240-241)
- `device`, `dtype`: target device/dtype
- **NO `spot_scale_override` argument** — Simulator class does not accept this parameter

---

## Calibration Metadata Flow

**File:** `dbex/refinement/stage_a_utils.py`
**Lines:** 236-265

```python
# Extract calibration payload
beam_flux = None
beam_exposure = None
beamsize_mm = None
N_cells = None
spot_scale_override = None
sqrt_spot_scale = None
calibration_adjusted_for_n_cells = False
if calibration_metadata is not None:
    beam_flux = calibration_metadata.get("beam_flux")
    beam_exposure = calibration_metadata.get("beam_exposure")
    beamsize_mm = calibration_metadata.get("beamsize_mm")
    N_cells = calibration_metadata.get("N_cells")
    calibration_adjusted_for_n_cells = calibration_metadata.get("calibration_adjusted_for_n_cells", False)
    if "spot_scale_override" in calibration_metadata:
        spot_scale_override = calibration_metadata.get("spot_scale_override")
        try:
            sqrt_spot_scale = float(np.sqrt(spot_scale_override))
            log_scale_baseline = float(np.log(sqrt_spot_scale))  # ← USED FOR LOG_SCALE BASELINE ONLY
        except (TypeError, ValueError):
            sqrt_spot_scale = None
            log_scale_baseline = None
```

**Flow:**
1. Extract `spot_scale_override` from `calibration_metadata` (line 256)
2. Compute `sqrt_spot_scale = sqrt(spot_scale_override)` (line 258)
3. Derive `log_scale_baseline = log(sqrt_spot_scale)` (line 259) — **stored for parameter initialization, NOT applied to simulator**
4. Build `beam_config` with `flux`, `beamsize_mm`, `exposure` (line 267), but **NOT `spot_scale_override`**
5. Build `crystal_config` with optional `N_cells` (line 272), but **NOT `spot_scale_override`**
6. Construct simulators **WITHOUT `spot_scale_override`** (lines 309-316)

---

## Post-Run Scaling Application

**File:** `dbex/refinement/stage_a.py`
**Lines:** 431-453 (baseline derivation), 1194-1202 (scale computation), 1422+ (loss closure)

### Baseline Derivation (Warm Simulators at Zero Iteration)

```python
# Lines 431-453
# Compute model mean from Stage A warmed simulators at delta=0
try:
    with torch.no_grad():
        bragg_samples = [simulator.run() for simulator in stage_a_ctx.simulators]
        bragg_stack = torch.stack(bragg_samples, dim=0)
        # Apply spot_scale_override per SCALE-002 (sqrt factor)
        spot_scale_override = config.calibration_metadata.get("spot_scale_override", 1.0)
        sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
        bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # ← POST-RUN APPLICATION
        if loss_mask_t is not None:
            model_mean_masked = float(bragg_stack_scaled[loss_mask_t].mean().item())
        else:
            model_mean_masked = float(bragg_stack_scaled[inputs.loss_mask].mean().item())
except Exception:
    model_mean_masked = None
```

**Pattern:** Run simulators → get raw output → multiply by `sqrt_spot_scale` → compute masked mean for baseline

### Scale Factor During Training

Stage A training applies the same pattern inside the LBFGS closure and validation runs (not shown here for brevity, but confirmed via code reading at lines 1194-1202, 1422+). Every simulator.run() output is immediately multiplied by `exp(log_scale)` where:
- `log_scale = log_scale_baseline + log_scale_delta` (calibrated path)
- `log_scale_baseline = log(sqrt(spot_scale_override))`

This means the **effective scaling factor** is:
```
scale_effective = exp(log_scale_baseline) * exp(log_scale_delta)
                = sqrt(spot_scale_override) * exp(log_scale_delta)
```

So `sqrt_spot_scale` is **baked into every forward model evaluation** during training.

---

## Cold Path (Fallback)

**Condition:** `config.enable_stage_a_warm_cache=False`

When cold mode is active, `stage_a_ctx=None` and simulators are **rebuilt inside the LBFGS closure on every iteration**. The closure would build simulators via the same `Simulator(detector, crystal, beam_config, ...)` pattern (no `spot_scale_override` argument), then apply post-run scaling.

**Evidence:** Not directly observed in this analysis (warm mode is the default and typical path for refinement), but the architecture suggests the same post-run pattern holds.

---

## Key Findings

1. **No factory delegation:** Stage A does NOT use `create_unified_simulator()` — it directly instantiates `Simulator` class from `nanobrag_torch` (lines 309-316, 341-347)

2. **spot_scale_override NOT passed to constructor:** The `Simulator` class constructor does not accept `spot_scale_override` as a parameter

3. **Post-run multiplication is normative:** Stage A applies `sqrt(spot_scale_override)` **after** calling `simulator.run()` to scale raw Bragg intensities (lines 442-443)

4. **Baseline derivation uses post-run pattern:** The `log_scale_baseline` is derived from `sqrt(spot_scale_override)` but the actual scaling happens at runtime via `exp(log_scale_baseline + delta)` multiplication (line 442)

5. **Calibration metadata is config-level:** Stored in `config.calibration_metadata`, threaded through context construction, but **NOT embedded in simulators**

---

## Spec Citations

- **docs/spec-db-core.md §§20-40:** Calibration contracts — simulators must produce outputs that match mapping baseline intensities when calibration metadata is present
- **docs/architecture/calibration_scaling.md:** ADU↔photon policy — spot_scale_override defines the scale factor relating simulator photon counts to detector ADU
- **SCALE-002 (findings):** sqrt factor application — `spot_scale_override` is multiplicative scale applied as `sqrt(value)` per nanoBragg physics convention
- **TOOLING-VIS-001 Phase D.E:** Log_scale baseline separation — when calibration is present, `log_scale_baseline = log(sqrt(spot_scale_override))` is fixed, `log_scale_delta` is the learnable parameter

---

## Cross-References

- Stage A parameter building: `dbex/refinement/stage_a.py::_build_stage_a_params()` lines 122-573
- Warm context construction: `dbex/refinement/stage_a_utils.py::_build_stage_a_context()` lines 177-376
- LBFGS closure: `dbex/refinement/stage_a.py::_build_lbfgs_closure()` (uses `stage_a_ctx.simulators` and applies post-run scaling)
- Reconstruction helper: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry()` lines 25-225 (comparison target)
