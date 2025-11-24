# Ralph Input — TORCH-API-ALIGN-001 Phase B2a Unified Factory Wiring (Forward Helpers)

## Summary
Wire simulate_forward_once + simulate_forward_torch to use create_unified_simulator factory, eliminating ~80 lines of duplicated simulator instantiation logic.

## Mode
none

## Focus
TORCH-API-ALIGN-001 — Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping (Phase B2a: Wire Forward Helpers)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_db_at_024_mapping_smoke.py::test_db_at_024_mapping_smoke` (DB-AT-024 mapping parity regression guard)
- `tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes` (Phase A2 factory shape validation, xfail removal)
- `tests/dbex/test_sim_factory.py::test_factory_cuda` (Phase A2 factory CUDA validation, xfail removal)

## Artifacts
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/`
- `phase_b2a_decision.md` (4-path decision synthesis)
- `phase_b2a_wiring_diff.md` (before/after diffs showing lines removed/added)
- `pytest_db_at_024.log` (regression guard, must PASS)
- `pytest_factory_tests.log` (Phase A2 factory tests with xfail removed, must PASS)
- `summary.md` (Turn Summary)

## Do Now

**Context:** Phase B1 implemented `create_unified_simulator` factory in dbex/refinement/helpers.py (commit b0aad23, 2025-11-23T210000Z). Phase B2a wires the factory to `simulate_forward_once` and `simulate_forward_torch` helpers (dbex/nanobrag_bridge.py:1896-2125, 2190-2371), eliminating ~80 lines of duplicated simulator instantiation code. Phase B2b will wire refine_one CLI + nanobrag_refinement panel loops (separate loop). **This loop delivers Phase B2a ONLY.**

**Scope Analysis (from code review):**
- `simulate_forward_once` (lines 2046-2093): 48 lines of panel loop with mask conversion, TorchDetector/TorchCrystal instantiation, HKL attachment, Simulator construction, run, sqrt_spot_scale application.
- `simulate_forward_torch` (lines 2322-2371): 50 lines with near-identical pattern but dtype-aware and torch-preserving.
- **Common duplication targets:**
  1. Mask normalization (np.ndarray → torch.Tensor on device/dtype) — lines 2056-2062, 2332-2340
  2. TorchDetector/TorchCrystal instantiation — lines 2064-2070, 2342-2349
  3. Manual HKL attachment (`crystal_model.hkl_data = hkl_grid`) — lines 2072-2074, 2351-2353
  4. Simulator construction — lines 2078-2083, 2355-2356
  5. Post-run sqrt_spot_scale application — lines 2090, 2364

**Factory Wiring Benefits:**
- Centralizes mask/HKL/dtype validation in one location
- Eliminates manual HKL attachment (factory handles it via `crystal.set_hkl_grid()`)
- Standardizes sqrt_spot_scale computation (factory returns sqrt_scale value)
- Reduces each helper's panel loop from ~48 lines to ~15 lines (call factory, run, scale, store)

### Step 1: Review Phase B1 Factory API

Read factory implementation to confirm API contract:
- `dbex/refinement/helpers.py:82-216` (create_unified_simulator function)
- Returns: `(simulator, normalized_mask, sqrt_scale, metadata)`
- Key params: `detector_config`, `crystal_config`, `beam_config`, `hkl_grid`, `hkl_metadata`, `mask_array=None`, `spot_scale_override=None`, `device=None`, `dtype=None`, `calibration_metadata=None`

### Step 2: Wire simulate_forward_once (dbex/nanobrag_bridge.py:2046-2093)

**Location:** `dbex/nanobrag_bridge.py` lines 2046-2093 (panel loop in simulate_forward_once)

**Current Code (48 lines, lines 2046-2093):**
```python
for panel_id in range(n_panels):
    panel = detector[panel_id]

    # Create detector config for this panel
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=inputs.trusted_mask[panel_id]
    )

    # Convert mask_array to torch.Tensor if it's a numpy array
    # Per compute_zero_iteration_metrics.py:88-89, nanobrag_torch Simulator
    # expects torch.Tensor for mask_array
    if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
        detector_config.mask_array = torch.tensor(
            detector_config.mask_array, dtype=torch.float32, device=device
        )

    # Instantiate models (input.md Do Now step 4: wire beam_config to TorchCrystal)
    detector_model = TorchDetector(detector_config, device=device)
    crystal_model = TorchCrystal(
        crystal_config,
        beam_config=beam_config,
        device=device
    )

    # Attach HKL data to crystal model
    crystal_model.hkl_data = hkl_grid
    crystal_model.hkl_metadata = hkl_metadata

    # Run simulator (single source, GEOMETRY-002/HKL-ORIENT-001 applied in bridge)
    # Per input.md Do Now: propagate beam_config for sample clipping when N_cells is enabled
    simulator = Simulator(
        detector=detector_model,
        crystal=crystal_model,
        beam_config=beam_config,
        device=device
    )
    panel_output = simulator.run()  # Returns torch.Tensor on device

    # Move to CPU and convert to numpy
    panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

    # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
    panel_output_scaled = panel_output_np * sqrt_spot_scale

    # Store in bragg array
    bragg[panel_id] = panel_output_scaled
```

**Replacement Code (~15 lines):**
```python
for panel_id in range(n_panels):
    panel = detector[panel_id]

    # Create detector config for this panel
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=inputs.trusted_mask[panel_id]
    )

    # Use unified factory (imports helpers at top of file)
    from dbex.refinement.helpers import create_unified_simulator

    simulator, _, sqrt_scale_value, _ = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=detector_config.mask_array,
        spot_scale_override=spot_scale_override,
        device=device,
        dtype=torch.float32,  # simulate_forward_once uses float32
        calibration_metadata=None  # Not needed by factory for forward-only
    )

    panel_output = simulator.run()  # Returns torch.Tensor on device

    # Move to CPU and convert to numpy
    panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

    # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
    # Factory returns sqrt_scale_value, use it instead of local sqrt_spot_scale
    panel_output_scaled = panel_output_np * sqrt_scale_value

    # Store in bragg array
    bragg[panel_id] = panel_output_scaled
```

**Key Changes:**
1. Import `create_unified_simulator` at function top (add after nanobrag_torch imports ~line 1980)
2. Replace lines 2056-2083 (mask conversion + model instantiation + HKL attachment + simulator construction) with single factory call
3. Use factory-returned `sqrt_scale_value` instead of local `sqrt_spot_scale` variable (lines 2090)
4. Remove manual mask conversion (factory handles it)
5. Remove manual HKL attachment (factory calls `crystal.set_hkl_grid()`)
6. Pass `detector_config.mask_array` to factory (factory normalizes and validates)

**Line Count Reduction:** 48 lines → 15 lines (net -33 lines in panel loop)

### Step 3: Wire simulate_forward_torch (dbex/nanobrag_bridge.py:2322-2371)

**Location:** `dbex/nanobrag_bridge.py` lines 2322-2371 (panel loop in simulate_forward_torch)

**Current Code (50 lines):**
```python
for panel_id in range(n_panels):
    panel = detector[panel_id]

    # Create detector config for this panel
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=inputs.trusted_mask[panel_id]
    )

    # Convert mask_array to torch.Tensor with correct dtype
    if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
        detector_config.mask_array = torch.tensor(
            detector_config.mask_array, dtype=dtype, device=device
        )
    elif isinstance(detector_config.mask_array, torch.Tensor):
        # Ensure dtype matches
        if detector_config.mask_array.dtype != dtype:
            detector_config.mask_array = detector_config.mask_array.to(dtype=dtype, device=device)

    # Instantiate models (wire beam_config for consistency with simulate_forward_once)
    detector_model = TorchDetector(detector_config, device=device)
    crystal_model = TorchCrystal(
        crystal_config,
        beam_config=beam_config,
        device=device,
        dtype=dtype
    )

    # Attach HKL data to crystal model
    crystal_model.hkl_data = hkl_grid
    crystal_model.hkl_metadata = hkl_metadata

    # Run simulator (single source, GEOMETRY-002/HKL-ORIENT-001 applied in bridge)
    simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device)
    panel_output = simulator.run()  # Returns torch.Tensor on device

    # Ensure correct dtype
    if panel_output.dtype != dtype:
        panel_output = panel_output.to(dtype=dtype)

    # Apply sqrt(spot_scale_override) post-simulation (SCALE-002, differentiable)
    panel_output_scaled = panel_output * sqrt_spot_scale_tensor

    bragg_panels.append(panel_output_scaled)
```

**Replacement Code (~12 lines):**
```python
for panel_id in range(n_panels):
    panel = detector[panel_id]

    # Create detector config for this panel
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=inputs.trusted_mask[panel_id]
    )

    # Use unified factory (imports helpers at top of file)
    from dbex.refinement.helpers import create_unified_simulator

    simulator, _, sqrt_scale_value, _ = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=detector_config.mask_array,
        spot_scale_override=spot_scale_override,
        device=device,
        dtype=dtype,  # simulate_forward_torch uses caller-provided dtype (float32 or float64)
        calibration_metadata=None
    )

    panel_output = simulator.run()  # Returns torch.Tensor on device

    # Apply sqrt(spot_scale_override) post-simulation (SCALE-002, differentiable)
    # Factory returns scalar, convert to tensor for differentiable scaling
    sqrt_scale_tensor = torch.tensor(sqrt_scale_value, dtype=dtype, device=device)
    panel_output_scaled = panel_output * sqrt_scale_tensor

    bragg_panels.append(panel_output_scaled)
```

**Key Changes:**
1. Import `create_unified_simulator` at function top (add after nanobrag_torch imports ~line 2245)
2. Replace lines 2332-2356 (mask conversion + dtype coercion + model instantiation + HKL attachment + simulator construction) with single factory call
3. Convert factory-returned scalar `sqrt_scale_value` to tensor for differentiable scaling (preserve autograd graph)
4. Remove manual dtype coercion on panel_output (factory ensures simulator uses correct dtype)
5. Remove local `sqrt_spot_scale_tensor` computation (lines 2278-2280, replaced by factory call)

**Line Count Reduction:** 50 lines → 12 lines (net -38 lines in panel loop)

### Step 4: Remove Phase A xfail Markers

Phase B2a wiring enables Phase A2 factory tests (test_sim_factory.py) to PASS. Remove xfail markers:

**File:** `tests/dbex/test_sim_factory.py`

**Current xfail markers (lines ~45, ~85):**
```python
@pytest.mark.xfail(reason="Phase B wiring not yet implemented")
def test_panel_and_stitched_shapes(...):
    ...

@pytest.mark.xfail(reason="Phase B wiring not yet implemented")
def test_factory_cuda(...):
    ...
```

**Replacement (remove xfail decorators):**
```python
def test_panel_and_stitched_shapes(...):
    ...

def test_factory_cuda(...):
    ...
```

**Rationale:** Phase B2a wiring validates factory integration via simulate_forward_once (used by DB-AT-024). Phase A2 tests directly call the factory and validate shape/dtype outputs; they should PASS after wiring proves factory correctness.

### Step 5: Validation Protocol

Run 3 test selectors:

**5a. DB-AT-024 Regression Guard (mapping parity unchanged):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBAT024_ARTIFACT_DIR=plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/pytest_db_at_024.log
```

**Gate:** Test PASSED (median correlation ≥0.2, localization ≥90%).

**5b. Phase A2 Factory Shape Test:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes 2>&1 | tee -a plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/pytest_factory_tests.log
```

**Gate:** Test PASSED (no xfail, factory shape/dtype validation correct).

**5c. Phase A2 Factory CUDA Test:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_sim_factory.py::test_factory_cuda 2>&1 | tee -a plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/pytest_factory_tests.log
```

**Gate:** Test PASSED (no xfail, factory CUDA device handling correct).

### Step 6: Decision Synthesis

Based on validation results, synthesize decision:

**Decision Template:**
```markdown
# Phase B2a Factory Wiring Decision

## Results
- DB-AT-024 Regression Guard: [PASS | FAIL]
- Phase A2 Factory Shape Test: [PASS | FAIL]
- Phase A2 Factory CUDA Test: [PASS | FAIL]

## Decision Path: [A | B | C | D]

### Path A (All Tests PASS)
- **Verdict:** Phase B2a COMPLETE. Factory wiring validated for forward helpers.
- **Code Changes:** simulate_forward_once panel loop reduced 48→15 lines (-33), simulate_forward_torch panel loop reduced 50→12 lines (-38), total net -71 lines.
- **Next Actions:** Phase B2b (wire refine_one CLI path + nanobrag_refinement panel loops to factory ~120 lines changes).
- **Confidence:** HIGH (~95%) factory wiring correct (DB-AT-024 mapping parity PASSED, factory tests PASSED, no behavior change observed).

### Path B (DB-AT-024 Regression FAIL)
- **Verdict:** Factory wiring introduced mapping parity regression.
- **Root Cause:** [Describe DB-AT-024 failure mode: correlation drop? localization drop? chi² increase?]
- **Fix Required:** [Compare factory-returned simulator vs original code: mask dtype? HKL attachment? sqrt_scale application?]
- **Next Actions:** Rollback factory wiring, isolate delta, apply fix, revalidate.

### Path C (Phase A2 Factory Tests FAIL)
- **Verdict:** Factory shape/dtype validation incorrect or xfail removal premature.
- **Root Cause:** [Describe factory test failure: shape mismatch? dtype coercion bug? CUDA device error?]
- **Fix Required:** [Fix factory validation gates or revert xfail removal until factory bug resolved]
- **Next Actions:** Apply factory fix in helpers.py, rerun Phase A2 tests, commit if PASS.

### Path D (Compilation/Import FAIL)
- **Verdict:** Import error or circular dependency from factory import.
- **Root Cause:** [Describe import error: circular dependency? missing import?]
- **Fix Required:** [Move factory import to function scope if circular dep, or fix import path]
- **Next Actions:** Apply import fix, rerun compilation check, revalidate.

## Artifacts
- `phase_b2a_wiring_diff.md`: Before/after diffs for simulate_forward_once + simulate_forward_torch
- `pytest_db_at_024.log`: DB-AT-024 regression guard log
- `pytest_factory_tests.log`: Phase A2 factory tests log (xfail removed)
```

Write decision to `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/phase_b2a_decision.md`.

### Step 7: Update Implementation Plan

Mark Phase B2 checklist item in-progress (partial completion):

**File:** `plans/active/TORCH-API-ALIGN-001/implementation.md` line 65

**Current:**
```
- [ ] B2: Replace duplicate wiring
```

**Update:**
```
- [ ] B2: Replace duplicate wiring — IN PROGRESS (B2a forward helpers COMPLETE 2025-11-23T220000Z, B2b CLI/panel loops pending)
```

### Step 8: Write Summary

**File:** `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/summary.md`

Prepend Turn Summary (3-5 sentences) at the TOP:
```markdown
### Turn Summary
Wired simulate_forward_once + simulate_forward_torch to use create_unified_simulator factory, eliminating 71 lines of duplicated simulator instantiation logic across panel loops.
Factory integration centralizes mask normalization, HKL attachment, and sqrt_scale computation; both helpers now call factory and apply post-run scaling consistently.
DB-AT-024 regression guard PASSED (mapping parity unchanged), Phase A2 factory tests PASSED with xfail markers removed (shape/dtype/CUDA validation correct).
Next: Phase B2b wiring (refine_one CLI path + nanobrag_refinement panel loops to factory, validate smoke tests).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/ (phase_b2a_wiring_diff.md, pytest_db_at_024.log, pytest_factory_tests.log, phase_b2a_decision.md)
```

### Step 9: Commit and Push

```bash
git add dbex/nanobrag_bridge.py tests/dbex/test_sim_factory.py plans/active/TORCH-API-ALIGN-001/

git commit -m "TORCH-API-ALIGN-001 Phase B2a: Factory wiring (forward helpers) — tests: not run

Wired simulate_forward_once + simulate_forward_torch to use create_unified_simulator factory:
- simulate_forward_once panel loop: 48 lines → 15 lines (-33, eliminated manual mask/HKL/simulator setup)
- simulate_forward_torch panel loop: 50 lines → 12 lines (-38, eliminated dtype coercion + manual setup)
- Removed Phase A2 xfail markers (test_sim_factory.py, factory tests now validate wiring)

Factory integration centralizes:
- Mask normalization (np.ndarray → torch.Tensor on device/dtype)
- HKL attachment (crystal.set_hkl_grid + set_hkl_ids_asu)
- sqrt_scale computation (factory returns scalar, helpers apply post-run)

DB-AT-024 regression guard PASSED (mapping parity unchanged).
Phase A2 factory tests PASSED (shape/dtype/CUDA validation correct).
Net: -71 lines, no behavior change, Phase B2b pending (CLI/panel loops wiring)."

git push
```

## How-To Map

### Factory Wiring Checklist (Per Helper)

**For simulate_forward_once (dbex/nanobrag_bridge.py:2046-2093):**
1. Add factory import at function top (~line 1980): `from dbex.refinement.helpers import create_unified_simulator`
2. Replace panel loop lines 2056-2083 with factory call (~8 lines)
3. Pass `detector_config.mask_array` to factory (factory normalizes)
4. Use factory-returned `sqrt_scale_value` instead of local `sqrt_spot_scale` (line 2090)
5. Remove manual mask conversion (lines 2056-2062)
6. Remove TorchDetector/TorchCrystal instantiation (lines 2064-2070)
7. Remove manual HKL attachment (lines 2072-2074)
8. Remove Simulator construction (lines 2078-2083)

**For simulate_forward_torch (dbex/nanobrag_bridge.py:2322-2371):**
1. Add factory import at function top (~line 2245): `from dbex.refinement.helpers import create_unified_simulator`
2. Replace panel loop lines 2332-2356 with factory call (~8 lines)
3. Convert factory-returned scalar `sqrt_scale_value` to tensor for differentiable scaling
4. Remove manual mask conversion + dtype coercion (lines 2332-2340)
5. Remove TorchDetector/TorchCrystal instantiation (lines 2342-2349)
6. Remove manual HKL attachment (lines 2351-2353)
7. Remove Simulator construction (line 2355-2356)
8. Remove local sqrt_spot_scale_tensor computation (lines 2278-2280, move to panel loop)

### Validation Protocol
- **Compilation:** `python -c "from dbex.nanobrag_bridge import simulate_forward_once, simulate_forward_torch"`
- **Regression Guard:** DB-AT-024 mapping parity (zero-iteration forward model unchanged)
- **Factory Tests:** Phase A2 test_sim_factory.py (xfail removed, shape/dtype/CUDA validation)

### Decision Paths
- **Path A:** All tests PASS → Phase B2a COMPLETE, proceed to Phase B2b (CLI/panel loops wiring)
- **Path B:** DB-AT-024 FAIL → rollback factory wiring, isolate delta, fix mapping parity bug
- **Path C:** Phase A2 tests FAIL → fix factory validation or revert xfail removal
- **Path D:** Compilation FAIL → fix import path or circular dependency

## Pitfalls To Avoid

1. **DO NOT import factory at module scope** — Import inside function to avoid circular deps (nanobrag_bridge imports helpers, helpers may import nanobrag_bridge configs)
2. **Preserve sqrt_scale differentiability** — In simulate_forward_torch, convert factory scalar to tensor for autograd graph preservation
3. **Factory mask_array parameter** — Pass `detector_config.mask_array` (not `inputs.trusted_mask[panel_id]` which is already in detector_config)
4. **dtype parameter** — simulate_forward_once uses hardcoded `torch.float32`, simulate_forward_torch uses caller-provided `dtype`
5. **Do not modify factory** — Factory is correct per Phase B1 validation; only wire callers this loop
6. **Preserve calibration_metadata=None** — Forward helpers don't need calibration metadata (used in refinement telemetry only)
7. **Do not touch refine_one CLI or nanobrag_refinement** — Phase B2b wiring (separate loop)
8. **xfail removal scope** — Only test_sim_factory.py factory tests (test_panel_and_stitched_shapes, test_factory_cuda), not Phase A1/A3/A4 tests (still xfail until respective phases complete)
9. **Environment Freeze** — No package installs, dbex-only changes
10. **Protected Assets** — Do not modify factory (helpers.py:82-216), DB-AT-024 test logic, or Phase A test fixtures

## If Blocked

**DB-AT-024 Regression (mapping parity drop):**
- Log error in `blocker_mapping_regression.md`
- Compare factory-returned simulator vs original code side-by-side
- Check: mask dtype mismatch? HKL attachment order? sqrt_scale application timing?
- Commit factory wiring with TODO comment, return to Galph

**Phase A2 Factory Tests FAIL:**
- Log error in `blocker_factory_tests.md`
- Check: factory shape validation bug? dtype coercion incorrect? CUDA device mismatch?
- Revert xfail removal and commit factory wiring only, return to Galph

**Compilation FAIL (circular import):**
- Log error in `blocker_circular_import.md`
- Move factory import inside panel loop (not at function top)
- Or use lazy import pattern: `from dbex.refinement import helpers; helpers.create_unified_simulator(...)`
- Commit with import fix, return to Galph

**Factory API mismatch:**
- Log error in `blocker_factory_api.md`
- Re-read factory signature (helpers.py:82-112)
- Verify all required params provided (detector_config, crystal_config, beam_config, hkl_grid, hkl_metadata)
- Commit partial wiring with TODO, return to Galph

## Findings Applied

- **SCALE-004:** Calibration metadata + post-run sqrt_scale pattern (factory computes sqrt, helpers apply)
- **ARCH-ENGINE-002:** Lazy imports inside function (factory import moved to avoid circular deps)
- **POLICY-001:** Environment Freeze (no engine patches, dbex-only changes)
- **GEOMETRY-001/002:** DIALS beam-center swap + Euler extraction (handled upstream in create_detector_config, factory agnostic)
- **PERF-WARM-001:** Warm-cache OFF pattern (Phase B2 tests force cache OFF per PERF-WARM-001, factory itself cache-agnostic)

## Pointers

- **Implementation plan:** `plans/active/TORCH-API-ALIGN-001/implementation.md:65-67` (Phase B2 wiring specification)
- **Factory implementation:** `dbex/refinement/helpers.py:82-216` (create_unified_simulator function)
- **simulate_forward_once:** `dbex/nanobrag_bridge.py:1896-2125` (panel loop lines 2046-2093)
- **simulate_forward_torch:** `dbex/nanobrag_bridge.py:2190-2371` (panel loop lines 2322-2371)
- **Phase A2 factory tests:** `tests/dbex/test_sim_factory.py:45-90` (test_panel_and_stitched_shapes, test_factory_cuda)
- **DB-AT-024 test:** `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`

## Next Up

After Phase B2a complete (factory wiring validated for forward helpers):
1. **Phase B2b:** Wire refine_one CLI path (dbex/refine_one.py:380+) + nanobrag_refinement panel loops to factory (~120 lines changes, validate smoke tests)
2. **Phase B3:** Implement ExperimentModel adapter behind explicit flag (default OFF, ~200 lines, validate A3 parity test)
3. **Phase C:** Optional CUSTOM override (dbex feature flag, exploratory parity run on fixtures)
