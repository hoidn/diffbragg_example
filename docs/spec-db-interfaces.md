# spec-db-interfaces.md — CLI/API (Normative)

Overview (Normative)
- Purpose: Define the CLI/API surface and precedence rules required to satisfy the workflow spec.

Status
- The `--backend {diffbragg,nanobrag}` flag is implemented in the current CLI (`dbex/refine_one.py`). Default is `diffbragg` (legacy) and SHALL remain so until a Spec‑DB version bump explicitly changes it. The `nanobrag` backend is implemented (Stage A on by default; Stage B/C behind flags) and writes torch diagnostics. Tests: `tests/dbex/test_refine_one_cli.py` (selector: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py`).
- Other flags (`--device`, `--adu-per-photon`, `--nabc`, `--debug-save-artifacts`) remain planned pending full torch simulator integration and hardening.

CLI Flags (Normative)
- `--backend {diffbragg,nanobrag}`: selects implementation; default SHALL remain `diffbragg` until an explicit Spec‑DB version bump/changelog changes it. DB‑AT conformance applies only to `--backend nanobrag` (torch backend); DiffBragg (`--backend diffbragg`) MAY have diagnostic smokes but SHALL NOT be advertised as Spec‑DB conformant.
- `--adu-per-photon <float>`: converts ADU→photons for target; if omitted, ADU target with learnable global scale.
- `--torch-config <path>`: Path to DiffBragg `config_torch.json`. Provides authoritative calibration metadata (spot_scale_override, flux/exposure/beamsize, N_cells, gain). If a CLI flag supplies a different value for the same field, the run SHALL fail fast (no silent override).
- `--device <cuda|cpu>:<index>`: selects device. Spec‑DB v1 conformance requires a CPU run; CUDA (e.g., `cuda:0`) is permitted but is considered experimental unless a future CUDA conformance profile is defined and exercised.
- `--debug-save-artifacts`: persist otherwise temporary artifacts (HKL, etc.).
- `--optimizer {lbfgs,adam}` (optional): selects optimizer; default SHALL be `lbfgs` for Stage A/C, `adam` MAY be used only for Stage B if chosen.
- `--sigma-rdout <float>`: scalar detector readout noise in the same units as the target (ADU by default, converted to photons when `--adu-per-photon` is set); required when no calibrated sigma map is available.
- `--sigma-map <path>`: calibrated `sigma_readout` map (e.g. `.npy/.npz` or pickled per-panel arrays) shaped `[panel, slow, fast]`; takes precedence over `--sigma-rdout` when provided.
- `--sigma-floor <float>`: variance floor guard in target units (ADU or photons). Defaults to instrument readout noise when unspecified; clamps `V` to `sigma_floor^2` per spec-db-core.md.
- Torch stage toggles (torch backend only; experimental): `--use-engine-delegation` (engine wrapper path), `--enable-stage-b`, `--enable-stage-c` (require delegation).

API Contracts (Normative)
- Data bridge SHALL expose:
  - `target_tensor` (float, device‑local), `bg_mask_tensor` (bool), `trusted_mask_tensor` (bool), `panel_slices`.
  - Panel configs (DetectorConfig per panel), BeamConfig, CrystalConfig seeded from dxtbx.
- Torch model entry SHALL expose:
  - `run_nanobrag_refinement(inputs, optimizer_cfg) -> (bragg_tensor, history)`.

Precedence Rules (Normative)
- CLI flag values SHALL override values inferred from Experiment metadata.
- Environment variables SHALL provide defaults (e.g., device), overridden by CLI.
- Detector readout noise (`sigma_readout`) SHALL follow the precedence chain `--sigma-map` (calibrated tensor) > `--sigma-rdout` (scalar) > Experiment metadata external_lookup tiles, as detailed in `docs/TESTING_GUIDE.md` and `spec-db-core.md`. When none of `--sigma-map`, `--sigma-rdout`, or external tiles are available, the CLI SHALL error (no silent defaults such as legacy ~3 ADU fallbacks).

Error Conditions (Normative)
- Rectangular pixel panels SHALL error (unless per‑pitch Detectors are constructed explicitly outside the single‑panel mapping).
- Mask/array shape mismatches SHALL error.
- Missing required inputs (Experiment, Reflections, MTZ) SHALL error.
- When a normative “SHALL error” condition triggers (e.g., missing sigma, non-square pixels), the CLI MUST exit non‑zero and SHALL NOT emit a viewer HDF5 that could be mistaken for valid output; diagnostic artifacts MAY be written to a separate debug path.

HDF5 Output Schema (Normative)
- Required groups/datasets for viewer/telemetry outputs:
  - `/data`, `/model`, `/bragg`, `/bg`, `/variance` (or equivalent) and ROI `score` datasets.
  - `/torch_diagnostics` attributes SHALL include at least: `backend`, `unit_mode`, `adu_per_photon`, `sigma_readout_provenance`, `sigma_floor` and provenance, `spot_scale_override`, `beam_flux`, `beam_exposure`, `beamsize_mm`, `N_cells`, HKL source/path, interpolation/halo flags, and `device_profile` (e.g., `cpu_conformance`, `cuda_experimental`).
  - `/trace/<panel>/<slow>_<fast>/` groups SHALL follow `spec-db-tracing.md`.
- Implementations MAY add extra fields but MUST supply these minima for conformance. Telemetry MUST record provenance for any defaulted calibration fields.

References (Informative)
- docs/spec-db-core.md, docs/spec-db-workflow.md, docs/config_crosswalk.md.
