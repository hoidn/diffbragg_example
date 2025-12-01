# ARCH-REFINE-001 Phase D Architecture Documentation Update Ledger

**Date**: 2025-12-01
**Scope**: Phase D.1–D.2 Documentation Consolidation
**Status**: Complete

## Executive Summary

Phase D completed the documentation hand-off for the ARCH-REFINE-001 refactoring initiative, publishing IDL contracts for the torch writer and physics helpers (Phase D.1) and retiring stale engine-delegation flag references across tooling and testing docs (Phase D.2). This ledger consolidates the changes so downstream initiatives can cite a single artifact instead of diff-spelunking across multiple commits.

---

## Phase D.1: IDL Contract Publication (2025-12-01T142116Z)

### New IDL Contracts Created

#### 1. `docs/architecture/dbex/io/writer.idl.md` (170 lines)
**Purpose**: Full API contract for `write_torch_outputs` — the canonical HDF5 telemetry writer for the torch backend.

**Key Sections**:
- **API**: `write_torch_outputs(args, data_load, bragg, inputs, masked_mse, hkl_telemetry, refine_telemetry, sigma_readout_provenance, sigma_readout_reference_value)`
- **Outputs**: Per-ROI HDF5 datasets (data/model/bragg/bg/variance, score, bragg_scale) + `/torch_diagnostics` group attributes (masked_mse, loss_mask_coverage, n_rois, target_shape, backend, hkl_source/hkl_count/hkl_mean/hkl_path, sigma_provenance/sigma_reference, calibration_source, per-stage telemetry)
- **Variance Computation**: V = max(I_model.detach() + σ_rdout², σ_floor²) per spec-db-core.md §86-90
- **Dependencies**: RefinementInputs, DataLoad, RefinementTelemetry (optional), HKL/sigma provenance metadata
- **Usage Patterns**: CLI multi-stage telemetry, forward-only probe, test fixture
- **Validation Rules**: ROI count consistency, sigma positivity, telemetry schema preservation
- **Maintenance Notes**: DIAGNOSTICS-001 schema stability, PHYSICS-LOSS-001/003 dual-loss metrics, TORCH-CLI-004 provenance threading, REFINE-010 Stage A auto-panel metadata

**Spec/Finding Citations**:
- `docs/spec-db-workflow.md` §§70-75 (HDF5 schema)
- `docs/spec-db-core.md` §§57-68 (variance model), §§86-90 (loss computation)
- DIAGNOSTICS-001, PHYSICS-LOSS-001, PHYSICS-LOSS-003, TORCH-CLI-004, REFINE-010

#### 2. `docs/architecture/dbex/physics/forward.idl.md` (139 lines)
**Purpose**: API contract for `simulate_forward_torch` — TEST-ONLY forward simulation helper for gradcheck/parity testing.

**Key Sections**:
- **TEST-ONLY Scope**: Warning that this helper is not for production refinement paths (use unified factory or direct Simulator)
- **API**: `simulate_forward_torch(inputs, detector, beam, crystal, experiment, hkl_indices, hkl_amplitudes, spot_scale_override, device, dtype, crystal_overrides)`
- **Outputs**: `bragg_torch` tensor with gradient preservation
- **Dependencies**: torch, nanobrag_torch, bridge imports (create_*_config, prepare_refinement_inputs)
- **Usage Patterns**: DB-AT-010 gradcheck with unit cell params, forward-only probe
- **Validation/Testing**: DB-AT-010 selectors with env vars (AUTHORITATIVE_CMDS_DOC, DBAT010_ARTIFACT_DIR, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE)
- **Maintenance Notes**: Gradient preservation for gradcheck, crystal_overrides parameter keys, test-only scope enforcement

**Spec/Finding Citations**:
- `docs/spec-db-workflow.md` §§45-52 (forward simulation)
- `docs/spec-db-runtime.md` §§10-17 (device/dtype neutrality)
- RUNTIME-001, SCALE-001/002, GRADIENT-001, PHYSICS-LOSS-001, ARCH-FACTORY-001

#### 3. `docs/architecture/dbex/physics/loss.idl.md` (126 lines)
**Purpose**: API contract for variance-weighted loss computation — `_compute_variance_weighted_loss` (internal) and `compute_masked_mse_loss` (TEST-ONLY public).

**Key Sections**:
- **Variance Model**: V = max(I_model.detach() + σ_rdout², σ_floor²)
- **IRLS Semantics**: Detached denominator per PHYSICS-LOSS-001
- **API**:
  - `_compute_variance_weighted_loss(predicted, target, loss_mask, sigma_readout, sigma_floor_sq)` → chi²
  - `compute_masked_mse_loss(predicted, target, loss_mask)` → masked MSE
- **Dependencies**: torch (standard library only, no external deps)
- **Usage Patterns**: DB-AT-010 gradcheck, Stage A LBFGS closure, forward-only MSE
- **Validation/Testing**: Variance positivity, loss_mask coverage, σ_floor/σ_rdout dimension matching
- **Maintenance Notes**: PHYSICS-LOSS-001 (IRLS detachment), PHYSICS-LOSS-003 (dual-loss metrics), SCALE-002 (sigma_floor semantics)

**Spec/Finding Citations**:
- `docs/spec-db-core.md` §§57-68 (loss function), §§86-90 (variance weighting)
- `docs/spec-db-workflow.md` §§38-44 (refinement loss)
- PHYSICS-LOSS-001, PHYSICS-LOSS-003, SCALE-002

### Module Docstring Updates

Phase D.1 updated module/function docstrings to reference the new IDLs:

- **`dbex/io/writer.py`** (lines 1-37): Module docstring references `docs/architecture/dbex/io/writer.idl.md` §API; added findings section citing DIAGNOSTICS-001, PHYSICS-LOSS-001, REFINE-010; updated change log noting D.1 IDL publication.

- **`dbex/physics/forward.py`** (lines 1-31, 51-101): Module docstring references `docs/architecture/dbex/physics/forward.idl.md`; added TEST-ONLY warning, findings section citing RUNTIME-001, SCALE-001/002, GRADIENT-001, PHYSICS-LOSS-001. Function docstring references IDL §API section.

- **`dbex/physics/loss.py`** (lines 1-26, 76-115): Module docstring references `docs/architecture/dbex/physics/loss.idl.md`; added findings section citing PHYSICS-LOSS-001, PHYSICS-LOSS-003, SCALE-002. Function docstring references IDL §API section.

### Module Map Updates

**`docs/architecture/module_map.md`** (lines 15-18, 29-30):
- Added row for `dbex/io/writer.py` with IDL link (line 15): "HDF5 telemetry writer, `/torch_diagnostics` schema"
- Updated `dbex/physics/forward.py` row with TEST-ONLY note and IDL link (line 16): "Forward simulation helpers (TEST-ONLY, DB-AT-010)"
- Updated `dbex/physics/loss.py` row to include `compute_masked_mse_loss` and IDL link (line 17): "Variance-weighted chi² and masked MSE"
- Updated Notes section (line 29): "Phase D.1 complete: IDL contracts published for `dbex/io/writer.py`, `dbex/physics/forward.py`, `dbex/physics/loss.py`"

### Validation Evidence

Phase D.1 validation ran telemetry and gradcheck selectors to prove docstring-only edits left runtime behavior untouched:

- **CLI telemetry test**: `test_torch_diagnostics_metadata` — 2/2 PASSED (parametrized with cli_override + external_lookup) in 0.91s
- **DB-AT-010 gradcheck**: 5/5 PASSED (crystal_cell_a, crystal_cell_gamma, detector_distance, beam_wavelength, full gradcheck) in 95.25s with --smoke-detector-size=full

**Artifacts**: `plans/active/ARCH-REFINE-001/reports/2025-12-01T142116Z/` (collect/pytest logs, docs_diff.md, summary.md)

---

## Phase D.2: Engine-Only Tooling & Documentation Sync (2025-12-01T144500Z)

Phase D.2 removed the deprecated `use_engine_delegation` flag from all Stage A tooling surfaces and refreshed architecture/testing docs to reflect that `RefinementEngine` is the sole execution path (no inline fallback branch).

### Code Changes: Tooling

#### 1. `dbex/tools/stage_a_adam.py::run_engine_zero_point_probe`
- **Change**: Removed `use_engine_delegation=True` kwarg when calling `run_nanobrag_refinement`
- **New Behavior**: Routes exclusively through `RefinementEngine`; raises targeted `RuntimeError` if Stage A telemetry is missing from engine return dict
- **Docstring Update**: Clarified that RefinementEngine is always active (no flag needed)

#### 2. TOOLING-VIS-001 Drivers
Updated all plan-local visualization scripts under `plans/active/TOOLING-VIS-001/bin/` that shell `run_nanobrag_refinement`:
- `compare_stage_a_mapping_parity.py`
- `generate_stage_a_refgeom_roi_triptychs.py`
- `generate_stage_a_refgeom_roi_triptychs_adam.py`
- `run_stage_a_engine_zero_point_probe.py`

**Changes**: Removed `use_engine_delegation=True` from all `run_nanobrag_refinement` calls; preserved calibration inputs verbatim.

### Documentation Updates

#### 1. `docs/architecture/live_backend.md` (lines 9, 23, 31, 45)
- **Line 9**: "Refinement engine: `RefinementEngine` + `StageA/B/C` is the sole execution path (ARCH-REFINE-001 Phase A complete)."
- **Line 23**: "Outputs: the torch backend uses a dedicated writer (`dbex/io/writer.py`, ARCH-REFINE-001 Phase C.2/C.4 complete) ... Physics helpers centralized in `dbex/physics/forward.py` and `dbex/physics/loss.py` (PHYSICS-LOSS-001)."
- **Line 31**: "Refinement path: `RefinementEngine` + contexts will become the only code path once ARCH-REFINE-001 Phase A/B completes and the inline helpers are removed." *(Note: Phase A/B are now complete; this line describes completed state)*
- **Line 45**: "HDF5 writer: `dbex.io.writer.write_torch_outputs(...)` writes per-ROI datasets and `/torch_diagnostics` attrs ... Canonical location is `dbex/io/writer.py` (DIAGNOSTICS-001, REFINE-010)."

**Key Message**: RefinementEngine is the only execution path; inline branch removed in Phase A.4.

#### 2. `docs/architecture/data_telemetry_flow.md` (lines 10, 14, 18, 24)
- **Line 10**: "`JobContext` / `RefinementContext` (ARCH-REFINE-001 Phase B complete) bundle DataLoad fixtures, calibration metadata, HKL grids"
- **Line 14**: "Torch writer (`dbex/io/writer.py`, ARCH-REFINE-001 Phase C.2/C.4 complete) emits HDF5 + optional triptych PNG export"
- **Line 18**: "Refinement path: `RefinementEngine` is the sole execution path (ARCH-REFINE-001 Phase A/B/C/D.1 complete)."
- **Line 24**: "This contract ... is now implemented in `dbex/io/writer.py` (ARCH-REFINE-001 Phase C.2/C.4 complete); physics helpers centralized in `dbex/physics/{forward,loss}.py` (PHYSICS-LOSS-001)."

**Key Message**: Engine-only flow operational; no inline fallback; writer/physics helpers extracted and documented.

#### 3. `docs/TESTING_GUIDE.md` (lines 167, 161)
- **Line 167**: "RefinementEngine Telemetry Validation" selector description updated to clarify: "RefinementEngine is the sole execution path (ARCH-REFINE-001 Phase D.2 complete). Collection: 1 test. Runtime: ~12.5s."
- **Line 161**: Stage A/B/C refinement smokes description confirms engine delegation is default (no flag required).

**Key Message**: Selectors validate default engine telemetry; no `--use-engine-delegation` flag needed.

#### 4. `docs/development/TEST_SUITE_INDEX.md` (line 22)
- **Line 22**: "ARCH-REFINE-FLOW-001: Phase E RefinementEngine Telemetry" entry updated: "RefinementEngine is the sole execution path (ARCH-REFINE-001 Phase D.2 complete). Verifies backward compatibility (telemetry dict key 'A'), Phase A4 field preservation, core telemetry integrity."

**Key Message**: Test suite index reflects engine-only execution; backward compatibility preserved.

### Validation Evidence

Phase D.2 validation re-ran DB-AT-027 zero-point probe and Stage A telemetry smoke to prove tooling/tests work without the removed flag:

- **DB-AT-027 zero-point parity**: `test_db_at_027_zero_point_parity` — PASSED in 20.45s (warnings only)
- **Stage A engine telemetry**: `test_stage_a_engine_delegation_telemetry` — PASSED in 7.30s (warnings only)

**Artifacts**: `plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/` (collect/pytest logs, docs_diff.md, summary.md)

---

## Finding Citations

The Phase D documentation updates reference the following findings from `docs/findings.md`:

- **DIAGNOSTICS-001** (writer.idl.md): `/torch_diagnostics` schema stability and ownership must remain explicit; writer is canonical location for HDF5 telemetry emission.
- **PHYSICS-LOSS-001** (writer.idl.md, forward.idl.md, loss.idl.md): Variance-weighted chi² and masked MSE dual-loss metrics; IRLS detachment semantics; sigma_floor/sigma_rdout handling.
- **PHYSICS-LOSS-003** (writer.idl.md, loss.idl.md): Dual-loss metrics (chi² + MSE) required for full validation coverage.
- **ARCH-ENGINE-003** (TESTING_GUIDE.md line 167): RefinementEngine telemetry enrichment placement pattern; engine_protocol/stage_modes fields must appear in production paths.
- **REFINE-010** (writer.idl.md, module_map.md): Stage A auto-panel threshold (ROI count ≤ 32 triggers panel-mode validations) ensures Stage C gates pass on small detectors.

## Spec Alignment

The IDL contracts and documentation updates align with the following spec sections:

- **`docs/spec-db-workflow.md`**:
  - §§30-41: Refinement engine sequencing (RefinementEngine protocol)
  - §§45-52: Forward simulation (simulate_forward_torch contract)
  - §§38-44: Refinement loss (variance-weighted chi²)
  - §§70-75: HDF5 schema (write_torch_outputs telemetry)

- **`docs/spec-db-core.md`**:
  - §§57-68: Loss function and variance model
  - §§86-90: Variance weighting in chi² computation

- **`docs/spec-db-runtime.md`**:
  - §§10-17: Device/dtype neutrality for PyTorch code

- **`docs/spec-db-conformance.md`**:
  - DB-AT-010: Gradcheck validation for forward simulation and loss helpers

---

## Phase D.5: Documentation Capture & Selector Refresh (This Loop)

Phase D.5 (this loop) synthesizes D.1–D.2 into this ledger and refreshes Stage A selector evidence:

1. **Architecture doc update ledger**: This document (`plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/architecture_doc_update.md`)
2. **Docs diff snapshot**: `docs_diff.md` captures any follow-up nits fixed while compiling the summary
3. **Fix plan reference**: `docs/fix_plan.md` Phase D Attempts History updated to reference this report
4. **Selector evidence refresh**: Rerun DB-AT-027 zero-point parity and Stage A engine telemetry smoke with current docs to keep logs synchronized

---

## Summary

Phase D completed the documentation consolidation for ARCH-REFINE-001 Phases A-C implementation work:

- **3 IDL contracts** published for torch writer and physics helpers with full API/validation/maintenance documentation
- **5 architecture/testing docs** updated to reflect engine-only execution and remove stale inline-path references
- **8 module docstrings** updated to reference IDLs
- **4 tooling scripts** migrated to engine-only API
- **2 validation selectors** (CLI telemetry + DB-AT-010 gradcheck, Stage A zero-point + telemetry) confirmed runtime parity

Downstream initiatives can now cite this ledger instead of reviewing individual Phase D commits. All selector evidence remains green (no regressions introduced by doc-only changes).

**Next Actions**: Phase D complete. Ready to advance to remaining ARCH-REFINE-001 phases (RefinementContext/JobContext enforcement in CLI, or pivot to supervisor-prioritized focus).

---

**Report Date**: 2025-12-01
**Initiative**: ARCH-REFINE-001
**Phase**: D.5 (Documentation Ledger)
**Loop Timestamp**: 2025-12-01T150955Z
