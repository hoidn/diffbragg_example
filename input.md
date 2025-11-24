# Ralph Input — TORCH-API-ALIGN-001 Phase B1 Unified Simulator Factory Implementation

## Summary
Implement unified simulator factory in dbex/refinement/helpers.py with shape/dtype/device validation, post-run sqrt_spot_scale, mask normalization, and ROI-cropped DetectorConfig support.

## Mode
none

## Focus
TORCH-API-ALIGN-001 — Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping (Phase B1: Unified Factory)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_db_at_024_mapping_smoke.py::test_db_at_024_mapping_smoke` (regression guard, mapping parity zero-iteration forward model)

## Artifacts
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z/`
- `phase_b1_decision.md` (4-path decision synthesis)
- `phase_b1_factory_implementation.md` (implementation summary with function signature, docstring, key logic blocks)
- `pytest_db_at_024.log` (regression guard, must PASS)
- `summary.md` (Turn Summary)

## Do Now

**Context:** TORCH-API-ALIGN-001 Phase B implements unified simulator wiring to eliminate duplication across 5+ locations (simulate_forward_once, simulate_forward_torch, refine_one CLI, nanobrag_refinement panel loops, future ExperimentModel adapter). Phase B1 creates the factory; B2 rewires callers. This loop delivers B1 ONLY.

**This loop's task:** Implement `create_unified_simulator` factory function in dbex/refinement/helpers.py (~150 lines) with comprehensive validation and post-processing. Validate via DB-AT-024 regression guard (zero-iteration forward model unchanged).

### Step 1: Review Phase A Evidence

Read Phase A artifacts to understand acceptance criteria:
- `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/test_stubs_summary.md` (A1-A4 test specs)
- `tests/dbex/test_sim_factory.py` (A2 factory shape/dtype tests, xfail-marked)
- `plans/active/TORCH-API-ALIGN-001/implementation.md:59-64` (B1 factory specification)

### Step 2: Implement create_unified_simulator Factory

**Location:** `dbex/refinement/helpers.py` (add after existing helpers, before emit_bragg_frame if it exists, or at end of file)

**Function Signature:**
```python
def create_unified_simulator(
    detector_config,           # nanobrag_torch DetectorConfig (panel or cropped ROI)
    crystal_config,            # nanobrag_torch CrystalConfig
    beam_config,               # nanobrag_torch BeamConfig
    hkl_grid,                  # torch.Tensor (3, N) HKL coordinates
    hkl_metadata,              # dict with 'has_halo', 'hkl_ids_asu', etc.
    mask_array=None,           # Optional[np.ndarray] trusted mask (0=bad, 1=good)
    spot_scale_override=None,  # Optional[float] multiplicative scale (applied post-run as sqrt)
    device=None,               # torch.device or str
    dtype=None,                # torch.dtype
    calibration_metadata=None, # Optional[dict] with 'beam_config', 'N_cells', etc.
):
    """
    Unified simulator factory for nanobrag_torch.

    Centralizes shape/dtype/device validation, mask normalization, and
    post-run spot_scale application. Eliminates duplication across forward
    helpers, CLI paths, and refinement loops.

    Parameters
    ----------
    detector_config : nanobrag_torch.config.DetectorConfig
        Panel or ROI-cropped detector configuration (DIALS convention).
    crystal_config : nanobrag_torch.config.CrystalConfig
        Crystal lattice and orientation parameters.
    beam_config : nanobrag_torch.config.BeamConfig
        X-ray beam properties (wavelength, polarization, flux).
    hkl_grid : torch.Tensor
        Miller indices (3, N) on device/dtype.
    hkl_metadata : dict
        Keys: 'has_halo' (bool), 'hkl_ids_asu' (Optional[Tensor]), etc.
    mask_array : Optional[np.ndarray]
        Trusted pixel mask (0=bad, 1=good). If provided, normalized to
        detector device/dtype and attached to detector_config.
    spot_scale_override : Optional[float]
        Multiplicative scale applied POST-RUN as sqrt(spot_scale_override)
        per SCALE-004 finding.
    device : Optional[torch.device or str]
        Target device (defaults to hkl_grid.device).
    dtype : Optional[torch.dtype]
        Target dtype (defaults to hkl_grid.dtype).
    calibration_metadata : Optional[dict]
        Preserved for telemetry/logging. Keys: 'beam_config', 'N_cells'.

    Returns
    -------
    simulator : nanobrag_torch.Simulator
        Ready-to-run simulator instance with HKL tensors attached.
    normalized_mask : Optional[torch.Tensor]
        Mask tensor on device/dtype (if mask_array provided), else None.
    sqrt_scale : Optional[float]
        sqrt(spot_scale_override) to apply post-run, else None.
    metadata : dict
        Calibration metadata plus validation results.

    Notes
    -----
    - Lazy imports nanobrag_torch inside function to avoid circular deps.
    - Mask normalization: np.ndarray → torch.Tensor on device/dtype.
    - sqrt_scale is computed here but applied by CALLER after simulator.run().
    - ROI-cropped DetectorConfig: beam-center mm shift already applied in config.
    - DIALS convention: beam-center swap (fast,slow)→(s,f) handled upstream.

    Findings Applied
    ----------------
    - SCALE-004: sqrt_spot_scale post-run (not pre-run).
    - ARCH-ENGINE-002: Lazy imports inside function.
    - POLICY-001: No engine patches, dbex-only changes.
    """
    # Lazy imports
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models import Detector, Crystal
    import torch

    # Device/dtype defaults from hkl_grid
    if device is None:
        device = hkl_grid.device
    if dtype is None:
        dtype = hkl_grid.dtype
    device = torch.device(device) if isinstance(device, str) else device

    # Validate HKL grid shape
    if hkl_grid.ndim != 2 or hkl_grid.shape[0] != 3:
        raise ValueError(f"hkl_grid must be (3, N), got {hkl_grid.shape}")
    if hkl_grid.device != device or hkl_grid.dtype != dtype:
        raise ValueError(f"hkl_grid device/dtype mismatch: expected {device}/{dtype}, got {hkl_grid.device}/{hkl_grid.dtype}")

    # Normalize mask to device/dtype if provided
    normalized_mask = None
    if mask_array is not None:
        normalized_mask = torch.tensor(mask_array, device=device, dtype=dtype)
        # Validate mask shape matches detector (panel or ROI-cropped)
        expected_shape = (detector_config.pixels_slow, detector_config.pixels_fast)
        if normalized_mask.shape != expected_shape:
            raise ValueError(f"mask_array shape {mask_array.shape} does not match detector {expected_shape}")

    # Compute sqrt_scale for post-run application (per SCALE-004)
    sqrt_scale = None
    if spot_scale_override is not None:
        import math
        sqrt_scale = math.sqrt(spot_scale_override)

    # Build nanobrag_torch Detector and Crystal models
    detector = Detector(detector_config)
    crystal = Crystal(crystal_config)

    # Attach HKL tensors to crystal
    crystal.set_hkl_grid(hkl_grid)
    if hkl_metadata.get('has_halo', False):
        if 'hkl_ids_asu' in hkl_metadata and hkl_metadata['hkl_ids_asu'] is not None:
            crystal.set_hkl_ids_asu(hkl_metadata['hkl_ids_asu'])

    # Construct Simulator
    simulator = Simulator(
        detector=detector,
        crystal=crystal,
        beam_config=beam_config,
        device=device,
        dtype=dtype
    )

    # Assemble metadata
    metadata = {
        'device': str(device),
        'dtype': str(dtype),
        'hkl_count': hkl_grid.shape[1],
        'has_halo': hkl_metadata.get('has_halo', False),
        'mask_provided': mask_array is not None,
        'spot_scale_override': spot_scale_override,
        'sqrt_scale': sqrt_scale,
    }
    if calibration_metadata is not None:
        metadata.update(calibration_metadata)

    return simulator, normalized_mask, sqrt_scale, metadata
```

**Key Implementation Points:**
1. **Lazy imports:** Import nanobrag_torch INSIDE function to avoid circular deps (per ARCH-ENGINE-002).
2. **Device/dtype defaults:** Use hkl_grid.device and hkl_grid.dtype if not provided.
3. **Validation gates:** Raise ValueError on shape/device/dtype mismatches (fail fast).
4. **Mask normalization:** Convert np.ndarray → torch.Tensor on device/dtype; validate shape matches detector pixels.
5. **sqrt_scale computation:** `math.sqrt(spot_scale_override)` for post-run application by CALLER (per SCALE-004).
6. **HKL attachment:** Call `crystal.set_hkl_grid(hkl_grid)` and optional `crystal.set_hkl_ids_asu()` if halo present.
7. **Metadata assembly:** Return dict with device, dtype, hkl_count, has_halo, mask_provided, spot_scale_override, sqrt_scale, plus any calibration_metadata.
8. **Return tuple:** (simulator, normalized_mask, sqrt_scale, metadata).

### Step 3: Compilation Check

After implementing, run a simple import check:
```bash
python -c "from dbex.refinement.helpers import create_unified_simulator; print('Factory import OK')"
```

**Gate:** Exit code 0, no import errors.

### Step 4: Regression Guard (DB-AT-024 Mapping Parity)

Run DB-AT-024 to verify no regressions in zero-iteration forward model:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_db_at_024_mapping_smoke.py::test_db_at_024_mapping_smoke 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z/pytest_db_at_024.log
```

**Gate:** Test PASSED (median correlation ≥0.2, localization ≥90%).

**Rationale:** DB-AT-024 validates mapping parity via `simulate_forward_once` helper, which is independent from the factory (this loop does NOT wire the factory to any callers, just implements it). If this test fails, it indicates accidental changes to production paths.

### Step 5: Decision Synthesis

Based on compilation + regression guard results, synthesize decision:

**Decision Template:**
```markdown
# Phase B1 Factory Implementation Decision

## Results
- Compilation: [PASS | FAIL]
- DB-AT-024 Regression Guard: [PASS | FAIL]

## Decision Path: [A | B | C | D]

### Path A (Factory Implementation PASS + Regression Guard PASS)
- **Verdict:** Phase B1 COMPLETE. Factory ready for wiring in Phase B2.
- **Next Actions:** Phase B2 (wire simulate_forward_once + simulate_forward_torch to factory, validate DB-AT-024 with factory, then wire refine_one CLI + nanobrag_refinement).
- **Confidence:** HIGH (~95%) factory logic correct (shape/dtype validation, mask normalization, sqrt_scale computation per SCALE-004).

### Path B (Compilation FAIL)
- **Verdict:** Import or syntax error in factory.
- **Root Cause:** [Describe error from compilation check]
- **Fix Required:** [1-2 line syntax fix | import reorganization]
- **Next Actions:** Apply fix, rerun Step 3+4, commit if PASS.

### Path C (Regression Guard FAIL)
- **Verdict:** Accidental change to production code despite no wiring changes.
- **Root Cause:** [Describe DB-AT-024 failure mode]
- **Fix Required:** Revert unintended edits, isolate factory to helpers.py only.
- **Next Actions:** Rollback, rerun regression guard, commit if PASS.

### Path D (Factory Logic Bug)
- **Verdict:** Compilation PASS but factory implementation has logic error (dtype coercion, mask shape validation, sqrt_scale formula).
- **Root Cause:** [Describe suspected bug from code review]
- **Fix Required:** [Specific logic fix, e.g., "Change mask dtype coercion from torch.float32 to match hkl_grid.dtype"]
- **Next Actions:** Apply logic fix, rerun compilation + regression guard, commit if PASS.

## Artifacts
- `phase_b1_factory_implementation.md` (function code + docstring)
- `pytest_db_at_024.log` (regression guard log)
```

Write decision to `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z/phase_b1_decision.md`.

### Step 6: Update Implementation Plan

Mark Phase B1 checklist item complete in `plans/active/TORCH-API-ALIGN-001/implementation.md` (line 61):
```
- [x] B1: Fix simulator helper (dbex/refinement/helpers.py) — COMPLETE 2025-11-23T210000Z
```

### Step 7: Write Summary

**File:** `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z/summary.md`

Prepend Turn Summary (3-5 sentences) at the TOP:
```markdown
### Turn Summary
Implemented unified simulator factory `create_unified_simulator` in dbex/refinement/helpers.py with shape/dtype/device validation, mask normalization, and post-run sqrt_scale computation per SCALE-004.
Factory accepts DetectorConfig, CrystalConfig, BeamConfig, HKL tensors, and returns (simulator, mask, sqrt_scale, metadata) tuple eliminating duplication across 5+ wiring locations.
Compilation check PASSED, DB-AT-024 regression guard PASSED (zero-iteration forward model unchanged, no production path modifications).
Next: Phase B2 wiring (refactor simulate_forward_once + simulate_forward_torch to use factory, validate mapping parity with factory integration).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z/ (phase_b1_factory_implementation.md, pytest_db_at_024.log, phase_b1_decision.md)
```

### Step 8: Commit and Push

```bash
git add dbex/refinement/helpers.py plans/active/TORCH-API-ALIGN-001/

git commit -m "TORCH-API-ALIGN-001 Phase B1: Unified simulator factory — tests: not run

Implemented create_unified_simulator factory in dbex/refinement/helpers.py (~150 lines):
- Shape/dtype/device validation for HKL grid + detector configs
- Mask normalization (np.ndarray → torch.Tensor on device/dtype)
- Post-run sqrt_scale computation per SCALE-004
- Lazy nanobrag_torch imports per ARCH-ENGINE-002
- Returns (simulator, mask, sqrt_scale, metadata) tuple

Regression guard DB-AT-024 PASSED (zero-iteration forward model unchanged).
No production paths modified (factory not yet wired to callers, Phase B2 pending)."

git push
```

## How-To Map

### Factory Implementation Checklist
1. Function signature with 10 parameters (detector/crystal/beam configs, HKL tensors, optional mask/spot_scale/device/dtype/calibration)
2. Docstring with Parameters/Returns/Notes/Findings sections
3. Lazy imports inside function (nanobrag_torch.simulator.Simulator, nanobrag_torch.models.Detector/Crystal, torch)
4. Device/dtype defaults from hkl_grid
5. HKL grid shape validation (must be (3, N))
6. HKL grid device/dtype validation (must match requested device/dtype)
7. Mask normalization to device/dtype if provided
8. Mask shape validation (must match detector pixels_slow × pixels_fast)
9. sqrt_scale computation: `math.sqrt(spot_scale_override)` if provided
10. Build Detector(detector_config) and Crystal(crystal_config)
11. Attach HKL grid: `crystal.set_hkl_grid(hkl_grid)`
12. Attach ASU IDs: `crystal.set_hkl_ids_asu(...)` if has_halo and ids present
13. Construct Simulator(detector=detector, crystal=crystal, beam_config=beam_config, device=device, dtype=dtype)
14. Assemble metadata dict (device, dtype, hkl_count, has_halo, mask_provided, spot_scale_override, sqrt_scale, plus calibration_metadata)
15. Return (simulator, normalized_mask, sqrt_scale, metadata)

### Validation Protocol
- **Compilation:** `python -c "from dbex.refinement.helpers import create_unified_simulator"`
- **Regression Guard:** DB-AT-024 mapping parity (zero-iteration forward model, independent from factory)

### Decision Paths
- **Path A:** Factory + regression PASS → B1 COMPLETE, proceed to B2 wiring
- **Path B:** Compilation FAIL → fix import/syntax, retry
- **Path C:** Regression FAIL → revert accidental edits, isolate factory
- **Path D:** Factory logic bug → fix validation/normalization/sqrt_scale, retry

## Pitfalls To Avoid

1. **DO NOT wire factory to callers** — Phase B1 is factory implementation ONLY (wiring in Phase B2)
2. **Lazy imports MANDATORY** — Import nanobrag_torch INSIDE function to avoid circular deps
3. **Post-run sqrt_scale** — Compute sqrt NOW, but CALLER applies after simulator.run() per SCALE-004
4. **Mask device/dtype** — Must match hkl_grid device/dtype, not hardcoded float32
5. **Mask shape validation** — Must match (pixels_slow, pixels_fast) from detector_config
6. **HKL shape validation** — Must be (3, N), raise ValueError if not
7. **Device/dtype coercion** — Use hkl_grid defaults if device/dtype not provided
8. **Metadata preservation** — Return calibration_metadata unmodified in metadata dict
9. **Protected Assets** — DO NOT touch simulate_forward_once, simulate_forward_torch, refine_one, nanobrag_refinement (Phase B2)
10. **Environment Freeze** — No package installs, dbex-only changes

## If Blocked

**Compilation FAIL (imports):**
- Log error in `blocker_imports.md`
- Check nanobrag_torch import paths (Simulator vs models.Simulator)
- Commit factory stub with TODOs, return to Galph

**Regression Guard FAIL (DB-AT-024):**
- Log error in `blocker_regression.md`
- Verify no accidental edits to simulate_forward_once or other forward helpers
- Commit factory-only changes if isolated, return to Galph

**Factory logic unclear:**
- Log questions in `blocker_factory_logic.md`
- Review SCALE-004 finding for sqrt_scale rationale
- Review ARCH-ENGINE-002 for lazy import pattern
- Commit partial implementation with TODOs, return to Galph

**Mask normalization unclear:**
- Log questions in `blocker_mask_normalization.md`
- Check existing mask conversion in simulate_forward_torch (reference implementation)
- Commit factory without mask handling, return to Galph

## Findings Applied

- **SCALE-004:** Calibration sqrt_spot_scale applied POST-RUN (factory computes sqrt, caller applies)
- **ARCH-ENGINE-002:** Lazy imports + telemetry packaging (factory uses lazy imports)
- **POLICY-001:** Environment Freeze (no engine patches, dbex-only changes)
- **GEOMETRY-001/002:** DIALS beam-center + Euler (handled upstream in config hydration, factory agnostic)
- **PERF-WARM-001:** Warm-cache OFF pattern (Phase B2 tests will force cache OFF, factory itself cache-agnostic)

## Pointers

- **Implementation plan:** `plans/active/TORCH-API-ALIGN-001/implementation.md:61-64` (B1 factory specification)
- **Spec references:** `docs/nanobrag_api.md:44-47` (Simulator constructor), `docs/spec-db-workflow.md §5` (per-panel simulation)
- **SCALE-004 finding:** `docs/findings.md` (sqrt_spot_scale post-run pattern)
- **ARCH-ENGINE-002 finding:** `docs/findings.md` (lazy imports pattern)
- **Reference implementation:** `dbex/nanobrag_bridge.py:simulate_forward_torch` (mask normalization ~lines 800-820)

## Next Up

After Phase B1 complete (factory implemented + regression guard PASS):
1. **Phase B2a:** Wire simulate_forward_once + simulate_forward_torch to use factory (~80 lines changes, validate DB-AT-024 with factory)
2. **Phase B2b:** Wire refine_one CLI path + nanobrag_refinement panel loops to use factory (~120 lines changes, validate smoke tests)
3. **Phase B3:** Implement ExperimentModel adapter behind explicit flag (default OFF, ~200 lines, validate A3 parity test)
