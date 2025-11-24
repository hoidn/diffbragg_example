# Integrating `nanobrag_torch` as the Refinement Backend

## Overview
- Replace the DiffBragg `hopper`-based optimizer in `dbex` with a PyTorch refinement loop powered by `nanobrag_torch`, while leaving the trusted simtbx/DIALS data-preparation pipeline intact.
- Produce the full Bragg model image (`Bragg`) matching `DataLoad.data` so the downstream ROI scoring and visualization code remain unchanged.
- Maintain scientific equivalence by mirroring the staged refinement strategy (crystal → Fhkl → detector) and validating against the existing workflow.

Estimated timeline: 12–18 engineering days (5 phased milestones with validation).

For detector config mapping, masks, units, and ROI semantics, see docs/nanobrag_api.md, docs/spec-db-core.md, and docs/dials_api.md.

## Stage Policy and Baseline Conventions

Stage refinement targets and interpolation requirements are defined in docs/spec-db-workflow.md §Stage A/B/C (lines 34-66). For mapping parity requirements and Stage A zero-point conventions, see docs/spec-db-conformance.md (DB-AT-024) and docs/spec-db-workflow.md §Baseline Convention (lines 29-32).

## Phase 0 – Environment & Baseline (verification only, 1–2 days)
- Environment Freeze: Do not install or upgrade packages, clone external repos, or modify toolchains. If `nanobrag_torch` or its tests are unavailable, record a blocker in `docs/fix_plan.md` and proceed with evidence‑only steps.
- Verify imports and runtime flags without modification:
  - `python -c "import dbex; import torch; print(torch.__version__)"`
  - Confirm `KMP_DUPLICATE_LIB_OK=TRUE` is exported for torch-based tests.
- If nanoBragg docs are present in the workspace, you MAY run the bundled CPU/CUDA smoke tests for verification only (`nanoBragg/docs/development/pytorch_runtime_checklist.md`). Do not attempt to fetch/install missing components.
- Capture the current DiffBragg output for a representative dataset (`refine_one` HDF5 + ROI scores) as the baseline for parity checks.

## Phase 1 – Data Preparation Bridge (2–3 days)

### Objectives
Provide a bridge that converts `DataLoad` outputs and DIALS experiment metadata into tensors and configuration objects consumable by `nanobrag_torch`.

### Tasks
- Extend `DataLoad` usage with a helper (e.g., `prepare_refinement_inputs(args)`) that returns:
  - `target_tensor`: background-subtracted image (`data - background`) with invalid pixels zeroed.
  - `bg_mask_tensor`: boolean mask where the background estimate is trusted (`background >= 0`).
  - `trusted_mask_tensor`: boolean mask from the DIALS trusted mask (1 = include, 0 = exclude), panel-aligned.
  - `panel_slices`: list of per-panel `(panel_id, slice_y, slice_x)` selectors for reconstructing the final image.
- Config construction from DIALS Experiment metadata is documented in docs/config_crosswalk.md and docs/nanobrag_api.md.
- Create an adapter module (`dbex.nanobrag_bridge`) encapsulating the above logic and returning a `RefinementInputs` dataclass with tensors and configs already on the target torch `device`.

For pixel geometry constraints, mask handling, and unit conventions, see docs/spec-db-core.md.
  

Multi-panel simulation and stitching workflow is specified in docs/spec-db-workflow.md §Per-Panel Simulation (lines 13-16).

### Consistency Smoke Test (mapping sanity)
- Purpose: verify geometry/beam/crystal mapping before any refinement.
- Steps:
  - Build per‑panel DetectorConfig/BeamConfig/CrystalConfig from `Expt` and `DataLoad` as above.
  - Run a single forward simulation to produce a full‑frame `Bragg` tensor (no parameter updates).
  - For a sample of ROIs (e.g., 32): compute correlation between `Bragg[roi]` and `data[roi] - background[roi]` and verify predicted intensity is spatially localized within the ROI.
  - Produce an overlay HDF5 (or PNGs) for quick visual inspection.
- Acceptance (tunable): median ROI correlation ≥ 0.2 and at least 90% of ROIs have a local max within the central half‑box. If thresholds fail, dump panel geometry, beam center, and basis vectors for debugging.

## Phase 2 – PyTorch Model & Parameterization (3–4 days)

### Objectives
Implement a differentiable refinement model with physically constrained parameters.

### Tasks
- Define `NanoBraggRefinementModel(torch.nn.Module)` with refinable parameters and stable parameterizations.
- Parameter constraints and baseline crystal state are defined in docs/spec-db-core.md §Baseline Crystal State and Parameterization (lines 34-57).
- Implement `forward()` to:
  1. Materialize `CrystalConfig`, `BeamConfig`, and per-panel `DetectorConfig` with the current parameter values.
  2. Invoke the panel simulation loop (Phase 1) to produce the full `Bragg` tensor.
  3. Return a tuple `(bragg_tensor, aux)` where `aux` bundles current physical parameters for logging.

### Outputs
- Drop-in function `run_nanobrag_refinement(inputs, optimizer_cfg)` returning:
  - Final `Bragg` tensor on CPU (numpy array) for ROI scoring.
  - History object with loss trace and parameter snapshots.

## Phase 3 – Training Schedule & Loss (3 days)

### Objectives
Mirror the staged refinement logic from DiffBragg to maintain convergence characteristics.

Variance-weighted loss definition and optimizer requirements are specified in docs/spec-db-core.md §Variance Model (lines 82-95) and docs/spec-db-runtime.md §Optimizer Requirements (lines 51-73).

### Logging
- Emit structured logs (JSON lines) recording stage transitions, losses, and parameter deltas to simplify validation against the baseline.
- Runtime/caching: Reuse a warmed Simulator per panel while changing differentiable parameters. Rebuild the Detector/Simulator when changing tensor shapes (panel dimensions, oversample factors, ROI detectors).

References: docs/nanobrag_api.md (runtime/caching).

Refinement lifecycle, convergence gates, and telemetry schema are defined in docs/spec-db-workflow.md §Refinement Lifecycle (lines 82-120) and docs/spec-db-runtime.md.

Stage B structure-factor refinement implementation is specified in docs/spec-db-workflow.md §Stage B (lines 58-66).

## Phase 4 – CLI Integration & Output (2 days)

### Tasks
- Add a new entry point (`dbex.refine_one_torch` or feature flag) that:
  - Parses existing CLI arguments plus an optional `--backend {diffbragg, nanobrag}` switch.
  - Calls the Phase 1 bridge to obtain tensors/configs.
  - Runs `run_nanobrag_refinement`.
  - Writes the `Bragg` array and derived HDF5 datasets with the same layout as the legacy path, fulfilling the TODO:
    ```python
    Bragg_np = bragg_tensor.cpu().numpy()
    ```
  - Persists optimizer diagnostics into an auxiliary group (`/torch_diagnostics`) for debugging.
- Ensure ROI scoring (`score_trainer.roi_check`) operates on the new `Bragg` array without modification.
- Update `dbex/look.py` to optionally overlay PyTorch diagnostics if present (non-blocking enhancement).

## Phase 5 – Validation & Documentation (3–4 days)

### Synthetic Tests
- Generate a synthetic diffraction image with known parameters using `nanobrag_torch` and verify the refinement recovers them when seeded with offsets.

### Parity Tests
 - Run both backends on the baseline dataset(s) and compare:
   - Final loss / ROI scores.
   - Refined cell parameters, orientation matrices, detector adjustments.
   - Residual maps (`target - Bragg`) saved as images for visual inspection.
 - Document acceptable tolerances (e.g., Δa < 0.1 Å, ROI score within 2 %).
- Include a parity check against the designated parity dataset once it exists; until then, document the skip and dataset gap before moving to real data.
 
References: docs/nanobrag_api.md (golden parity assumptions).

### Documentation Deliverables
- `reports/nanobrag_validation.md` summarizing results.
- Update project README with backend selection instructions and limitations.

## Filesystem and Tempfile Policy
- Torch backend:
  - Avoid on‑disk artifacts during refinement; perform all structure‑factor and parameter updates in memory.
  - When exporting HKL for debugging or parity tests, write under a `TemporaryDirectory()` and clean up on exit.
- DiffBragg fallback (legacy):
  - Replace hardcoded filenames in the legacy DiffBragg path (`_geom_ref.*`, `_geom_groups.txt`, `_geom.out`, `_temp.mtz`) with paths under a `TemporaryDirectory()` context to avoid polluting the working tree.
  - Keep an opt‑in flag (e.g., `--debug-save-artifacts`) to persist outputs for debugging when needed; default is ephemeral.

## Deliverables Checklist
- [ ] `dbex/nanobrag_bridge.py` (or similar) with conversion utilities.
 - [ ] `dbex/torch_model.py` implementing `NanoBraggRefinementModel`.
 - [ ] Updated CLI/entry point with backend toggle.
 - [ ] Automated tests covering data preparation and a short refinement smoke test.
 - [ ] Validation report with parity metrics.
 - [ ] HDF5 outputs containing `Bragg` arrays for both backends.
 - [ ] In‑memory cctbx→dense F grid helper (or HKL export) and optional padding utility for tricubic halos.
 - [ ] Optional ROI‑cropped Detector builder utility for performance‑sensitive runs.
 
References: docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md, docs/nanobrag_api.md.

## Open Questions & Follow-ups
1. **Rectangular pixel support:** Current Detector supports square pixels only. If fast/slow pitch differs, plan either separate Detector instances per unique pixel size or defer until `pixel_size_s_mm/pixel_size_f_mm` is available.
2. **Structure‑factor refinement scope:** Decide between per‑reflection, per‑shell, or fixed Fhkl strategy after initial performance/gradient tests with tricubic enabled.
3. **Beam polarization & spectral distribution:** Start with single‑source; evaluate multi‑source beam and polarization metadata prevalence in our datasets before enabling.
4. **Gradient stability for large crystals:** For large `N_cells`, consider gradient clipping or smoothing if needed; monitor during synthetic tests.
5. **Memory/performance:** If full‑frame per‑panel simulation exceeds memory budgets, adopt ROI‑cropped Detectors and panel batching. Consider contributing ROI‑aware execution upstream when time permits.
