# Phase B Implementation Summary — TORCH-BRIDGE-001

**Loop:** 2025-10-28T224846Z
**Focus:** Phase B config hydration (Detector/Beam/Crystal mapping)
**Mode:** TDD
**Branch:** integration

## Objectives Completed

### B1 — Detector Config Mapping
Implemented `create_detector_config(panel, beam, trusted_mask)` with complete test coverage:
- ✅ Beam center swap: dxtbx (fast, slow) → torch (beam_center_s, beam_center_f)
- ✅ Sample→source vector: normalized -s0/||s0|| for custom_beam_vector
- ✅ CUSTOM detector convention with explicit basis vectors
- ✅ Mask array float conversion: bool True=include → float 1.0=include
- ✅ Pixel size and dimensions mapping (square pixel guard enforced)
- ✅ Distance extraction via panel.get_directed_distance()

**Tests:** 6 tests in `TestDetectorConfigMapping`, all passing

### B2 — Beam and Crystal Config Mapping
Implemented `create_beam_config(beam)` and `create_crystal_config(crystal, experiment)` with complete test coverage:

**Beam:**
- ✅ Wavelength extraction in Angstroms
- ✅ Polarization factor=0.0 parity default, nopolar=False
- ✅ Polarization axis/fraction extraction from metadata
- ✅ Fallback to [0,0,1] axis and 0.999 fraction when metadata missing

**Crystal:**
- ✅ Unit cell parameters in Angstroms and degrees (no conversion)
- ✅ MOSFLM A* injection from crystal.get_A() columns
- ✅ Stills defaults: phi_steps=1, osc_range_deg=0, mosaic off
- ✅ Misset angles default to [0, 0, 0] (identity rotation)

**Tests:** 8 tests in `TestBeamCrystalConfigMapping`, all passing

## Implementation Details

### Config Dataclass Stubs
Created stub config classes matching nanobrag_torch API:
- `DetectorConfig` — distance, pixel metrics, beam center, CUSTOM vectors, mask
- `BeamConfig` — wavelength, polarization settings
- `CrystalConfig` — unit cell, MOSFLM A*, misset, stills defaults
- `DetectorConvention` enum

These stubs will be replaced with real imports when nanobrag_torch is installed (Phase 0).

### Helper Functions
All three config helpers implemented in `dbex/nanobrag_bridge.py`:
- `create_detector_config()` — 75 lines, comprehensive mapping
- `create_beam_config()` — 35 lines, with try/except fallback
- `create_crystal_config()` — 45 lines, stills-focused

### Spec Compliance
All implementations align with:
- `docs/config_crosswalk.md:15-72` — field-by-field mappings
- `docs/spec-db-core.md:35-46` — geometry/physics requirements
- `docs/dxtbx_api.md:1-50` — source API contracts
- `docs/nanobrag_api.md:23-58` — target API contracts

### Pitfalls Avoided
- ✅ Beam center swap: dxtbx (fast, slow) → torch (s, f) per crosswalk:29
- ✅ Sample→source normalization enforced (not source→sample)
- ✅ Mask polarity preserved (no inversion for simulator path)
- ✅ Unit cell angles kept in degrees (dxtbx and torch both use degrees)
- ✅ Square pixel guard reused from Phase A helper
- ✅ No mutation of source Experiment objects

## Test Results

### Command
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
python -m pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py
```

### Summary
- **Total tests:** 18 (4 Phase A + 14 Phase B)
- **Passed:** 18
- **Failed:** 0
- **Runtime:** 0.18s
- **Platform:** CPU (pytest on simtbx environment)

### Test Breakdown
**Phase A (existing):**
- test_tensor_contract
- test_mask_polarity
- test_pixel_pitch_guard
- test_tuple_mask_input

**Phase B (new):**
- Detector: 6 tests (swap, vector, convention, mask, dimensions, distance)
- Beam: 4 tests (wavelength, parity factor, metadata, fallback)
- Crystal: 4 tests (cell params, MOSFLM A*, stills defaults, misset)

## Artifacts
- `pytest.log` — Detector test run (6 tests)
- `pytest_full.log` — Complete test run (18 tests)
- `do-now-notes.md` — This summary

## Next Actions
1. Phase C: Smoke harness (single-experiment flow, ROI triptych)
2. Integration: Wire config helpers into data_load workflow
3. Validation: Golden-data comparison once nanobrag_torch available

## References
- Implementation: `dbex/nanobrag_bridge.py:24-399`
- Tests: `tests/dbex/test_nanobrag_bridge_configs.py:1-471`
- Spec DB: `docs/config_crosswalk.md`, `docs/spec-db-core.md`
- APIs: `docs/dxtbx_api.md`, `docs/nanobrag_api.md`
