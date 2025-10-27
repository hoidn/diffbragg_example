# spec-db-interfaces.md — CLI/API (Normative)

Overview (Normative)
- Purpose: Define the CLI/API surface and precedence rules required to satisfy the workflow spec.

Status
- The CLI flags described here (e.g., `--backend`, `--device`, `--adu-per-photon`, `--nabc`, `--debug-save-artifacts`) apply to the planned `nanobrag_torch` backend. They are not implemented in the current CLI.
- Until the torch backend lands, use the existing DiffBragg entry point: `python -m dbex.refine_one` (see `dbex/refine_one.py:5-26`).

CLI Flags (Normative)
- `--backend {diffbragg,nanobrag}`: selects implementation; default MAY be `nanobrag` once stable.
- `--adu-per-photon <float>`: converts ADU→photons for target; if omitted, ADU target with learnable global scale.
- `--nabc <Na Nb Nc>`: sets `CrystalConfig.N_cells`; default `(20,20,20)` for parity with xtal_refine.
- `--device <cuda|cpu>:<index>`: selects device.
- `--debug-save-artifacts`: persist otherwise temporary artifacts (HKL, etc.).
- `--optimizer {lbfgs,adam}` (optional): selects optimizer; default SHALL be `lbfgs` for Stage A/C, `adam` MAY be used only for Stage B if chosen.

API Contracts (Normative)
- Data bridge SHALL expose:
  - `target_tensor` (float, device‑local), `bg_mask_tensor` (bool), `trusted_mask_tensor` (bool), `panel_slices`.
  - Panel configs (DetectorConfig per panel), BeamConfig, CrystalConfig seeded from dxtbx.
- Torch model entry SHALL expose:
  - `run_nanobrag_refinement(inputs, optimizer_cfg) -> (bragg_tensor, history)`.

Precedence Rules (Normative)
- CLI flag values SHALL override values inferred from Experiment metadata.
- Environment variables SHALL provide defaults (e.g., device), overridden by CLI.

Error Conditions (Normative)
- Rectangular pixel panels SHALL error (unless per‑pitch Detectors are constructed explicitly outside the single‑panel mapping).
- Mask/array shape mismatches SHALL error.
- Missing required inputs (Experiment, Reflections, MTZ) SHALL error.

References (Informative)
- docs/spec-db-core.md, docs/spec-db-workflow.md, docs/config_crosswalk.md.
