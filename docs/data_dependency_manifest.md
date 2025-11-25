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
- **Default Provenance:**
  - HKL: **Current behavior:** still defaults to `scaled.mtz` even when `sp.proc/calibration/config_torch_smoke.json` is present (TOOLING-VIS-001 gap). `DBEX_SMOKE_HKL_PATH` override is the only way to force the refined MTZ today. **Planned fix:** once the Stage A fixture is updated, the default will automatically switch to `sp.proc/calibration/smoke_refined_structure_factors.mtz` whenever the smoke calibration bundle exists and no override is set.
  - Calibration: `sp.proc/calibration/config_torch_smoke.json` when present, otherwise `DBEX_SMOKE_CALIB_PATH` env var.
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

### Refined Structure Factors (`smoke_refined_structure_factors.mtz`)

- **Asset:** `sp.proc/calibration/smoke_refined_structure_factors.mtz`
- **Generation Command:** `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors.mtz --manifest <artifacts-path>/smoke_calibration_manifest.json`
- **Provenance:** DiffBragg-refined structure factors produced during smoke calibration capture; replaces raw `scaled.mtz` amplitudes with variance-weighted refined values.
- **Purpose:** Ensures Stage A mapping and DB-AT-028/029 parity tests consume the same refined structure factors as the calibration metadata, avoiding ROI CC collapse (per SCALE-004 finding).
- **Validation:** Manifest JSON includes SHA256, file size, and generation timestamp; `refgeom_dataload` fixture emits `hkl_source="refined"` when this asset is loaded.
- **Default Behavior:** When `sp.proc/calibration/config_torch_smoke.json` exists, `refgeom_dataload` and mapping helpers default to this refined MTZ unless `DBEX_SMOKE_HKL_PATH` explicitly overrides it.

### Cropped Sigma-Map Asset (refGeom_small)

- **Asset:** `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl`
- **Generation Command:** `plans/active/TOOLING-VIS-001/bin/crop_sigma_map_to_window.py --sigma-map sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl --fast-start 751 --slow-start 719 --width 1024 --height 1024 --output sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl --report <report-path>`
- **Provenance:** Cropped from full-detector metadata sigma-map (`sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl`) to match refGeom_small detector window [fast: 751-1775, slow: 719-1743].
- **Purpose:** Enables metadata sigma-map loading for small-detector smoke fixtures without shape mismatch errors.
- **Validation:** Crop report JSON includes SHA256, file size, panel count, and crop window parameters for reproducibility checks.

## Maintainer Notes

- When adding a new helper or CLI under `plans/` that consumes dataset assets, append an entry here describing its inputs and overrides.
- When modifying an existing helper’s data sourcing (e.g., swapping HKL defaults), update this manifest and the helper docstring in the same commit.
- Supervisors should reference this manifest before issuing Do Nows to ensure planned work accounts for the helper’s real dependencies.
