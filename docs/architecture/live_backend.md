# DBEX Implementation Architecture — Current Backends
Scope: descriptive of current implementation; normative behavior lives in docs/spec-db*.md.

Purpose: Describe the *shipped* pipelines (torch + DiffBragg), where they diverge, and the migration intent. This is not the forward-looking design; it documents what runs today.

## Entrypoints and Modes
- CLI: `dbex/refine_one.py` (`python -m dbex.refine_one ...`).
- Backends: `--backend diffbragg` (legacy, default) | `--backend nanobrag` (torch, the target architecture).
- Refinement engine: `RefinementEngine` + `StageA/B/C` is the normative path; the inline helpers in `dbex/nanobrag_refinement.py` remain only for compatibility until ARCH-REFINE-001 finishes removing them.
- Stage toggles: `--enable-stage-b`, `--enable-stage-c` (torch only; wired into the engine configuration).

## Ingestion (shared)
- `dbex/data_load.py`: loads MTZ (Bijvoet mates), Experiment/Reflections, raw image stack, ROI bboxes/pids/background (`simtbx.diffBragg.utils.get_roi_background_and_selection_flags`), trusted mask (pickle, True=trusted), sigma_readout map (CLI `--sigma-map` or dxtbx `external_lookup`), detector/beam/crystal fixtures.
- Guardrails: square-pixel enforcement, trusted-mask polarity check, background sentinel checks, sigma map shape/positivity/finite checks.

## Torch Backend (nanobrag — target backend)
- Preparation: `dbex/nanobrag_bridge.py::prepare_refinement_inputs` builds background-subtracted targets, loss mask `(background >= 0) & trusted`, ROI slices, sigma tensors, ADU↔photon conversion, global_scale_hint (ADU).
- Contexts: the forthcoming `RefinementContext`/`JobContext` objects (ARCH-REFINE-001) will carry DataLoad fixtures, calibration payloads, and warmed simulators so Stage modules consume a single structured API.
- Configs: `create_detector_config`/`create_beam_config`/`create_crystal_config` map dxtbx geometry → nanobrag_torch configs; forward-only simulator instantiation is funneled through the unified factory in `dbex/refinement/helpers.py` (Stage closures keep direct `Simulator` objects for autograd).
- Zero-iteration sim: loop per panel, runs nanobrag_torch Simulator via the factory; applies `sqrt(spot_scale_override)` post-sim.
- Refinement: `RefinementEngine` + `StageA/B/C` is the target. Stage A optimizes scale + full crystal (incremental UB param), Stage B optional shell |F| modifiers, Stage C optional detector distance offsets. Inline execution remains only as a compatibility shim until ARCH-REFINE-001 removes it.
- Loss: variance-weighted chi² + masked MSE (`dbex/physics/loss.py`), sigma_floor clamping, ROI sampling; warm-cache reuse planned but blocked (ENV-CUDA-001; PERF-WARM-SIM-001).
- Outputs: the torch backend uses a dedicated writer (`dbex/io/writer.py`, ARCH-REFINE-001 Phase C.2/C.4 complete) that emits per-ROI datasets (data/model/bragg/bg/variance), per-ROI optimal scales/scores, sigma metadata, and `/torch_diagnostics` attrs (masked_mse, loss_mask_coverage, HKL source/path, sigma provenance/reference, backend, per-stage telemetry). Physics helpers for forward simulation and loss computation are centralized in `dbex/physics/forward.py` and `dbex/physics/loss.py` (PHYSICS-LOSS-001).

## DiffBragg Legacy Backend (default)
- Path: `dbex/run_diffbragg.py` invoked via `run_diffbragg_backend` in `refine_one.py`.
- Flow: runs legacy DiffBragg pipeline to produce Bragg image; per-ROI Nelder–Mead scale fit vs background; writes HDF5 (data/model/bragg/bg/variance, per-ROI scores/scales, sigma metadata). Uses same viewer (`dbex/look.py`) and optional triptych export.
- Hygiene: scratch artifacts cleanup and telemetry parity pending (ARCH-REFACTOR-001 exit criterion #7).

## Migration and Status
- Refinement path: `RefinementEngine` + contexts will become the only code path once ARCH-REFINE-001 Phase A/B completes and the inline helpers are removed.
- IO: a torch-only writer will replace the duplicated HDF5 logic in `refine_one.py`; the diffBragg writer remains frozen for baseline comparisons.
- Deprecated/archived: quaternion/U-matrix parameterization (TORCH-GEOMETRY-PARITY-002/003) is superseded by incremental UB (UB-REALIGN-001).
- Warm-cache: reuse infrastructure partially planned; blocked by ENV-CUDA-001 (PERF-WARM-SIM-001).
- DiffBragg: retained for compatibility; not the target architecture.

## Implementation Interfaces (descriptive)
- `DataLoad(args)`: yields `data`, `background_image`, `bbox`, `pids`, `trusted_mask`, optional `sigma_readout_map`, plus `detector/beam/crystal`, `F` (Bijvoet mates). Mask polarity True=trusted; background sentinel -1 outside ROI.
- `prepare_refinement_inputs(data, background_image, trusted_mask, bbox, pids, detector, adu_per_photon=None, sigma_readout=None, sigma_readout_provenance=None)` → `RefinementInputs` with `target`, `loss_mask`, `panel_slices`, `trusted_mask`, `sigma_readout`, `target_representation`, `global_scale_hint`, `sigma_readout_provenance`.
- Config builders: `create_detector_config(panel, beam, trusted_mask[, distance_mm_override, roi_bbox])`, `create_beam_config(beam[, flux, beamsize_mm, exposure])`, `create_crystal_config(crystal, experiment[, N_cells, apply_n_cells, crystal_overrides, misset_deg_override])`.
- Simulator seam: `create_unified_simulator(detector_config, crystal_config, beam_config, hkl_grid, hkl_metadata, mask_array, spot_scale_override, device, dtype, calibration_metadata=None)` → `(simulator, metadata, sqrt_scale_value, cache_state)`.
- Refinement core: `run_nanobrag_refinement(inputs, detector, beam, crystal, hkl_grid, hkl_metadata, config, use_engine_delegation=False)` → `(Bragg, telemetry_dict)`; `RefinementConfig` carries device/dtype, sigma_floor_value, sigma_readout provenance/reference, stage flags, calibration payload.
- Engine path: `RefinementEngine(stages, config).run(inputs_dict)` expects stage wrappers `StageA/B/C.run(inputs_dict, telemetry_sink=None)` returning dicts compatible with `RefinementTelemetry`.
- Telemetry class: `RefinementTelemetry` key fields include optimizer/stage metadata, loss/chi² traces, param_deltas, clamp fractions, ROI sampling counts, canonical detector distances (Stage C), stage_type/mode, engine_protocol/stage_modes; `to_dict()` used for HDF5 serialization.
- HDF5 writer: `dbex.io.writer.write_torch_outputs(args, DL, Bragg, inputs, masked_mse, hkl_telemetry, refine_telemetry, sigma_readout_provenance, sigma_readout_reference_value)` writes per-ROI datasets and `/torch_diagnostics` attrs (masked_mse, loss_mask_coverage, n_rois, target_shape, backend, HKL telemetry, sigma provenance/reference, stage telemetry). Canonical location is `dbex/io/writer.py` (DIAGNOSTICS-001, REFINE-010).
