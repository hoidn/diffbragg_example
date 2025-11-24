# Ralph Input — TORCH-API-ALIGN-001 Phase B3 ExperimentModel Adapter

## Summary
Implement ExperimentModel adapter path behind explicit flag (default OFF) for parity testing against factory baseline.

## Mode
none

## Focus
TORCH-API-ALIGN-001 — Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping (Phase B3: ExperimentModel Adapter)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_experiment_parity.py::test_parity_small_fixture` (Phase A3 — Primary validation, remove xfail marker)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (DB-AT-024 regression guard, adapter NOT used)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Stage A smoke regression guard, adapter NOT used)

## Artifacts
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/`
- `phase_b3_decision.md` (4-path decision synthesis)
- `pytest_experiment_parity.log` (Phase A3 test, must PASS within 1e-6 tolerance)
- `pytest_db_at_024.log` (regression guard, must PASS)
- `pytest_stage_a_expansion.log` (smoke regression guard, must PASS)
- `summary.md` (Turn Summary)

## Do Now

**Context:** Phase B2 COMPLETE (2025-11-24T000000Z) — all forward-only simulation paths use unified factory (forward helpers + refine_one CLI, -79 lines). Phase B3 implements ExperimentModel adapter per implementation.md:68-71: thin wrapper behind flag (default OFF), parity-first, no loss/warm-cache changes. API verification confirms `ExperimentModel` exists in nanobrag_torch.models.experiment with expected signature matching docs/nanobrag_api.md.

**Objective:** Add ~100-150 lines adapter function + wire Phase A3 test to validate ExperimentModel(param_init="frozen") parity against factory baseline within 1e-6 tolerance.

### Step 1: Verify ExperimentModel API

Confirm import and constructor signature:
```bash
python3 -c "from nanobrag_torch.models.experiment import ExperimentModel; import inspect; print(inspect.signature(ExperimentModel.__init__))"
```

**Expected output:**
```
(self, crystal_config: 'CrystalConfig', detector_config: 'DetectorConfig', beam_config: 'BeamConfig', device: 'Optional[torch.device]' = None, dtype: 'torch.dtype' = torch.float32, param_init: 'str' = 'frozen', hkl_data: 'Optional[torch.Tensor]' = None, hkl_metadata: 'Optional[dict]' = None) -> 'None'
```

If signature differs, document exact signature in blocker report and return to Galph.

### Step 2: Implement ExperimentModel Adapter

**Location:** `dbex/refinement/helpers.py` (after `create_unified_simulator` function, before module end)

**Function Signature:**
```python
def simulate_via_experiment_model(
    detector_config,
    crystal_config,
    beam_config,
    hkl_grid,
    hkl_metadata,
    mask_array=None,
    spot_scale_override=None,
    device=None,
    dtype=torch.float32,
    calibration_metadata=None
):
    """
    Thin adapter wrapping ExperimentModel(param_init="frozen") for parity testing.

    This adapter provides a parity path using the nanobrag_torch ExperimentModel API
    (docs/nanobrag_api.md) to validate shape/dtype/device consistency and output
    correctness against the unified simulator factory (create_unified_simulator).

    Args:
        detector_config: DetectorConfig instance
        crystal_config: CrystalConfig instance
        beam_config: BeamConfig instance (optional, can be None)
        hkl_grid: torch.Tensor (h_range, k_range, l_range) structure factors
        hkl_metadata: dict with 'has_halo', 'hkl_ids_asu' keys
        mask_array: Optional np.ndarray or torch.Tensor mask (normalized inside adapter)
        spot_scale_override: Optional float for post-run scaling (default 1.0)
        device: Optional torch.device (default from hkl_grid)
        dtype: torch.dtype (default torch.float32)
        calibration_metadata: Optional dict (stored in metadata, not used for construction)

    Returns:
        Tuple[torch.Tensor, float, dict]:
            - image: (spixels, fpixels) float tensor on device/dtype
            - sqrt_scale_value: float (sqrt of spot_scale_override) for CALLER to apply post-run
            - metadata: dict with {'device', 'dtype', 'hkl_count', 'has_halo', 'mask_provided', 'spot_scale_override', 'sqrt_scale', 'calibration_metadata', 'adapter': 'ExperimentModel'}

    Notes:
        - This adapter is behind an explicit flag (default OFF) for parity testing only.
        - param_init="frozen" ensures no trainable parameters (forward-only mode).
        - Post-run sqrt_scale application is CALLER's responsibility (matching factory pattern per SCALE-004).
        - Lazy imports nanobrag_torch.models.experiment.ExperimentModel inside function (ARCH-ENGINE-002).

    Findings Applied:
        - ARCH-ENGINE-002: Lazy imports
        - SCALE-004: Post-run sqrt_scale pattern
        - POLICY-001: Environment Freeze (ExperimentModel exists, no patches)
    """
    # Lazy import to avoid circular deps
    from nanobrag_torch.models.experiment import ExperimentModel

    # Device/dtype defaults from hkl_grid
    if device is None:
        device = hkl_grid.device
    if dtype is None:
        dtype = hkl_grid.dtype

    # Validate HKL grid shape (3D: h_range x k_range x l_range)
    if hkl_grid.ndim != 3:
        raise ValueError(f"HKL grid must be 3D (h, k, l), got shape {hkl_grid.shape}")
    if hkl_grid.device != device or hkl_grid.dtype != dtype:
        hkl_grid = hkl_grid.to(device=device, dtype=dtype)

    # Compute sqrt(spot_scale_override) for CALLER to apply post-run (SCALE-004)
    import math
    spot_scale_val = 1.0 if spot_scale_override is None else spot_scale_override
    sqrt_scale_value = math.sqrt(spot_scale_val)

    # Instantiate ExperimentModel with param_init="frozen" (no trainable parameters)
    experiment = ExperimentModel(
        crystal_config=crystal_config,
        detector_config=detector_config,
        beam_config=beam_config,
        device=device,
        dtype=dtype,
        param_init="frozen",
        hkl_data=hkl_grid,
        hkl_metadata=hkl_metadata
    )

    # Run forward pass
    image = experiment()

    # Validate output shape/dtype
    expected_shape = (detector_config.spixels, detector_config.fpixels)
    if image.shape != expected_shape:
        raise ValueError(f"ExperimentModel output shape {image.shape} != expected {expected_shape}")
    if image.dtype != dtype:
        raise ValueError(f"ExperimentModel output dtype {image.dtype} != expected {dtype}")
    if image.device != device:
        raise ValueError(f"ExperimentModel output device {image.device} != expected {device}")

    # Assemble metadata
    metadata = {
        'device': str(device),
        'dtype': str(dtype),
        'hkl_count': hkl_grid.shape[0] * hkl_grid.shape[1] * hkl_grid.shape[2],
        'has_halo': hkl_metadata.get('has_halo', False),
        'mask_provided': mask_array is not None,
        'spot_scale_override': spot_scale_val,
        'sqrt_scale': sqrt_scale_value,
        'adapter': 'ExperimentModel',
        'param_init': 'frozen'
    }
    if calibration_metadata is not None:
        metadata['calibration_metadata'] = calibration_metadata

    return image, sqrt_scale_value, metadata
```

**Key Design Decisions:**
1. **Lazy import** ExperimentModel inside function (ARCH-ENGINE-002 pattern)
2. **param_init="frozen"** ensures no trainable parameters (forward-only mode)
3. **HKL attachment** via constructor args `hkl_data`/`hkl_metadata` (per API verification)
4. **sqrt_scale computation** matches factory pattern (SCALE-004): returned for CALLER to apply post-run
5. **Shape/dtype validation** ensures output matches expected (spixels, fpixels) on device/dtype
6. **Metadata assembly** includes adapter type marker for telemetry/debugging

**Line Count:** ~100-120 lines (function body ~80 lines, docstring ~40 lines)

### Step 3: Wire Phase A3 Test (Remove xfail, Implement Parity Check)

**Location:** `tests/dbex/test_experiment_parity.py::test_parity_small_fixture`

**Changes:**
1. Remove `@pytest.mark.xfail(reason="...")` decorator
2. Remove `pytest.skip("Phase B/C wiring pending")` guard
3. Implement parity check:

```python
def test_parity_small_fixture(warm_cache_off):
    """
    Validates ExperimentModel parity against unified simulator factory.

    Tests:
    - ExperimentModel(param_init="frozen") outputs match factory within 1e-6
    - Shape/dtype/device consistency
    - Per-pixel max abs diff ≤ 1e-6
    """
    import torch
    import numpy as np
    from pathlib import Path
    from dbex.data_load import DataLoad
    from dbex.nanobrag_bridge import create_detector_config, create_beam_config, create_crystal_config
    from dbex.refinement.helpers import create_unified_simulator, simulate_via_experiment_model

    # Load tiny dxtbx fixture (use same fixture as test_stage_a_expansion for consistency)
    base_path = Path(__file__).parent.parent.parent / "dbex_files" / "refGeom"
    expt_path = base_path / "refGeom.expt"
    mtz_path = base_path / "refGeom_gen.mtz"

    # Construct DataLoad (minimal Args object)
    class Args:
        def __init__(self):
            self.exptName = str(expt_path)
            self.mtzFile = str(mtz_path)
            self.mtzCol = "F,SIGF"

    args = Args()
    DL = DataLoad(args)

    # Get HKL grid and metadata (from DataLoad)
    hkl_grid = DL.HKL_ARRAY  # torch.Tensor (3, N) or (h, k, l) 3D grid
    hkl_metadata = {'has_halo': False, 'hkl_ids_asu': None}  # Adjust if DL provides metadata

    # Single panel test (use panel 0)
    panel_id = 0
    panel = DL.detector[panel_id]

    # Create configs (no calibration metadata for simplicity)
    detector_config = create_detector_config(
        panel=panel,
        beam=DL.beam,
        trusted_mask=None  # Or DL.trusted_mask[panel_id] if available
    )
    beam_config = create_beam_config(DL.beam)
    crystal_config, _ = create_crystal_config(DL.crystal, DL.Expt)

    device = torch.device("cpu")
    dtype = torch.float32

    # Run factory path (baseline)
    simulator_factory, _, sqrt_scale_factory, metadata_factory = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=detector_config.mask_array,
        spot_scale_override=1.0,
        device=device,
        dtype=dtype,
        calibration_metadata=None
    )
    image_factory = simulator_factory.run()

    # Run ExperimentModel adapter path
    image_adapter, sqrt_scale_adapter, metadata_adapter = simulate_via_experiment_model(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=detector_config.mask_array,
        spot_scale_override=1.0,
        device=device,
        dtype=dtype,
        calibration_metadata=None
    )

    # Parity checks
    # 1. Shape/dtype/device consistency
    assert image_factory.shape == image_adapter.shape, \
        f"Shape mismatch: factory {image_factory.shape} != adapter {image_adapter.shape}"
    assert image_factory.dtype == image_adapter.dtype, \
        f"Dtype mismatch: factory {image_factory.dtype} != adapter {image_adapter.dtype}"
    assert image_factory.device == image_adapter.device, \
        f"Device mismatch: factory {image_factory.device} != adapter {image_adapter.device}"

    # 2. sqrt_scale consistency
    assert abs(sqrt_scale_factory - sqrt_scale_adapter) < 1e-9, \
        f"sqrt_scale mismatch: factory {sqrt_scale_factory} != adapter {sqrt_scale_adapter}"

    # 3. Per-pixel parity (max abs diff ≤ 1e-6)
    max_abs_diff = torch.max(torch.abs(image_factory - image_adapter)).item()
    assert max_abs_diff <= 1e-6, \
        f"Parity FAIL: max abs diff {max_abs_diff:.2e} > 1e-6 tolerance"

    # 4. Per-pixel MSE (informational)
    mse = torch.mean((image_factory - image_adapter) ** 2).item()
    print(f"[PARITY CHECK] ExperimentModel vs Factory: max_abs_diff={max_abs_diff:.2e}, MSE={mse:.2e}, sqrt_scale={sqrt_scale_factory}")

    # PASS if all assertions pass
```

**Key Implementation Notes:**
- Use `dbex_files/refGeom/refGeom.expt` + `refGeom_gen.mtz` (same fixture as test_stage_a_expansion)
- Single panel test (panel_id=0) for simplicity (~100x100 pixels, <10s execution)
- Parity tolerance: 1e-6 max abs diff (per implementation.md:8 acceptance criteria)
- Force warm-cache OFF via `warm_cache_off` fixture (already defined in test file)
- Device: CPU (CUDA test can be added later if needed)

### Step 4: Validation Protocol

Run 3 test selectors:

**4a. Phase A3 ExperimentModel Parity Test (PRIMARY):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_experiment_parity.py::test_parity_small_fixture 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/pytest_experiment_parity.log
```

**Gate:** Test PASSED (max abs diff ≤ 1e-6, shape/dtype/device match).

**4b. DB-AT-024 Regression Guard (adapter NOT used):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBAT024_ARTIFACT_DIR=plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/pytest_db_at_024.log
```

**Gate:** Test PASSED (median correlation ≥0.2, localization ≥90%).

**4c. Stage A Smoke Regression Guard (adapter NOT used):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/pytest_stage_a_expansion.log
```

**Gate:** Test PASSED (Stage A refinement completes, telemetry structure correct).

### Step 5: Decision Synthesis

Based on validation results, synthesize decision:

**Decision Template:**
```markdown
# Phase B3 ExperimentModel Adapter Decision

## Results
- Phase A3 ExperimentModel Parity Test: [PASS | FAIL]
  - Max abs diff: [value] (tolerance 1e-6)
  - MSE: [value]
  - Shape/dtype/device: [match | mismatch]
- DB-AT-024 Regression Guard: [PASS | FAIL]
- Stage A Expansion Smoke Test: [PASS | FAIL]

## Decision Path: [A | B | C | D]

### Path A (All Tests PASS)
- **Verdict:** Phase B3 COMPLETE. ExperimentModel adapter validated for parity within 1e-6 tolerance.
- **Code Changes:** helpers.py +~120 lines (adapter function), test_experiment_parity.py +~80 lines (parity check implementation), total +~200 lines.
- **Parity Metrics:** max_abs_diff=[value], MSE=[value], sqrt_scale=[value].
- **Next Actions:** Phase B3 COMPLETE. Mark implementation.md B3 checklist complete. Proceed to Phase C planning (optional CUSTOM override behind flag) OR Phase D planning (rollout & parity matrix).
- **Confidence:** HIGH (~95%) adapter correct (parity within tolerance, shape/dtype/device validated).

### Path B (ExperimentModel Parity FAIL — max abs diff > 1e-6)
- **Verdict:** ExperimentModel adapter produces different outputs than factory baseline.
- **Root Cause:** [Describe parity delta: max abs diff, spatial pattern, hypothesis for mismatch]
- **Fix Required:** [Debug ExperimentModel wiring vs factory: HKL attachment? detector config? beam config? spot_scale application?]
- **Next Actions:** Investigate delta source (compare ExperimentModel vs Simulator internal wiring), adjust adapter or tolerance, revalidate. If delta is systematic and acceptable (<1e-5), document in findings and adjust tolerance.

### Path C (Regression Guard FAIL — DB-AT-024 or Stage A smoke)
- **Verdict:** Adapter implementation introduced unintended side effects.
- **Root Cause:** [Describe regression: mapping parity drop? Stage A convergence failure?]
- **Fix Required:** [Check for global state mutation, import side effects, factory logic contamination]
- **Next Actions:** Rollback adapter, isolate contamination source, apply fix, revalidate.

### Path D (API Mismatch — Import/Constructor FAIL)
- **Verdict:** ExperimentModel API differs from specification.
- **Root Cause:** [Describe API mismatch: signature difference? missing method?]
- **Fix Required:** [Update adapter to match actual API, or document blocker if API unavailable]
- **Next Actions:** Document exact API signature, consult nanobrag_torch source, adjust adapter or mark Phase B3 blocked.

## Artifacts
- `phase_b3_decision.md` (this file)
- `pytest_experiment_parity.log` (Phase A3 test, PRIMARY validation)
- `pytest_db_at_024.log` (DB-AT-024 regression guard)
- `pytest_stage_a_expansion.log` (Stage A smoke regression guard)
```

Write decision to `plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/phase_b3_decision.md`.

### Step 6: Update Implementation Plan

Mark Phase B3 checklist item complete:

**File:** `plans/active/TORCH-API-ALIGN-001/implementation.md` line 68

**Current:**
```
- [ ] B3: ExperimentModel adapter
```

**Update:**
```
- [x] B3: ExperimentModel adapter — COMPLETE 2025-11-24T044933Z (adapter function ~120 lines, Phase A3 test wired and PASSED with max_abs_diff≤1e-6, regression guards PASSED)
```

### Step 7: Update Test Registry

**File:** `docs/TESTING_GUIDE.md` §2

Add/update Phase A3 test row (change status from "Active (xfail)" to "Active"):
```markdown
| DB-API-A3: ExperimentModel Parity (param_init="frozen") | `tests/dbex/test_experiment_parity.py::test_parity_small_fixture` | active | `docs/nanobrag_api.md:109-220`, `plans/active/TORCH-API-ALIGN-001/implementation.md:50-54` | TORCH-API-ALIGN-001 Phase A3. Validates ExperimentModel(param_init="frozen") outputs match unified simulator factory within 1e-6 max abs diff. Single panel test on tiny fixture (refGeom.expt), warm-cache OFF, NANOBRAGG_DISABLE_COMPILE=1. [FINDINGS: tbd] [ENV: NANOBRAGG_DISABLE_COMPILE=1] [ADDED: 2025-11-23] [XFAIL REMOVED: 2025-11-24] |
```

**File:** `docs/development/TEST_SUITE_INDEX.md`

Update corresponding row (remove xfail note, add parity metrics).

### Step 8: Write Summary and Commit

**File:** `plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/summary.md`

Prepend Turn Summary (3-5 sentences) at the TOP:
```markdown
### Turn Summary
Implemented ExperimentModel adapter function (~120 lines) in helpers.py wrapping param_init="frozen" mode for parity testing against factory baseline.
Wired Phase A3 test (test_experiment_parity.py) with parity check comparing ExperimentModel vs create_unified_simulator outputs within 1e-6 tolerance.
Validation results: [max_abs_diff, MSE, PASS/FAIL status].
Next: Phase B3 COMPLETE if parity PASSED; Phase C planning (optional CUSTOM override) OR Phase D planning (rollout & broader parity matrix).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/ (phase_b3_decision.md, pytest_experiment_parity.log, pytest_db_at_024.log, pytest_stage_a_expansion.log)
```

**Commit Message:**
```bash
git add dbex/refinement/helpers.py tests/dbex/test_experiment_parity.py docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md plans/active/TORCH-API-ALIGN-001/

git commit -m "TORCH-API-ALIGN-001 Phase B3: ExperimentModel adapter — tests: Phase A3 [PASS/FAIL], DB-AT-024 PASSED, Stage A smoke PASSED

Implemented simulate_via_experiment_model adapter (~120 lines) in dbex/refinement/helpers.py:
- Wraps ExperimentModel(param_init=\"frozen\") for parity testing
- Lazy imports per ARCH-ENGINE-002
- Post-run sqrt_scale computation per SCALE-004 (CALLER applies)
- Shape/dtype/device validation ensures (spixels, fpixels) consistency

Wired Phase A3 test (test_experiment_parity.py::test_parity_small_fixture):
- Removed xfail marker
- Implemented parity check: factory vs adapter within 1e-6 max abs diff
- Single panel test on refGeom.expt fixture (~100x100 px, <10s execution)
- Warm-cache OFF + NANOBRAGG_DISABLE_COMPILE=1 per PERF-WARM-001

Validation results:
- Phase A3 parity: [max_abs_diff, MSE, PASS/FAIL]
- DB-AT-024 regression guard: PASSED (mapping parity unchanged)
- Stage A smoke regression guard: PASSED (production path unaffected)

Phase B3 [COMPLETE/BLOCKED]: ExperimentModel adapter [validated/pending fixes].
Net: +~200 lines (adapter ~120, test wiring ~80), 0 regressions.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

## How-To Map

### Adapter Implementation Checklist (helpers.py)

1. Locate insertion point: after `create_unified_simulator` function (line ~217)
2. Add `simulate_via_experiment_model` function (~120 lines total: docstring ~40, body ~80)
3. Lazy import ExperimentModel inside function body: `from nanobrag_torch.models.experiment import ExperimentModel`
4. Device/dtype defaults from hkl_grid
5. HKL grid shape validation (must be 3D)
6. Compute sqrt_scale from spot_scale_override (math.sqrt)
7. Instantiate ExperimentModel with constructor args: crystal_config, detector_config, beam_config, device, dtype, param_init="frozen", hkl_data=hkl_grid, hkl_metadata=hkl_metadata
8. Call `experiment()` to get image
9. Validate output shape/dtype/device
10. Assemble metadata dict (include 'adapter': 'ExperimentModel', 'param_init': 'frozen')
11. Return (image, sqrt_scale_value, metadata)

### Test Wiring Checklist (test_experiment_parity.py)

1. Remove `@pytest.mark.xfail(...)` decorator (line 36)
2. Remove `pytest.skip("Phase B/C wiring pending")` guard (line 54)
3. Import helpers: `from dbex.refinement.helpers import create_unified_simulator, simulate_via_experiment_model`
4. Load fixture: DataLoad with refGeom.expt + refGeom_gen.mtz
5. Build configs: create_detector_config, create_beam_config, create_crystal_config (single panel)
6. Run factory path: create_unified_simulator
7. Run adapter path: simulate_via_experiment_model
8. Assert shape/dtype/device consistency
9. Assert sqrt_scale match (abs diff < 1e-9)
10. Assert per-pixel parity: max abs diff ≤ 1e-6
11. Print informational metrics (max_abs_diff, MSE, sqrt_scale)

### Validation Protocol

- **Compilation:** `python -c "from dbex.refinement.helpers import simulate_via_experiment_model"`
- **API Verification:** `python -c "from nanobrag_torch.models.experiment import ExperimentModel; import inspect; print(inspect.signature(ExperimentModel.__init__))"`
- **Parity Test:** Phase A3 test_experiment_parity.py (PRIMARY validation)
- **Regression Guards:** DB-AT-024 mapping parity + Stage A expansion smoke

### Decision Paths

- **Path A:** All tests PASS (parity ≤1e-6) → Phase B3 COMPLETE
- **Path B:** Parity FAIL (max abs diff >1e-6) → debug ExperimentModel wiring, adjust adapter or tolerance
- **Path C:** Regression FAIL → rollback, isolate side effects
- **Path D:** API mismatch → document blocker, consult nanobrag_torch source

## Pitfalls To Avoid

1. **Lazy import** — Import ExperimentModel inside function to avoid circular deps (ARCH-ENGINE-002)
2. **param_init="frozen"** — Do NOT use "stage_a" (trainable params), Phase B3 is parity-first forward-only mode
3. **sqrt_scale application** — Adapter RETURNS sqrt_scale, CALLER applies post-run (matching factory pattern per SCALE-004)
4. **HKL attachment** — Use constructor args `hkl_data`/`hkl_metadata` (per API verification), NOT `experiment.set_structure_factors` (method may not exist)
5. **Parity tolerance** — 1e-6 max abs diff per implementation.md:8, NOT 1e-5 or 1e-7
6. **Test fixture** — Use refGeom.expt (same as test_stage_a_expansion), NOT different fixture (consistency)
7. **Device** — CPU only for Phase B3 (CUDA test deferred), do NOT force GPU
8. **Warm-cache** — Force OFF via warm_cache_off fixture (PERF-WARM-001 pattern), do NOT enable
9. **Production paths** — Adapter is behind flag (default OFF), do NOT modify refine_one or nanobrag_refinement
10. **Environment Freeze** — No engine patches, ExperimentModel exists in nanobrag_torch (verified 2025-11-24T044933Z)

## If Blocked

**API Signature Mismatch:**
- Log actual signature in `blocker_api_mismatch.md`
- Compare against docs/nanobrag_api.md specification
- Consult nanobrag_torch source code (/home/ollie/Documents/nanoBragg/src/nanobrag_torch/models/experiment.py)
- Document exact mismatch, return to Galph with blocker report

**Parity FAIL (max abs diff > 1e-6):**
- Log parity delta in `blocker_parity_fail.md` with max_abs_diff, MSE, spatial pattern
- Compare ExperimentModel vs Simulator internals: HKL attachment? detector config? beam config?
- Check if delta is systematic (e.g., constant offset, scaling factor)
- If delta <1e-5 and systematic, document findings and propose tolerance adjustment
- Commit partial progress (adapter + test with XFAIL), return to Galph

**Regression FAIL (DB-AT-024 or Stage A smoke):**
- Log regression in `blocker_regression.md`
- Check for global state mutation (imports, factory contamination)
- Revert adapter changes, validate regression disappears
- Isolate contamination source (import side effects? factory shared state?)
- Commit revert, return to Galph with blocker report

**Import FAIL (ExperimentModel unavailable):**
- Log import error in `blocker_import_fail.md`
- Document exact error message + traceback
- Check nanobrag_torch installation (python3 -c "import nanobrag_torch; print(nanobrag_torch.__file__)")
- If ExperimentModel truly missing, Phase B3 is BLOCKED (Environment Freeze prevents install)
- Return to Galph with blocker report

## Findings Applied

- **ARCH-ENGINE-002:** Lazy imports inside adapter function to avoid circular deps
- **SCALE-004:** Post-run sqrt_scale computation (factory pattern consistency)
- **POLICY-001:** Environment Freeze (ExperimentModel exists, verified 2025-11-24T044933Z, no engine patches needed)
- **PERF-WARM-001:** Warm-cache OFF pattern in parity test (NANOBRAGG_DISABLE_COMPILE=1 fixture)
- **GEOMETRY-001/002:** DIALS beam-center swap + Euler extraction (handled upstream in bridge, adapter agnostic)

## Pointers

- **Implementation plan:** `plans/active/TORCH-API-ALIGN-001/implementation.md:68-71` (Phase B3 specification)
- **Phase B3 complexity assessment:** `plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/phase_b3_complexity_assessment.md`
- **ExperimentModel API docs:** `docs/nanobrag_api.md:109-220` (constructor, forward usage, param_init modes)
- **Factory implementation:** `dbex/refinement/helpers.py:82-216` (create_unified_simulator reference pattern)
- **Phase A3 test stub:** `tests/dbex/test_experiment_parity.py::test_parity_small_fixture`
- **DB-AT-024 regression guard:** `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
- **Stage A smoke regression guard:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

## Next Up

After Phase B3 complete (ExperimentModel adapter validated):
1. **Phase C:** Optional CUSTOM override (dbex feature flag for custom_fdet/sdet/odet + custom_beam_vector, default OFF, exploratory parity run per A4 test)
2. **Phase D:** Rollout & parity (flip adapter default ON with rollback flag, broader parity matrix, decide mid-term seam: factory via adapter or vice versa)
3. **Documentation:** Update docs/nanobrag_api.md import examples, docs/spec-db-workflow.md DIALS mapping note, findings.md with adapter parity results

## Doc Sync Plan

**Conditional:** Only if Phase A3 test collection changes (test status active → xfail removed):

1. Run `pytest --collect-only tests/dbex/test_experiment_parity.py::test_parity_small_fixture` to confirm 1 test collected (no xfail marker)
2. Archive log to `plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T044933Z/pytest_collect_phase_a3.log`
3. Update `docs/TESTING_GUIDE.md` §2: change Phase A3 row status from "Active (xfail)" to "Active" (xfail removed 2025-11-24)
4. Update `docs/development/TEST_SUITE_INDEX.md`: add parity metrics note to Phase A3 row

**Timing:** Update docs AFTER Phase A3 test PASSES (per Hard Gate rule).
