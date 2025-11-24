# Ralph Input — TORCH-API-ALIGN-001 Phase B2b(i) Unified Factory Wiring (refine_one CLI)

## Summary
Wire refine_one CLI forward simulation panel loop to use create_unified_simulator factory, eliminating ~65 lines of duplicated simulator instantiation logic.

## Mode
none

## Focus
TORCH-API-ALIGN-001 — Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping (Phase B2b(i): Wire refine_one CLI)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (DB-AT-024 mapping parity regression guard)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Stage A smoke regression guard)

## Artifacts
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/`
- `phase_b2b_i_decision.md` (4-path decision synthesis)
- `pytest_db_at_024.log` (regression guard, must PASS)
- `pytest_stage_a_expansion.log` (smoke test regression guard, must PASS)
- `summary.md` (Turn Summary)

## Do Now

**Context:** Phase B2a successfully wired simulate_forward_once + simulate_forward_torch to factory (commit 0e768c0, DB-AT-024 PASSED, 56 lines eliminated). Phase B2b wires remaining duplicate simulator instantiation locations. **This loop (Phase B2b(i)) wires ONLY refine_one.py CLI forward simulation panel loop** (lines 403-475, ~73 lines). Phase B2b(ii) will wire nanobrag_refinement panel loops (separate loop).

**Scope Analysis:** refine_one.py:403-475 panel loop has near-identical duplication pattern to Phase B2a helpers:
1. Config creation (detector_config, beam_config, crystal_config) — lines 407-436
2. Manual model instantiation (Detector, Crystal) — lines 439-440
3. Manual HKL attachment — lines 447-448
4. Simulator construction (with/without beam_config branch) — lines 451-465
5. Post-run sqrt_spot_scale application — line 472

**Factory Wiring Benefits:**
- Centralizes mask/HKL/dtype validation (proven correct in Phase B2a)
- Eliminates beam_config branching (factory accepts optional beam_config)
- Standardizes sqrt_spot_scale computation (factory returns sqrt_scale value)
- Reduces panel loop from ~73 lines to ~20 lines (call factory, run, scale, store)

### Step 1: Review Phase B2a Pattern

Confirm factory API usage pattern from Phase B2a (simulate_forward_once):
- Import factory inside function (lazy import to avoid circular deps)
- Pass detector_config, crystal_config, beam_config, hkl_grid, hkl_metadata to factory
- Use factory-returned sqrt_scale_value for post-run scaling
- Factory handles mask normalization, HKL attachment, model instantiation

### Step 2: Wire refine_one.py Panel Loop (Lines 403-475)

**Location:** `dbex/refine_one.py` lines 403-475 (panel loop in main() function)

**Current Code (73 lines):**
```python
for panel_id in range(n_panels):
    panel = DL.detector[panel_id]

    # Create configs for this panel
    detector_config = create_detector_config(
        panel=panel,
        beam=DL.beam,
        trusted_mask=inputs.trusted_mask[panel_id]
    )

    # Create beam config with optional calibration metadata (SCALE-005/SCALE-006)
    if calibration_metadata is not None:
        beam_config = create_beam_config(
            DL.beam,
            flux=calibration_metadata['beam_flux'],
            beamsize_mm=calibration_metadata['beamsize_mm'],
            exposure=calibration_metadata['beam_exposure']
        )
    else:
        beam_config = create_beam_config(DL.beam)

    # Create crystal config with optional N_cells (SCALE-005: gate sample clipping)
    apply_n_cells = (calibration_metadata is not None and
                    calibration_metadata['N_cells'] is not None)
    if calibration_metadata is not None and calibration_metadata['N_cells'] is not None:
        crystal_config, n_cells_applied = create_crystal_config(
            DL.crystal,
            DL.Expt,
            N_cells=calibration_metadata['N_cells'],
            apply_n_cells=apply_n_cells
        )
    else:
        crystal_config, n_cells_applied = create_crystal_config(DL.crystal, DL.Expt)

    # Instantiate models
    detector_model = Detector(detector_config, device=device, dtype=torch.float32)
    crystal_model = Crystal(crystal_config, device=device, dtype=torch.float32)

    # Attach HKL data to crystal model
    crystal_model.hkl_data = hkl_grid
    crystal_model.hkl_metadata = hkl_metadata

    # Run simulator with optional beam_config
    if calibration_metadata is not None:
        simulator = Simulator(
            detector=detector_model,
            crystal=crystal_model,
            beam_config=beam_config,
            device=device,
            dtype=torch.float32
        )
    else:
        simulator = Simulator(
            detector=detector_model,
            crystal=crystal_model,
            device=device,
            dtype=torch.float32
        )
    panel_output = simulator.run()

    # Move to CPU and convert to numpy
    panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

    # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
    panel_output_scaled = panel_output_np * sqrt_spot_scale

    # Store in Bragg array
    Bragg[panel_id] = panel_output_scaled
```

**Replacement Code (~20 lines):**
```python
for panel_id in range(n_panels):
    panel = DL.detector[panel_id]

    # Create configs for this panel
    detector_config = create_detector_config(
        panel=panel,
        beam=DL.beam,
        trusted_mask=inputs.trusted_mask[panel_id]
    )

    # Create beam config with optional calibration metadata (SCALE-005/SCALE-006)
    if calibration_metadata is not None:
        beam_config = create_beam_config(
            DL.beam,
            flux=calibration_metadata['beam_flux'],
            beamsize_mm=calibration_metadata['beamsize_mm'],
            exposure=calibration_metadata['beam_exposure']
        )
    else:
        beam_config = create_beam_config(DL.beam)

    # Create crystal config with optional N_cells (SCALE-005: gate sample clipping)
    apply_n_cells = (calibration_metadata is not None and
                    calibration_metadata['N_cells'] is not None)
    if calibration_metadata is not None and calibration_metadata['N_cells'] is not None:
        crystal_config, n_cells_applied = create_crystal_config(
            DL.crystal,
            DL.Expt,
            N_cells=calibration_metadata['N_cells'],
            apply_n_cells=apply_n_cells
        )
    else:
        crystal_config, n_cells_applied = create_crystal_config(DL.crystal, DL.Expt)

    # Use unified factory (imports helpers at function top)
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
        dtype=torch.float32,
        calibration_metadata=calibration_metadata
    )

    panel_output = simulator.run()

    # Move to CPU and convert to numpy
    panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

    # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
    panel_output_scaled = panel_output_np * sqrt_scale_value

    # Store in Bragg array
    Bragg[panel_id] = panel_output_scaled
```

**Key Changes:**
1. Import `create_unified_simulator` at function top (add after nanobrag_torch imports ~line 380)
2. Replace lines 439-465 (model instantiation + HKL attachment + Simulator construction) with single factory call
3. Pass `calibration_metadata` to factory (factory stores it in metadata dict, doesn't use it for construction)
4. Use factory-returned `sqrt_scale_value` instead of local `sqrt_spot_scale` variable (line 472)
5. Remove manual Detector/Crystal instantiation (lines 439-440)
6. Remove manual HKL attachment (lines 447-448)
7. Remove beam_config branching for Simulator construction (lines 451-465) - factory accepts optional beam_config

**Line Count Reduction:** 73 lines → 20 lines (net -53 lines in panel loop)

**Critical Note:** Config creation (detector_config, beam_config, crystal_config, lines 407-436) is KEPT because refine_one needs crystal_config for subsequent Stage A refinement call (`run_nanobrag_refinement` at line 510). Do NOT move config creation inside factory call or defer it.

### Step 3: Validation Protocol

Run 2 test selectors:

**3a. DB-AT-024 Regression Guard (mapping parity unchanged):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBAT024_ARTIFACT_DIR=plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/pytest_db_at_024.log
```

**Gate:** Test PASSED (median correlation ≥0.2, localization ≥90%).

**3b. Stage A Expansion Smoke Test (refine_one CLI regression guard):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/pytest_stage_a_expansion.log
```

**Gate:** Test PASSED (Stage A refinement completes successfully, telemetry structure correct).

### Step 4: Decision Synthesis

Based on validation results, synthesize decision:

**Decision Template:**
```markdown
# Phase B2b(i) refine_one CLI Wiring Decision

## Results
- DB-AT-024 Regression Guard: [PASS | FAIL]
- Stage A Expansion Smoke Test: [PASS | FAIL]

## Decision Path: [A | B | C | D]

### Path A (All Tests PASS)
- **Verdict:** Phase B2b(i) COMPLETE. Factory wiring validated for refine_one CLI.
- **Code Changes:** refine_one.py panel loop reduced 73→20 lines (-53), config creation preserved for downstream Stage A refinement.
- **Next Actions:** Phase B2b(ii) (wire nanobrag_refinement Stage B/C panel loops to factory ~60 lines changes, validate Stage B/C smokes).
- **Confidence:** HIGH (~95%) factory wiring correct (DB-AT-024 PASSED, Stage A smoke PASSED, no behavior change observed).

### Path B (DB-AT-024 Regression FAIL)
- **Verdict:** Factory wiring introduced mapping parity regression.
- **Root Cause:** [Describe DB-AT-024 failure mode]
- **Fix Required:** [Isolate delta, compare factory vs original code]
- **Next Actions:** Rollback factory wiring, apply fix, revalidate.

### Path C (Stage A Smoke FAIL)
- **Verdict:** Factory wiring broke refine_one CLI or Stage A refinement path.
- **Root Cause:** [Describe test failure: compilation error? telemetry mismatch? convergence failure?]
- **Fix Required:** [Check config creation preservation, beam_config wiring, sqrt_scale application]
- **Next Actions:** Apply fix, rerun smoke test, commit if PASS.

### Path D (Compilation/Import FAIL)
- **Verdict:** Import error or circular dependency from factory import.
- **Root Cause:** [Describe import error]
- **Fix Required:** [Move factory import to function scope if circular dep]
- **Next Actions:** Apply import fix, rerun compilation check, revalidate.

## Artifacts
- `phase_b2b_i_decision.md` (this file)
- `pytest_db_at_024.log` (DB-AT-024 regression guard)
- `pytest_stage_a_expansion.log` (Stage A smoke test)
```

Write decision to `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/phase_b2b_i_decision.md`.

### Step 5: Update Implementation Plan

Mark Phase B2 checklist item partial progress:

**File:** `plans/active/TORCH-API-ALIGN-001/implementation.md` line 65

**Current:**
```
- [ ] B2: Replace duplicate wiring — IN PROGRESS (B2a forward helpers COMPLETE 2025-11-23T220000Z, B2b CLI/panel loops pending)
```

**Update:**
```
- [ ] B2: Replace duplicate wiring — IN PROGRESS (B2a forward helpers COMPLETE 2025-11-23T220000Z, B2b(i) refine_one CLI COMPLETE 2025-11-23T240000Z, B2b(ii) nanobrag_refinement panel loops pending)
```

### Step 6: Write Summary

**File:** `plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/summary.md`

Prepend Turn Summary (3-5 sentences) at the TOP:
```markdown
### Turn Summary
Wired refine_one CLI forward simulation panel loop to use create_unified_simulator factory, eliminating 53 lines of duplicated simulator instantiation logic.
Factory integration centralizes model instantiation, HKL attachment, and sqrt_scale computation while preserving config creation for downstream Stage A refinement.
DB-AT-024 regression guard PASSED (mapping parity unchanged), Stage A expansion smoke test PASSED (refine_one CLI unaffected).
Next: Phase B2b(ii) wiring (nanobrag_refinement Stage B/C panel loops to factory, validate Stage B/C smokes).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/ (phase_b2b_i_decision.md, pytest_db_at_024.log, pytest_stage_a_expansion.log)
```

### Step 7: Commit and Push

```bash
git add dbex/refine_one.py plans/active/TORCH-API-ALIGN-001/

git commit -m "TORCH-API-ALIGN-001 Phase B2b(i): Factory wiring (refine_one CLI) — tests: DB-AT-024 PASSED, Stage A smoke PASSED

Wired refine_one CLI forward simulation panel loop to use create_unified_simulator factory:
- Panel loop: 73 lines → 20 lines (-53, eliminated manual model/HKL/simulator setup)
- Config creation preserved for downstream Stage A refinement (crystal_config needed by run_nanobrag_refinement)
- Eliminated beam_config branching for Simulator construction (factory accepts optional beam_config)

Factory integration centralizes:
- Model instantiation (Detector, Crystal)
- HKL attachment (crystal.hkl_data, crystal.hkl_metadata)
- sqrt_scale computation (factory returns scalar, refine_one applies post-run)

DB-AT-024 regression guard PASSED (mapping parity unchanged).
Stage A expansion smoke test PASSED (refine_one CLI unaffected).
Net: -53 lines, no behavior change, Phase B2b(ii) pending (nanobrag_refinement panel loops)."

git push
```

## How-To Map

### Factory Wiring Checklist (refine_one.py)

1. Add factory import at function top (~line 380): `from dbex.refinement.helpers import create_unified_simulator`
2. Locate panel loop lines 403-475
3. Replace lines 439-465 (model instantiation + HKL attachment + Simulator construction) with factory call (~12 lines)
4. Pass `calibration_metadata` to factory (factory stores it in metadata dict)
5. Use factory-returned `sqrt_scale_value` instead of local `sqrt_spot_scale` (line 472)
6. **CRITICAL:** Keep config creation (lines 407-436) - `crystal_config` is needed by `run_nanobrag_refinement` at line 510
7. Remove manual Detector/Crystal instantiation (lines 439-440)
8. Remove manual HKL attachment (lines 447-448)
9. Remove beam_config branching for Simulator construction (lines 451-465)

### Validation Protocol
- **Compilation:** `python -c "from dbex.refine_one import main"`
- **Regression Guard:** DB-AT-024 mapping parity (zero-iteration forward model unchanged)
- **Smoke Test:** Stage A expansion (refine_one CLI + Stage A refinement unaffected)

### Decision Paths
- **Path A:** All tests PASS → Phase B2b(i) COMPLETE, proceed to Phase B2b(ii) (nanobrag_refinement panel loops)
- **Path B:** DB-AT-024 FAIL → rollback, isolate delta, fix mapping parity bug
- **Path C:** Stage A smoke FAIL → fix config preservation or beam_config wiring
- **Path D:** Compilation FAIL → fix import path or circular dependency

## Pitfalls To Avoid

1. **DO NOT remove config creation** — crystal_config is needed by run_nanobrag_refinement at line 510, cannot be deferred to factory
2. **Import factory inside function** — Add import at function top (~line 380) to avoid circular deps
3. **calibration_metadata parameter** — Pass to factory even though factory doesn't use it for construction (stores in metadata dict for telemetry)
4. **Do not modify factory** — Factory is correct per Phase B2a validation; only wire callers this loop
5. **Do not touch nanobrag_refinement** — Phase B2b(ii) wiring (separate loop)
6. **Environment Freeze** — No package installs, dbex-only changes
7. **Protected Assets** — Do not modify factory (helpers.py:82-216), DB-AT-024 test logic, or Stage A smoke test fixtures

## If Blocked

**DB-AT-024 Regression (mapping parity drop):**
- Log error in `blocker_mapping_regression.md`
- Compare factory-returned simulator vs original code side-by-side
- Check: config creation order? beam_config wiring? sqrt_scale application timing?
- Commit factory wiring with TODO comment, return to Galph

**Stage A Smoke FAIL:**
- Log error in `blocker_stage_a_smoke.md`
- Check: config creation preserved? crystal_config accessible at line 510? telemetry structure correct?
- Revert factory wiring and commit partial progress, return to Galph

**Compilation FAIL (circular import):**
- Log error in `blocker_circular_import.md`
- Move factory import inside function if not already
- Or use lazy import pattern: `from dbex.refinement import helpers; helpers.create_unified_simulator(...)`
- Commit with import fix, return to Galph

## Findings Applied

- **SCALE-004:** Calibration metadata + post-run sqrt_scale pattern (factory computes sqrt, refine_one applies)
- **ARCH-ENGINE-002:** Lazy imports inside function (factory import moved to avoid circular deps)
- **POLICY-001:** Environment Freeze (no engine patches, dbex-only changes)
- **GEOMETRY-001/002:** DIALS beam-center swap + Euler extraction (handled upstream in create_detector_config, factory agnostic)

## Pointers

- **Implementation plan:** `plans/active/TORCH-API-ALIGN-001/implementation.md:65` (Phase B2 wiring specification)
- **Factory implementation:** `dbex/refinement/helpers.py:82-216` (create_unified_simulator function)
- **refine_one CLI:** `dbex/refine_one.py:403-475` (panel loop)
- **DB-AT-024 test:** `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
- **Stage A smoke test:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

## Next Up

After Phase B2b(i) complete (refine_one CLI factory wiring validated):
1. **Phase B2b(ii):** Wire nanobrag_refinement Stage B/C panel loops to factory (~60 lines changes, validate Stage B/C smokes)
2. **Phase B3:** Implement ExperimentModel adapter behind explicit flag (default OFF, ~200 lines, validate A3 parity test)
3. **Phase C:** Optional CUSTOM override (dbex feature flag, exploratory parity run on fixtures)
