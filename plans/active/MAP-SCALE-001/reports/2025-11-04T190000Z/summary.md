# MAP-SCALE-001 Ralph Implementation (2025-11-04T190000Z)

## Problem Statement

Per `input.md` Do Now (2025-11-04T190000Z), implement beam flux/beamsize/exposure and crystal N_cells plumbing from `config_torch.json` into `simulate_forward_once` to align zero-iteration mapping physics with canonical nanobrag capture.

**Quoted SPEC lines implemented:**
- docs/spec-db-conformance.md:43-46: DB-AT-024 acceptance thresholds (median corr ≥0.2, localization ≥90%)
- docs/findings.md SCALE-002: sqrt(spot_scale_override) applied post-simulation
- docs/findings.md SCALE-003: Zero-iteration helper must ingest DiffBragg-refined calibration
- docs/findings.md SCALE-004: Refined geometry + refined Fopt + calibration metadata required

**ADR/ARCH alignment:**
- docs/architecture.md:82-109: Bridge responsibilities and calibration surfaces
- docs/nanobrag_api.md:18-67: BeamConfig and CrystalConfig required fields

## Implementation Summary

### Code Changes

1. **Extended `load_calibration_metadata` (dbex/nanobrag_bridge.py:606-695)**
   - Added parsing for `beam.beamsize_mm` (optional, fallback None)
   - Added parsing for `crystal.N_cells` as tuple of 3 ints (optional, fallback None)
   - Updated docstring to document new return fields
   - Validation: beamsize and N_cells are optional; if present, must be valid

2. **Updated `create_beam_config` (dbex/nanobrag_bridge.py:392-432)**
   - Added optional parameters: `flux`, `beamsize_mm`, `exposure`
   - Parameters flow through to BeamConfig constructor
   - When all three are provided and valid, BeamConfig.__post_init__ computes fluence = flux·exposure/beamsize²

3. **Updated `create_crystal_config` (dbex/nanobrag_bridge.py:435-493)**
   - Added optional parameter: `N_cells` (tuple of 3 ints)
   - Parameter flows through to CrystalConfig constructor

4. **Refactored `simulate_forward_once` (dbex/nanobrag_bridge.py:822-942)**
   - Added optional `calibration` dict parameter
   - Extracts calibration values: spot_scale_override, beam_flux, beam_exposure, beamsize_mm, N_cells
   - Passes calibration overrides to `create_beam_config` and `create_crystal_config`
   - Calibration dict takes precedence over deprecated `spot_scale_override` parameter
   - Still applies sqrt(spot_scale_override) post-simulation per SCALE-002

5. **Updated test (tests/dbex/test_mapping_consistency.py:183-212,251-258)**
   - Changed `simulate_forward_once` call to pass `calibration=calibration` instead of `spot_scale_override=spot_scale_override`
   - Extended metrics JSON to include `beamsize_mm` and `N_cells` fields
   - Test still applies refined geometry and refined MTZ per SCALE-004

### Test Results

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```

**Metrics (2025-11-04T190000Z):**
- n_roi: 92
- corr_median: **-0.0431** (was 0.0190 in 2025-11-04T130000Z)
- localization_success_rate: **7.61%** (was 1.09% in 2025-11-04T130000Z)
- bragg_stats.max: **4.17e15** ADU (was 4.84e7 in 2025-11-04T130000Z)
- bragg_stats.mean: **2.97e10** ADU (was 1.32e6 in 2025-11-04T130000Z)
- calibration.beamsize_mm: 1.0 (newly populated)
- calibration.N_cells: [36, 28, 26] (newly populated)
- using_refined_geometry: True
- hkl_source: refined_structure_factors.mtz

**Comparison to canonical bragg_torch.npy:**
- Canonical (masked ROI) mean: 77.5 ADU
- Test output (masked ROI) mean: ~2.97e10 ADU
- Ratio: **3.8e8× too large**

**Comparison to prior run (2025-11-04T130000Z, without flux/beamsize):**
- Prior mean: 1.32e6 ADU
- Current mean: 2.97e10 ADU
- Regression: **22,500× increase**

## First Divergence

**Root cause:** Passing `flux=1e12`, `beamsize_mm=1.0`, `exposure=1.0` to BeamConfig causes fluence calculation:
```
fluence = flux · exposure / (beamsize_m)²
        = 1e12 · 1.0 / (0.001)²
        = 1e18 photons/m²
```

BeamConfig default fluence is `1.26e29` (from C code). Setting flux/beamsize reduces fluence by 1e11×, but the resulting bragg output is still **3.8e8× larger** than canonical bragg_torch.npy.

**Hypothesis:** The flux/beamsize/exposure values in `config_torch.json` are **diagnostic metadata** documenting what the canonical generator used, NOT **runtime parameters** for zero-iteration simulation. 

The canonical generator:
1. Runs simulator WITH flux/beamsize/N_cells (physical beam parameters)
2. Gets raw output
3. Applies `post_sim_scale = sqrt(spot_scale_override)` = 5.643e8
4. Saves scaled output as `bragg_torch.npy`

For zero-iteration mapping test, we want to match DiffBragg's forward simulation for comparison with real detector data. DiffBragg uses its own internal flux/beamsize settings. The `spot_scale_override` is what **calibrates the simulation output to match real data**.

**spot_scale_override already includes the flux effect**. Applying both flux AND spot_scale double-counts the intensity scaling.

**Correct zero-iteration approach (revised hypothesis):**
1. Run simulator WITHOUT flux/beamsize/exposure (use defaults or leave unset)
2. Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
3. Use refined geometry + refined Fopt (SCALE-004)

This matches the prior run (2025-11-04T130000Z) which had better correlation (0.019) than current (-0.043).

## Artifacts

- `pytest_db_at_024.log`: Full pytest output with test failure
- `mapping_metrics.json`: ROI metrics showing correlation=-0.0431, localization=7.61%
- `mapping_metrics.csv`: Per-ROI detailed metrics
- Summary: This document

## Next Actions

**BLOCKED pending supervisor clarification:**

The input.md Do Now directed implementation of flux/beamsize/N_cells plumbing based on analysis from 2025-11-04T175020Z. Implementation is technically correct (code does what was asked), but test results show severe regression (correlation degraded from 0.019 to -0.043, intensity inflation by 3.8e8×).

**Root question:** Are flux/beamsize/exposure/N_cells in `config_torch.json` intended as:
1. **Diagnostic metadata** (what generator used to create canonical tensors) → Should NOT be passed to zero-iteration runtime bridge
2. **Runtime calibration parameters** (needed for physics alignment) → Should be passed but with different scaling logic

**Recommendation:** Revert flux/beamsize/exposure plumbing from `simulate_forward_once`; keep only N_cells if it affects mosaic domain physics independently of intensity scaling. Supervisor (Galph) should clarify whether `config_torch.json` beam parameters are diagnostic or prescriptive for zero-iteration tests.

**Alternative:** If flux/beamsize/N_cells ARE required, then spot_scale_override should NOT be applied when calibration dict is provided (because scale is already baked into flux). But this contradicts SCALE-002 guidance.

**Exit criteria status:**
- ✅ Code changes implemented per Do Now
- ❌ DB_AT_024 thresholds NOT met (corr=-0.043 < 0.2, loc=7.61% < 90%)
- ❌ Regression from prior run (corr 0.019 → -0.043, mean 1.32e6 → 2.97e10)
- ⚠️  Blocker: Ambiguity in calibration parameter semantics

---

**Ralph implementation complete; supervisor decision required before proceeding.**
