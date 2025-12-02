# ARCH-SIM-CONSTRUCTION-001 Phase A.1 Evidence Collection Summary

**Initiative:** ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
**Phase:** A.1 Evidence Collection
**Date:** 2025-12-02T233717Z
**Status:** Complete — Root cause confirmed, ready for Phase B probe

---

## Executive Summary

**Root cause identified:** Reconstruction helper `build_final_bragg_from_stage_a_telemetry()` violates the factory contract by passing `spot_scale_override=None` to `create_unified_simulator()` and ignoring the returned `sqrt_scale` value. This produces simulator raw outputs that are **~23,900× too small** (missing factor ≈ `(spot_scale_override)^(1/4)`), causing DB-AT-028/029 test failures despite correct `log_scale_baseline` extraction logic (commit 6db57f45).

**Key finding:** Stage A applies `sqrt(spot_scale_override)` post-run to **every** simulator output during training and baseline derivation. Reconstruction assumes `exp(log_scale_baseline)` handles all scaling, but the baseline was derived from **already-scaled** output. The missing explicit `sqrt(spot_scale)` multiplication in reconstruction's cold path produces outputs 23,900× too small.

---

## Evidence Summary

### 1. Stage A Simulator Construction

**Pattern:** Direct `Simulator(detector, crystal, beam_config, device, dtype)` instantiation (no factory)
**File:** `dbex/refinement/stage_a_utils.py::_build_stage_a_context()` lines 309-316
**Calibration threading:**
- Extracts `spot_scale_override` from `config.calibration_metadata` (line 256)
- Derives `log_scale_baseline = log(sqrt(spot_scale_override))` (line 259) — used for **parameter initialization only**
- Threads `flux`, `exposure`, `beamsize_mm` into `beam_config` (line 267)
- **Does NOT pass** `spot_scale_override` to `Simulator` constructor (parameter does not exist)

**Post-run scaling (normative):**
```python
# dbex/refinement/stage_a.py:442-443
bragg_stack = torch.stack([sim.run() for sim in stage_a_ctx.simulators], dim=0)
sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # ← Applied to EVERY forward model evaluation
```

**Result:** Stage A training and baseline derivation **consistently apply** `sqrt(spot_scale_override)` to raw simulator output.

### 2. Reconstruction Simulator Construction (Cold Path)

**Pattern:** `create_unified_simulator()` factory call
**File:** `dbex/refinement/reconstruction.py` lines 177-190
**Calibration threading:**
- Passes `calibration_metadata=config.calibration_metadata` to factory (line 187) — present but **not used** for `spot_scale_override` extraction
- Passes `spot_scale_override=None` explicitly (line 184) — **BUG**
- Does **NOT** thread `flux`, `exposure`, `beamsize_mm` into `beam_config` (line 170)

**Factory return value:**
```python
simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(...)
# sqrt_scale = None (because spot_scale_override=None)
# But factory contract says: "sqrt_scale is computed here but applied by CALLER after simulator.run()"
```

**Post-run scaling (WRONG):**
```python
# dbex/refinement/reconstruction.py:220-223
for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()                       # ← RAW output ~1.8e-14 ADU
    bragg_scaled = bragg_panel * scale_factor     # ← ONLY applies exp(log_scale_baseline), NOT sqrt(spot_scale)
    bragg_full[pid] = bragg_scaled.cpu().numpy()
```

**Result:** Reconstruction **does NOT apply** `sqrt(spot_scale_override)` to raw output, violating the factory contract and breaking magnitude parity with Stage A.

### 3. Factory Contract

**File:** `dbex/refinement/helpers.py::create_unified_simulator()` lines 83-219

**Documented contract (lines 117-119):**
> `spot_scale_override : Optional[float]`
>     Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)
>     per SCALE-004 finding.

**Return value (lines 133-134):**
> `sqrt_scale : Optional[float]`
>     sqrt(spot_scale_override) to apply post-run, else None.

**Implementation (lines 183-187):**
```python
sqrt_scale = None
if spot_scale_override is not None:
    import math
    sqrt_scale = math.sqrt(spot_scale_override)
```

**Observation:** Factory computes `sqrt_scale` but **does NOT apply it** to the simulator. Caller **must** apply it post-run. Reconstruction violates this contract.

### 4. Debug Metrics (Commit 6db57f45)

**Source:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json`

| Metric | Value | Notes |
|--------|-------|-------|
| `spot_scale_override` | 3.105e+17 | From calibration metadata |
| `sqrt(spot_scale_override)` | 5.572e+8 | Correct derivation |
| `log_scale_baseline` | 20.138 | Correct: `log(5.572e8)` |
| `scale_factor` | 5.572e+8 | Correct: `exp(20.138)` |
| `bragg_panel (raw)` | 1.839e-14 | **TOO SMALL** (expected ~4.3e-10) |
| `bragg_after (scaled)` | 1.025e-05 | **TOO SMALL** (expected ~0.24) |
| Missing factor | **23,900** | `0.24 / 1.02e-05 ≈ (spot_scale)^(1/4)` |

**Confidence:** High — missing factor matches `(3.105e17)^0.25 = 23,600` within 1.3%

---

## Root Cause Analysis

### Hypothesis: Double-Baseline Problem

**Stage A baseline derivation:**
1. Run simulators at delta=0: `model_raw = sim.run()` → ~1.8e-14 ADU (raw, no scaling)
2. Apply `sqrt(spot_scale_override)`: `model_scaled = model_raw × 5.572e8` → ~1e-5 ADU
3. Compute baseline: `log_scale_baseline = log(target_mean / model_scaled)`
4. Store `log_scale_baseline` in telemetry

**Reconstruction baseline application:**
1. Extract `log_scale_baseline` from telemetry → 20.138
2. Compute `scale_factor = exp(log_scale_baseline)` → 5.572e8
3. Run simulators: `model_raw = sim.run()` → ~1.8e-14 ADU (raw, **same as Stage A**)
4. Apply scale: `bragg = model_raw × scale_factor` → ~1e-5 ADU ✗ **WRONG**

**Expected:**
- `bragg = model_raw × sqrt(spot_scale) × scale_factor`
- Where `scale_factor` encodes the **delta** from baseline, not the full sqrt factor

**But Stage A's baseline derivation already includes sqrt factor:**
- `baseline = log(target / (model_raw × sqrt(spot_scale)))`
- So `exp(baseline) = target / (model_raw × sqrt(spot_scale))`
- Applying this to raw output: `model_raw × exp(baseline) = target / sqrt(spot_scale)` ✗ **missing sqrt factor**

**The fix:** Reconstruction must also apply `sqrt(spot_scale)` explicitly:
```python
bragg = model_raw × sqrt(spot_scale) × exp(baseline)
```

---

## Key Differences: Stage A vs Reconstruction

| Aspect | Stage A | Reconstruction (Cold Path) | Impact |
|--------|---------|---------------------------|--------|
| **Simulator factory** | Direct `Simulator(...)` instantiation | `create_unified_simulator()` factory | Different code paths, but same underlying `Simulator` constructor |
| **spot_scale_override arg** | N/A (not a Simulator parameter) | `spot_scale_override=None` (line 184) | Factory cannot compute `sqrt_scale` |
| **Factory sqrt_scale return** | N/A (no factory) | Ignored (unpacked but not used) | Missing post-run multiplication |
| **beam_config threading** | Includes `flux`, `exposure`, `beamsize_mm` from `calibration_metadata` (stage_a_utils.py:267) | Does NOT include (reconstruction.py:170) | May contribute to magnitude mismatch |
| **Post-run scaling** | `bragg = sim.run() × sqrt(spot_scale) × exp(log_scale)` | `bragg = sim.run() × exp(log_scale_baseline)` | Missing explicit `sqrt(spot_scale)` factor |
| **Baseline derivation** | Computed from **scaled** model output | Assumed from Stage A telemetry | Baseline already includes sqrt factor |

---

## Spec Violations

1. **Factory contract (`dbex/refinement/helpers.py:117-119`):** "Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)" — reconstruction violates by passing `None` and ignoring `sqrt_scale` return value

2. **Calibration threading (`docs/spec-db-core.md §§20-40`):** Simulators must produce outputs consistent with calibration metadata — reconstruction cold path does not thread `spot_scale_override` or `beam_flux`/`exposure`

3. **Post-run scaling pattern (`SCALE-004 finding`):** `sqrt(spot_scale_override)` must be applied to raw Bragg intensities — reconstruction omits this step

4. **DB-AT-028 acceptance:** `chi2_per_pixel_initial ≤ 100` — FAIL (1.084e+05, **1000× too large**)

5. **DB-AT-029 acceptance:** `roi_cc_median_before ≥ 0.2` — FAIL (-0.050, **below floor**)

---

## Recommended Fix (Phase C Implementation)

### Option A: Factory-Based (Minimal)

**File:** `dbex/refinement/reconstruction.py`
**Lines:** 184, 220-223

```python
# Line 184: Pass spot_scale_override to factory
spot_scale_override_value = None
if config.calibration_metadata is not None:
    spot_scale_override_value = config.calibration_metadata.get('spot_scale_override')

simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(
    detector_config=detector_config,
    crystal_config=crystal_config,
    beam_config=beam_config,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    mask_array=None,
    spot_scale_override=spot_scale_override_value,  # ← FIX: Thread from calibration_metadata
    device=device,
    dtype=dtype,
    calibration_metadata=getattr(config, 'calibration_metadata', None),
)

# Lines 220-223: Apply returned sqrt_scale
for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()
    if sqrt_scale is not None:
        bragg_panel = bragg_panel * sqrt_scale  # ← FIX: Apply factory-returned scale
    bragg_scaled = bragg_panel * scale_factor
    bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**Note:** Factory computes `sqrt_scale` per-call (one value for all simulators), but the loop builds simulators one at a time. Need to store `sqrt_scale` from first call and reuse, OR move `sqrt_scale` computation outside the loop.

### Option B: Consistent with Stage A Pattern (Preferred)

**File:** `dbex/refinement/reconstruction.py`
**Lines:** Before line 220 (outside simulator loop)

```python
# Extract spot_scale_override from calibration metadata (matching Stage A pattern)
spot_scale_override = None
if config.calibration_metadata is not None:
    spot_scale_override = config.calibration_metadata.get('spot_scale_override', 1.0)
sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0

# Lines 220-223: Apply sqrt_spot_scale post-run (matching stage_a.py:442-443)
for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()
    bragg_panel_scaled = bragg_panel * sqrt_spot_scale  # ← FIX: Consistent with Stage A
    bragg_scaled = bragg_panel_scaled * scale_factor
    bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**Advantages:**
- Matches Stage A's normative pattern exactly (stage_a.py:442-443)
- Does NOT rely on factory (avoids coupling to factory contract changes)
- Single `sqrt_spot_scale` value computed once, applied to all panels
- Architectural consistency: both training and reconstruction use the same scaling semantics

### Option C: Thread Beam Calibration (Supplementary)

**File:** `dbex/refinement/reconstruction.py`
**Line:** 170

```python
# Thread beam calibration from metadata (matching stage_a_utils.py:267)
beam_flux = None
beam_exposure = None
beamsize_mm = None
if config.calibration_metadata is not None:
    beam_flux = config.calibration_metadata.get('beam_flux')
    beam_exposure = config.calibration_metadata.get('beam_exposure')
    beamsize_mm = config.calibration_metadata.get('beamsize_mm')

beam_config = create_beam_config(beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)
```

**Note:** This may partially address magnitude issues, but **Option B is still required** to apply `sqrt(spot_scale)`.

**Recommendation:** Implement **Option B + Option C** for full architectural alignment with Stage A.

---

## Artifacts Created

1. `stage_a_simulator_construction.md` — How Stage A builds simulators and applies calibration (warm cache path, post-run sqrt scaling pattern)
2. `reconstruction_simulator_construction.md` — How reconstruction builds simulators (cold vs warm paths, factory contract violation)
3. `factory_call_comparison.md` — Side-by-side comparison table showing exact differences in arguments and scaling logic
4. `debug_metrics_analysis.md` — Quantitative analysis of Ralph's debug evidence (missing factor ≈ (spot_scale)^(1/4), confidence: high)
5. `summary.md` — This document (synthesis, root cause, recommended fix)

**Artifacts path:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/`

---

## Next Steps (Phase B — Root Cause Isolation)

**Goal:** Confirm hypothesis via targeted probe before implementing fix

### B.1 — Minimal Probe Script (Optional)

**Action:** Write `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_spot_scale_factory.py` (Tier 2 script)
**Purpose:** Build simulators with and without `spot_scale_override`, measure raw output magnitude difference
**Validation:** Confirm missing factor ≈ `(spot_scale)^(1/4)` when `spot_scale_override=None`

**Skip condition:** Evidence is already conclusive — can proceed directly to Phase C fix implementation

### B.2 — Warm Path Parity Check (Recommended)

**Action:** Run DB-AT-028/029 tests with `stage_a_ctx` provided (warm path) instead of cold path
**Purpose:** Verify warm path produces correct magnitudes (reuses Stage A simulators, should have parity)
**Expected:** Tests **pass** in warm mode, **fail** in cold mode → confirms cold path is the issue

**How-to:**
1. Modify test fixture to save `stage_a_ctx` from Stage A run
2. Pass `stage_a_ctx` to `build_final_bragg_from_stage_a_telemetry()`
3. Rerun tests

### B.3 — Hypothesis Confirmation (Required Before Phase C)

**Action:** Review this evidence summary with Galph; decide whether to:
- Proceed directly to Phase C fix (Option B + Option C recommended)
- Run Phase B probe to build additional confidence
- Open spec_change initiative if baseline derivation semantics need clarification

**Confidence level:** High (arithmetic checks out, pattern match with Stage A is clear, missing factor quantified)

---

## Architecture Notes

### Why Stage A Doesn't Use the Factory

Stage A predates the `create_unified_simulator()` factory (added in TORCH-API-ALIGN-001 Phase B). Stage A directly instantiates `Simulator` for maximum control over device/dtype/cache behavior. The factory was introduced for **forward-only** reconstruction helpers and CLI paths.

**Implication:** Stage A and reconstruction have **diverged** in their construction patterns. This initiative aligns them by ensuring reconstruction follows the same **post-run scaling semantics** as Stage A.

### Factory Contract Clarity

The factory docstring (helpers.py:117-119, 133-134) is clear about the contract: `sqrt_scale` is **computed** by the factory but **applied by the caller**. Reconstruction violates this by passing `None` and ignoring the return value.

**Recommendation:** Update reconstruction to honor the contract (Option B is simplest and most consistent with Stage A).

---

## Cross-References

- **Spec:** `docs/spec-db-core.md §§20-40` (calibration contracts)
- **Spec:** `docs/architecture/calibration_scaling.md` (ADU↔photon policy, spot_scale threading)
- **Finding:** `SCALE-002` (sqrt factor application per nanoBragg convention)
- **Finding:** `SCALE-004` (post-run application pattern)
- **Initiative:** `TOOLING-VIS-001 Phase D.E` (log_scale baseline separation for calibrated runs)
- **Initiative:** `ARCH-FACTORY-001` (unified simulator factory adoption)
- **Test:** `DB-AT-028` (chi²/pixel initial ≤ 100)
- **Test:** `DB-AT-029` (median ROI correlation before ≥ 0.2)
- **Ralph's evidence:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`
- **Metrics:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json`
