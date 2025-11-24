# DBEX Implementation Architecture — Current Backends
Scope: descriptive of current implementation; normative behavior lives in docs/spec-db*.md.

Purpose: Describe the *shipped* pipelines (torch + DiffBragg), where they diverge, and the migration intent. This is not the forward-looking design; it documents what runs today.

## Entrypoints and Modes
- CLI: `dbex/refine_one.py` (`python -m dbex.refine_one ...`).
- Backends: `--backend nanobrag` (torch, default) | `--backend diffbragg` (legacy).
- Engine delegation: optional flag `--use-engine-delegation`; inline path remains the default. Migration intent: make delegation the default and remove the inline path once Phase C of ARCH-REFACTOR-001 resumes.
- Stage toggles: `--enable-stage-b`, `--enable-stage-c` (torch only; require delegation).

## Ingestion (shared)
- `dbex/data_load.py`: loads MTZ (Bijvoet mates), Experiment/Reflections, raw image stack, ROI bboxes/pids/background (`simtbx.diffBragg.utils.get_roi_background_and_selection_flags`), trusted mask (pickle, True=trusted), sigma_readout map (CLI `--sigma-map` or dxtbx `external_lookup`), detector/beam/crystal fixtures.
- Guardrails: square-pixel enforcement, trusted-mask polarity check, background sentinel checks, sigma map shape/positivity/finite checks.

## Torch Backend (nanobrag)
- Preparation: `dbex/nanobrag_bridge.py::prepare_refinement_inputs` builds background-subtracted targets, loss mask `(background >= 0) & trusted`, ROI slices, sigma tensors, ADU↔photon conversion, global_scale_hint (ADU).
- Configs: `create_detector_config`/`create_beam_config`/`create_crystal_config` map dxtbx geometry → nanobrag_torch configs; unified simulator factory in `dbex/refinement/helpers.py`.
- Zero-iteration sim: loop per panel, runs nanobrag_torch Simulator via factory; applies `sqrt(spot_scale_override)` post-sim.
- Refinement: `dbex/nanobrag_refinement.py` (inline path) or engine delegation (`dbex/refinement/engine.py` + `stage_a/b/c.py`). Stage A optimizes scale + full crystal (incremental UB param), Stage B optional shell |F| modifiers, Stage C optional detector distance offsets. Engine delegation is implemented but not default.
- Loss: variance-weighted chi² + masked MSE (`dbex/physics/loss.py`), sigma_floor clamping, ROI sampling; warm-cache reuse planned but blocked (ENV-CUDA-001; PERF-WARM-SIM-001).
- Outputs: HDF5 with per-ROI datasets (data/model/bragg/bg/variance), per-ROI optimal scales/scores, sigma metadata. `/torch_diagnostics` attrs include masked_mse, loss_mask_coverage, HKL source/path, sigma provenance/reference, backend, and per-stage refinement telemetry (optimizer params, loss/chi² traces, param_deltas, detector distances, ROI sampling, calibration source).

## DiffBragg Legacy Backend
- Path: `dbex/run_diffbragg.py` invoked via `run_diffbragg_backend` in `refine_one.py`.
- Flow: runs legacy DiffBragg pipeline to produce Bragg image; per-ROI Nelder–Mead scale fit vs background; writes HDF5 (data/model/bragg/bg/variance, per-ROI scores/scales, sigma metadata). Uses same viewer (`dbex/look.py`) and optional triptych export.
- Hygiene: scratch artifacts cleanup and telemetry parity pending (ARCH-REFACTOR-001 exit criterion #7).

## Migration and Status
- Delegation intent: make engine delegation the default torch path; remove inline refinement once Phase C (SimulationContext + single simulator seam) is completed.
- Deprecated/archived: quaternion/U-matrix parameterization (TORCH-GEOMETRY-PARITY-002/003) is superseded by incremental UB (UB-REALIGN-001).
- Warm-cache: reuse infrastructure partially planned; blocked by ENV-CUDA-001 (PERF-WARM-SIM-001).
- DiffBragg: retained for compatibility; not the target architecture.*** End Patch
