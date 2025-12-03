# Boundary Audit — Writer / Bridge Responsibility Split

**Initiative:** ARCH-BRIDGE-RESP-001
**Date:** 2025-12-02T213000Z
**Purpose:** Capture current `write_torch_outputs` and `prepare_refinement_inputs` call graph and responsibilities to establish baseline before Phase A.2 dataclass extraction.

## Search Commands

```bash
rg -n "write_torch_outputs" dbex tests > writer_callers.txt
rg -n "prepare_refinement_inputs" dbex tests > bridge_callers.txt
```

## write_torch_outputs Call Graph

**Primary Callers:**
- `dbex/refine_one.py:604` — Main CLI entry point after Stage C completion; passes full-detector Bragg, ROI arrays, telemetry, and HKL metadata to writer.
- `tests/dbex/test_refine_one_cli.py` — Multiple test mocks/patches (lines 110, 264, 442, 534, 627) verifying HDF5 schema compliance, telemetry routing (hkl_source), and Bragg scaling.

**Definition:**
- `dbex/io/writer.py:41` — Extracted from legacy `_write_torch_outputs` per ARCH-REFINE-001 Phase C.2 (2025-12-01). Currently accepts 15+ parameters including raw ROI data/background/bragg arrays, runs internal Nelder–Mead optimization for ROI scoring, and serializes `/torch_diagnostics` + ROI datasets into HDF5.

**Current Responsibilities:**
1. ROI scoring via SciPy Nelder–Mead (computes scale/score per ROI triptych)
2. HDF5 dataset creation (`/torch_diagnostics`, `/data/roiN`, `/model/roiN`, `/bragg/roiN`, `/bg/roiN`, `/score`)
3. Telemetry schema serialization (chi2, masked_mse, convergence flags, hkl_source)

**Seam:** The writer currently mixes ROI analysis (optimization) with serialization (HDF5 I/O), violating single-responsibility principle. Phase A.2 will introduce typed `ROIAnalysisPayload` so the writer can delegate scoring to a separate helper and focus solely on serialization.

## prepare_refinement_inputs Call Graph

**Primary Callers:**
- `dbex/refine_one.py:321` — Main CLI entry; builds RefinementInputs from DataLoad after sigma/calibration setup.
- `dbex/vis/mapping.py:145` — Mapping diagnostic tool uses RefinementInputs for visualization.
- `tests/dbex/test_nanobrag_bridge.py` (TestPrepareRefinementInputs suite) — Unit tests for tensor contract, sigma precedence, mask semantics, photon conversion.
- Multiple acceptance tests: `test_mask_semantics.py`, `test_background_semantics.py`, `test_calibration_policy.py`, `test_gradients.py`, `test_mapping_consistency.py`.

**Definition:**
- `dbex/nanobrag_bridge.py:81` — Orchestrates background subtraction, mask application, sigma validation, photon conversion, and config factory calls (detector, crystal, beam). Returns typed `RefinementInputs` dataclass.

**Current Responsibilities:**
1. Background subtraction (data - bg → targets)
2. Variance/sigma validation and unit conversion (ADU ↔ photons per docs/spec-db-core.md §§36-45)
3. Mask intersection (DIALS trusted mask + optional DiffBragg hot mask) with polarity guards (GEOMETRY-001)
4. Detector/crystal/beam config hydration via factory-style helpers (square-pixel guards, beam-center/rotation validation per CONFIG-001)
5. RefinementInputs dataclass population with telemetry provenance (sigma source, adu_per_photon, mask stats)

**Seam:** The bridge currently serves as a god module mixing I/O, config factories, physics (variance), and input builders. Phase C will decompose this into:
- `dbex/refinement/inputs.py` — RefinementInputs dataclass + builder
- `dbex/refinement/config_factories.py` — Detector/crystal/beam config hydration with typed returns
- Retained orchestration glue in `dbex/nanobrag_bridge.py` (slim shim pointing to new modules)

## Dependency Analysis

**Writer Dependencies (in-scope):**
- SciPy (Nelder–Mead) — ROI scoring; will move to separate helper in Phase B.
- h5py — HDF5 serialization; stays in writer.
- numpy — array operations; will be the primary interface after Phase A.2 (no torch tensors at writer boundary).

**Bridge Dependencies (out-of-scope for this loop):**
- dxtbx — Experiment/detector metadata
- DIALS — Reflection table, trusted mask
- torch — RefinementInputs fields are torch tensors; future decomposition will keep factories numpy-compatible and let stages handle torch conversion.

**Circular Import Risks:**
- If `dbex/io/roi_analysis.py` imports writer or stages → avoid by keeping roi_analysis as pure numpy dataclasses + packaging helper (no dependencies).
- If `dbex/refinement/inputs.py` imports from stages → avoid by injecting stage-specific dependencies (e.g., simulators) rather than importing stage modules.

## Summary

**Writer Seam:** Currently runs ROI scoring (optimization) internally; Phase A.2 will introduce `ROIAnalysisPayload` to separate analysis from serialization. Phase B will implement the scoring helper and wire it to CLI/engine paths.

**Bridge Seam:** Currently a 1800+ line god module; Phase C will extract RefinementInputs builder and config factories into focused modules under `dbex/refinement/`, leaving a slim orchestration shim.

**Next Actions (This Loop — Phase A.0/A.2/A.3):**
1. Create `dbex/io/roi_analysis.py` with `ROITriptych`, `ROIAnalysisPayload`, and `build_roi_payloads_from_arrays` helper (numpy-only, no optimization logic).
2. Update `docs/architecture/dbex/io/writer.idl.md` with "ROI Analysis Payload" section describing new typed parameter.
3. Extend `docs/data_dependency_manifest.md` with helper inputs/outputs and telemetry fields.
4. Re-run mapped tests to confirm no behavior change (writer still runs internal optimization; new module is unused scaffolding for Phase B wiring).

**Artifacts:**
- `writer_callers.txt` — ripgrep output (24 lines)
- `bridge_callers.txt` — ripgrep output (66 lines)
- This document — call graph summary + seam description

**Compliance:**
- DIAGNOSTICS-001 — HDF5 schema must remain stable; new payload is additive only.
- PHYSICS-LOSS-001/002/003 — Variance + mask semantics preserved (no behavior change this loop).
- GEOMETRY-001 & CONFIG-001 — Bridge guards remain enforced (no bridge code changes this loop).
