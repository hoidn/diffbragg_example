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
  - `DBEX_SMOKE_HKL_PATH` overrides HKL file (default `scaled.mtz`).
  - `DBEX_SMOKE_CALIB_PATH` (planned) to forward calibration config to mapping helpers.
- **Default Provenance:** `scaled.mtz` for HKL; no calibration field is currently exposed (needs addition).
- **Telemetry/Diagnostics:** Stage A smoke metrics emit `hkl_source`, `hkl_path`, `spot_scale_override`, `sigma_source`.

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

## Maintainer Notes

- When adding a new helper or CLI under `plans/` that consumes dataset assets, append an entry here describing its inputs and overrides.
- When modifying an existing helper’s data sourcing (e.g., swapping HKL defaults), update this manifest and the helper docstring in the same commit.
- Supervisors should reference this manifest before issuing Do Nows to ensure planned work accounts for the helper’s real dependencies.
