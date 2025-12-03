# Data Dependency Manifest

This manifest records the external data inputs (datasets, calibration payloads, MTZ/HKL sources, masks, sigma maps) consumed by the key DBEX modules/CLIs. Each entry lists the required arguments, optional overrides (env vars/CLI flags), default provenance, and the expected telemetry fields so reviewers can verify asset usage without spelunking code.

> **Review rule:** When reusing one of these helpers in a new context (plan, probe, or selector), confirm the data inputs match the manifest. If a helper needs different defaults or fallback behavior, update both the helper docstring and this manifest in the same change.

## Legend

- **Req. Inputs:** Mandatory files/structs the helper expects.
- **Optional Overrides:** Env vars or CLI flags that redirect data inputs.
- **Default Provenance:** Where the helper currently sources the data if no override is provided.
- **Telemetry/Diagnostics:** Fields that must be updated to reflect the actual inputs.

## Mapping/Stage-A Helpers

### `dbex.vis.mapping.build_mapping_stage_a_context`

- **Req. Inputs:**
  - `dataload.args.mtzFile` (default `scaled.mtz` in repo root).
  - `dataload.args.exptName`, `dataload.args.reflName`, `dataload.trusted_mask`, `background_image`.
- **Optional Overrides:**
  - `dataload.args.hkl_source_path` (populated via `DBEX_SMOKE_HKL_PATH`).
  - `dataload.args.calibration_config_path` (populated via `DBEX_SMOKE_CALIB_PATH` once TODO landed).
  - `dataload.sigma_readout_map` (map tier).
- **Default Provenance (current code):**
  - HKL: prefers `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz` when present (even for other datasets) — **needs fix**.
  - Calibration: unconditionally loads `tests/fixtures/golden_data/simple_cubic/config_torch.json` — **needs fix**.
  - Sigma: uses `dataload.sigma_readout_map` or uniform fallback.
- **Telemetry/Diagnostics:**
  - `diagnostics["hkl_source"]` / `["hkl_path"]` MUST reflect the actual HKL file used.
  - Add `diagnostics["calibration_path"]` when calibration metadata is loaded.
  - `spot_scale_override`, `sigma_floor_value`, `sigma_readout_provenance`.

### `tests/dbex/test_torch_refine_smoke.py::refgeom_dataload`

- **Req. Inputs:** `sp.proc/refGeom*.expt`, `.refl`, mask path (`747_mask.pkl` or small variant).
- **Optional Overrides:**
  - `DBEX_SMOKE_DETECTOR_SIZE={small,full}` selects dataset bundle.
  - `DBEX_SMOKE_HKL_PATH` overrides HKL file (explicit override takes precedence).
  - `DBEX_SMOKE_CALIB_PATH` overrides calibration config path.
  - `DBEX_SMOKE_SIGMA_MAP_PATH` overrides sigma-map pickle path when `DBEX_SMOKE_SIGMA_SOURCE=metadata`.
- **Default Provenance (Detector-Size Aware, TOOLING-VIS-001 Phase D.D):**
  - HKL (with override precedence):
    - Override: `DBEX_SMOKE_HKL_PATH` if set (takes precedence).
    - Small detector: `sp.proc/calibration/smoke_refined_structure_factors_small.mtz` when calibration exists, else `scaled.mtz`.
    - Full detector: `sp.proc/calibration/smoke_refined_structure_factors.mtz` when calibration exists, else `scaled.mtz`.
  - Calibration (with override precedence):
    - Override: `DBEX_SMOKE_CALIB_PATH` if set (takes precedence).
    - Small detector: `sp.proc/calibration/config_torch_smoke_small.json` when present, else None.
    - Full detector: `sp.proc/calibration/config_torch_smoke.json` when present, else None.
  - Sigma-map (when metadata source):
    - Small detector (`DBEX_SMOKE_DETECTOR_SIZE=small`): `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl` (cropped to [fast: 751-1775, slow: 719-1743] matching refGeom_small window).
    - Full detector: `sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl`.
- **Telemetry/Diagnostics:** Stage A smoke metrics emit `hkl_source`, `hkl_path`, `spot_scale_override`, `sigma_source`, and `geometry_metadata` (includes `geometry_path` and `rotation_delta_deg`).

### `plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py`

- **Req. Inputs:** same as `build_mapping_stage_a_context`.
- **Optional Overrides:** CLI `--mtz-path`, `DBEX_SMOKE_*` env vars.
- **Default Provenance:** inherits helper behavior.
- **Telemetry:** writes `mapping_forward_cpu_gpu.json` containing HKL count, `hkl_source`, `spot_scale_override`, `sigma_source`.

### `tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result`

- **Req. Inputs:** outputs from `build_mapping_stage_a_context` plus perturbed geometry fixtures.
- **Optional Overrides:** `DBAT028_ARTIFACT_DIR`, `DBEX_SMOKE_SIGMA_SOURCE`, `DBEX_SMOKE_HKL_PATH`.
- **Telemetry:** persists `mapping_context` diagnostics, `hkl_*`, `sigma_source`, `spot_scale_override`.

## Sigma/Calibration Sources

### Sigma Precedence (per `spec-db-core.md`)

- **Tier 1:** `--sigma-map` (CLI/config) → stored on DataLoad.
- **Tier 2:** `--sigma-rdout` scalar overrides.
- **Tier 3:** dxtbx `external_lookup` tiles (metadata).
- **Failure:** missing sigma at all tiers is a hard error.
- **Telemetry:** `RefinementInputs.sigma_readout_provenance`, `sigma_readout_reference_value`.

### Calibration Config (`config_torch.json`)

- Fields: `spot_scale_override`, `sigma_floor`, `beam_flux`, `beam_exposure`, `beamsize_mm`, `N_cells`.
- **Current consumers:** `build_mapping_stage_a_context`, Stage A warm cache helpers.
- **Required telemetry:** `/torch_diagnostics` entries for each field plus provenance (config vs CLI vs env).
- **Action:** ensure smoke fixtures pass their own calibration path instead of falling back to the golden config.

### Refined Structure Factors (`smoke_refined_structure_factors*.mtz`)

#### Full-Detector Bundle
- **Asset:** `sp.proc/calibration/smoke_refined_structure_factors.mtz`
- **Generation Command:** `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors.mtz --manifest <artifacts-path>/smoke_calibration_manifest.json`
- **Provenance:** DiffBragg-refined structure factors produced during smoke calibration capture; replaces raw `scaled.mtz` amplitudes with variance-weighted refined values.
- **Purpose:** Ensures Stage A mapping and DB-AT-028/029 parity tests consume the same refined structure factors as the calibration metadata, avoiding ROI CC collapse (per SCALE-004 finding).
- **Validation:** Manifest JSON includes SHA256, file size, and generation timestamp; `refgeom_dataload` fixture emits `hkl_source="refined"` when this asset is loaded.
- **Default Behavior:** When `sp.proc/calibration/config_torch_smoke.json` exists, `refgeom_dataload` and mapping helpers default to this refined MTZ unless `DBEX_SMOKE_HKL_PATH` explicitly overrides it.

#### Small-Detector Bundle (TOOLING-VIS-001 Phase D.D)
- **Asset:** `sp.proc/calibration/smoke_refined_structure_factors_small.mtz`
- **Generation Command:** `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/refGeom_small/refGeom_small.expt --refl sp.proc/refGeom_small/refGeom_small.refl --mask sp.proc/refGeom_small/refGeom_small_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke_small.json --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors_small.mtz --manifest <artifacts-path>/smoke_calibration_small_manifest.json`
- **Provenance:** DiffBragg-refined structure factors produced from refGeom_small (1024×1024 cropped detector) during smoke calibration capture.
- **Purpose:** Provides detector-size-specific refined MTZ paired with `config_torch_smoke_small.json` so small-detector smoke fixtures (DB-AT-028/029) consume calibration metadata aligned with the dataset geometry.
- **Validation:** Manifest JSON includes SHA256 (`3bf935d74fb121f3...`), file size (955K), generation timestamp, and `spot_scale_override=4.786111e+17` (vs 3.105e+17 for full detector).
- **Default Behavior:** When `DBEX_SMOKE_DETECTOR_SIZE=small` and `sp.proc/calibration/config_torch_smoke_small.json` exists, `refgeom_dataload` and mapping helpers default to this refined MTZ unless `DBEX_SMOKE_HKL_PATH` explicitly overrides it.

### Cropped Sigma-Map Asset (refGeom_small)

- **Asset:** `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl`
- **Generation Command:** `plans/active/TOOLING-VIS-001/bin/crop_sigma_map_to_window.py --sigma-map sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl --fast-start 751 --slow-start 719 --width 1024 --height 1024 --output sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl --report <report-path>`
- **Provenance:** Cropped from full-detector metadata sigma-map (`sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl`) to match refGeom_small detector window [fast: 751-1775, slow: 719-1743].
- **Purpose:** Enables metadata sigma-map loading for small-detector smoke fixtures without shape mismatch errors.
- **Validation:** Crop report JSON includes SHA256, file size, panel count, and crop window parameters for reproducibility checks.

## ROI Analysis & Writer Helpers (ARCH-BRIDGE-RESP-001)

### `dbex.io.roi_analysis.build_roi_payloads_from_arrays`

- **Preparation Responsibilities:** Input prep (`dbex.refinement.inputs.RefinementInputs` dataclass / `prepare_refinement_inputs`) constructs background-subtracted targets and loss masks; config factories (now under `dbex/refinement/config_factories.py`) hydrate detector/beam/crystal configs. The bridge module (`dbex/nanobrag_bridge.py`) retains orchestration and HKL grid helpers.
- **Req. Inputs:**
  - `target`: Full-detector target intensities (n_panels, slow, fast) in ADU or photons from DataLoad.data.
  - `background`: Full-detector background image (n_panels, slow, fast) from DataLoad.background_image.
  - `bragg`: Full-detector simulated Bragg intensities (n_panels, slow, fast) from RefinementEngine final forward model or Stage C output.
  - `pids`: Panel IDs per ROI (length n_rois) from DataLoad.pids.
  - `bbox`: Bounding boxes per ROI (length n_rois), each (x0, x1, y0, y1) with x1/y1 exclusive, from DataLoad.bbox.
- **Optional Inputs:**
  - `scores`: Pre-computed per-ROI scores (length n_rois) from upstream ROI scoring helper (Phase B, currently None).
  - `scales`: Pre-computed optimal Bragg scales (length n_rois) from upstream ROI scoring helper (Phase B, currently None; defaults to 1.0).
- **Outputs:**
  - List of `ROIAnalysisPayload` instances (length n_rois), each containing:
    - `triptych`: `ROITriptych` with cropped data/background/bragg arrays and metadata (panel_id, bbox).
    - `score`: Optional float (0-1, higher=better) from roiCheck scorer.
    - `optimal_scale`: Float (>= 0) Bragg intensity scale factor from Nelder-Mead optimization.
    - `variance`: Optional array V = max(I_model + sigma_readout^2, sigma_floor^2) per spec-db-core.md §§86-90 (Phase B wiring).
    - `model`: Optional optimized model image (background + optimal_scale * bragg) (Phase B wiring).
- **Telemetry/Diagnostics:**
  - Helper does NOT emit telemetry directly; consumers (writer, future scoring helper) will populate `/torch_diagnostics` fields:
    - `roi_scoring_method`: "inline" (Phase A) or "nelder_mead" (Phase B when scoring helper is wired).
    - `roi_checker`: "score_trainer.roi_check.roiCheck" (legacy parity).
    - `n_rois`: Number of payloads (from len(payloads)).
- **Default Provenance:**
  - Arrays: Sourced from DataLoad (target/background) and RefinementEngine/Stage C (bragg).
  - Scores/scales: None (Phase A scaffolding); Phase B will populate via dedicated ROI scoring helper calling Nelder-Mead.
- **Purpose:**
  - Packages existing ROI arrays into typed payloads without mutating or optimizing.
  - Decouples ROI scoring (Nelder-Mead optimization) from HDF5 serialization in `dbex.io.writer` (ARCH-BRIDGE-RESP-001 Phase B future wiring).
  - Provides a numpy-only interface (no torch tensors) for h5py serialization boundary.
- **Notes:**
  - Helper performs only array slicing and dataclass construction; no Nelder-Mead or variance computation (deferred to Phase B).
  - Background arrays SHALL NOT contain NaN; caller must validate upstream (enforced by dbex/nanobrag_bridge.py per PHYSICS-LOSS-001).
  - Array ordering: [panel, slow, fast] per docs/spec-db-core.md §21.

### `dbex.io.roi_scoring.score_roi_payloads` (ARCH-BRIDGE-RESP-001 Phase B.1)

- **Preparation Context:** Refinement prep (`dbex.refinement.inputs.prepare_refinement_inputs`) and config builders (`dbex.refinement.config_factories.{create_detector_config, create_beam_config, create_crystal_config}`) now live under `dbex/refinement/`. The bridge module orchestrates HKL grids and calibration metadata loading.
- **Req. Inputs:**
  - `target`: Full-detector target intensities (n_panels, slow, fast) in ADU or photons from DataLoad.data.
  - `background`: Full-detector background image (n_panels, slow, fast) from DataLoad.background_image.
  - `bragg`: Full-detector simulated Bragg intensities (n_panels, slow, fast) from RefinementEngine final forward model or Stage C output.
  - `pids`: Panel IDs per ROI (length n_rois) from DataLoad.pids.
  - `bbox`: Bounding boxes per ROI (length n_rois), each (x0, x1, y0, y1) with x1/y1 exclusive, from DataLoad.bbox.
  - `sigma_readout`: Readout noise sigma in target units (ADU or photons). Must be >= 0. Sourced from CLI args or calibration.
  - `sigma_floor`: Variance floor in target units (ADU or photons). Must be > 0. Sourced from CLI args (default 1.0).
- **Optional Inputs:**
  - `roi_checker`: roiCheck instance for scoring. If None, imports score_trainer.roi_check.roiCheck(). Injection enables testing without SciPy.
  - `log_fn`: Callable(roi_index: int, score_pct: float) for per-ROI logging. If None, prints legacy format `"roi=%d : score= %.1f"`.
- **Outputs:**
  - List of `ROIAnalysisPayload` instances (length n_rois) with populated fields:
    - `triptych`: `ROITriptych` with cropped arrays (data/background/bragg) and metadata.
    - `score`: Float (0-1, higher=better) from CHECKER.score(data, model).
    - `optimal_scale`: Float (>= 0) from Nelder-Mead optimization (fallback to 1.0 on failure).
    - `model`: np.ndarray = background + optimal_scale * bragg (shape: ny, nx).
    - `variance`: np.ndarray = max(model + sigma_readout^2, sigma_floor^2) per spec-db-core.md §§86-90 (shape: ny, nx).
- **Artifacts/Telemetry:**
  - Per-ROI logging via print() or custom log_fn: `"roi=%d : score= %.1f" % (i, score_pct)`.
  - No file artifacts emitted directly; caller (e.g., CLI, tests) may log outputs to `archive/plans/ARCH-BRIDGE-RESP-001/reports/.../` as needed.
  - Telemetry fields for downstream writer/diagnostics (populated by caller, not this helper):
    - `roi_scoring_method`: "nelder_mead" (Phase B when this helper is used).
    - `roi_checker`: "score_trainer.roi_check.roiCheck" (legacy parity).
    - `n_rois`: len(payloads).
- **Default Provenance:**
  - Arrays: Sourced from DataLoad (target/background) and RefinementEngine/Stage C (bragg).
  - Sigma parameters: `sigma_readout` from CLI `--sigma-rdout` or calibration map; `sigma_floor` from CLI `--sigma-floor` (default 1.0).
  - Scorer: score_trainer.roi_check.roiCheck() unless injected via `roi_checker` parameter.
- **Transitive Dependencies:**
  - `scipy.optimize.minimize`: Nelder-Mead optimizer (imported locally per Environment Freeze).
  - `score_trainer.roi_check`: roiCheck scorer (imported locally unless injected).
  - `dbex.io.roi_analysis.build_roi_payloads_from_arrays`: Upstream helper for slicing ROIs.
- **Purpose:**
  - Decouples ROI scoring (Nelder-Mead optimization + variance computation) from HDF5 serialization in `dbex.io.writer`.
  - Runs scipy.optimize.minimize with roiCheck objective to find optimal Bragg scale per ROI.
  - Populates typed `ROIAnalysisPayload` instances suitable for direct consumption by `write_torch_outputs` (future Phase B.2 wiring).
- **Notes:**
  - Imports scipy/score_trainer locally (not at module import time) per Environment Freeze constraint.
  - Variance must be strictly positive and finite per spec-db-core.md §38.
  - Background arrays SHALL NOT contain NaN (enforced by `build_roi_payloads_from_arrays`).
  - Score coercion via float() guards against mocked/non-scalar returns (TORCH-CLI-004).
  - Algorithm: Minimizes `1 - CHECKER.score(data, bragg_scale^2 * bragg + background)` with initial guess x0=[1]; optimal_scale = result.x[0]^2.
- **CLI Usage (ARCH-BRIDGE-RESP-001 Phase B.2):**
  - Invoked by `dbex.refine_one.run_nanobrag_backend()` after refinement completes, before calling `write_torch_outputs`.
  - Receives sigma values in target units (photons when `--adu-per-photon` is set, ADU otherwise) derived from `inputs.sigma_readout` array (mean) or `sigma_reference_target_units` fallback.
  - Converts `DataLoad.pids` and `DataLoad.bbox` from numpy arrays to Python ints/tuples before passing to helper.
  - Produces `List[ROIAnalysisPayload]` that is threaded to `write_torch_outputs` via required `roi_payloads` kwarg (Phase B.3 complete).

### `dbex.io.writer.write_torch_outputs`

- **Preparation Context:** RefinementInputs dataclass and `prepare_refinement_inputs` now sourced from `dbex.refinement.inputs`; config factories reside in `dbex/refinement/config_factories.py`. Bridge module retains orchestration/HKL helpers.
- **Req. Inputs:**
  - `args`: CLI parser namespace with `outFile` (HDF5 path), `sigma_floor` (float, default 1.0), `adu_per_photon` (Optional[float]).
  - `data_load`: DataLoad object with `data`, `background_image`, `detector`, `pids`, `bbox`.
  - `bragg`: Full-detector simulated Bragg intensities (n_panels, slow, fast) from RefinementEngine or Stage C.
  - `inputs`: RefinementInputs dataclass from `dbex.refinement.inputs` with `target`, `loss_mask`, `panel_slices`, `trusted_mask`.
  - `masked_mse`: Masked mean squared error (float) between target and Bragg.
  - `hkl_telemetry`: Dict with `hkl_source` ("refined"/"raw"), `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path`.
- **Optional Inputs:**
  - `refine_telemetry`: Dict[str, RefinementTelemetry] (multi-stage) or single RefinementTelemetry (legacy).
  - `sigma_readout_provenance`: String describing sigma source ("cli_override", "calibrated_map", "external_lookup").
  - `sigma_readout_reference_value`: Scalar sigma_readout in target units (after ADU→photon conversion if applicable).
  - `stage_artifacts`: Dict[str, Any] from RefinementEngine.artifacts containing stage-specific metadata (ARCH-STAGE-CONTEXT-001).
  - `roi_payloads`: List[ROIAnalysisPayload] from `dbex.io.roi_scoring.score_roi_payloads` (ARCH-BRIDGE-RESP-001 Phase B.3). Required (non-None). Pre-scored ROI triptychs with populated `score`, `optimal_scale`, `model`, and `variance` fields. Inline Nelder-Mead loop removed; passing None raises ValueError.
- **Outputs:**
  - HDF5 file at `args.outFile` with:
    - `/torch_diagnostics` group (attributes): `masked_mse`, `loss_mask_coverage`, `n_rois`, `target_shape`, `backend`, `sigma_floor`, optional: `adu_per_photon`, `sigma_readout_provenance`, `sigma_readout_reference_value`, plus Phase B.3 telemetry: `roi_scoring_method="nelder_mead"`, `roi_checker="score_trainer.roi_check.roiCheck"`.
    - `/torch_diagnostics/hkl_telemetry` (attributes): `hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path`.
    - `/torch_diagnostics/refine_telemetry` (JSON string): Serialized Dict[str, RefinementTelemetry.to_dict()].
    - Per-ROI datasets: `/data/roi<i>`, `/model/roi<i>`, `/bragg/roi<i>`, `/bg/roi<i>`, `/variance/roi<i>`, `/score`, `/bragg_scale`.
- **Telemetry/Diagnostics:**
  - All `/torch_diagnostics` fields are persisted in HDF5 attributes for downstream replay/audit.
  - Variance computation follows spec-db-core.md §86-90: `V = max(I_model + sigma_rdout^2, sigma_floor^2)` (computed by `score_roi_payloads` helper in Phase B.3).
  - Phase B.3: Writer consumes typed `List[ROIAnalysisPayload]` from `score_roi_payloads` helper (no inline optimization). ROI telemetry attrs record scoring provenance.
- **Default Provenance:**
  - ROI scoring: Delegated to `dbex.io.roi_scoring.score_roi_payloads` (Phase B.3 complete; inline Nelder-Mead removed).
  - Variance: Computed by `score_roi_payloads` per spec-db-core.md §86-90 using `sigma_readout`/`sigma_floor` parameters.
- **Purpose:**
  - Canonical torch backend HDF5 writer consolidating ROI scoring, telemetry serialization, and `/torch_diagnostics` schema emission.
  - Byte-for-byte compatible with prior `dbex.refine_one._write_torch_outputs` (DIAGNOSTICS-001).
  - Supports multi-stage telemetry (Dict[str, RefinementTelemetry]) for Stage A/B/C aggregation (ARCH-ENGINE-003).

## Maintainer Notes

- When adding a new helper or CLI under `plans/` that consumes dataset assets, append an entry here describing its inputs and overrides.
- When modifying an existing helper's data sourcing (e.g., swapping HKL defaults), update this manifest and the helper docstring in the same commit.
- Supervisors should reference this manifest before issuing Do Nows to ensure planned work accounts for the helper's real dependencies.
