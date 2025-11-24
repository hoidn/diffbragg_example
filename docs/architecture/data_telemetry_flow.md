# Data and Telemetry Flow (Current Implementation)
Scope: descriptive of current implementation; normative behavior lives in docs/spec-db*.md.

Textual flow for the shipped pipelines (torch default, DiffBragg legacy) showing where data and telemetry move and where paths diverge.

## End-to-End Pipeline
Inputs (Expt/Refl/MTZ, mask, optional refined MTZ, torch_config, sigma map, gain)
→ `DataLoad` (MTZ Bijvoet mates, Experiment selection, reflections filter, raw image stack, ROI bboxes/pids/background, trusted mask, sigma map, detector/beam/crystal fixtures)
→ `prepare_refinement_inputs` (background-subtracted target, loss_mask=(bg>=0)&trusted, sigma tensor, ROI slices, ADU↔photon conversion, global_scale_hint)
→ Zero-iteration simulation (per-panel Simulator via unified factory; spot_scale applied post-sim)
→ Stage A LBFGS (scale + crystal) ± Stage B (|F| shell modifiers) ± Stage C (detector distance offsets) [inline vs engine delegation]
→ ROI scoring (Nelder–Mead per-ROI optimal scale vs background)
→ HDF5 write + optional triptych PNG export

## Divergence Points
- Backend: `--backend nanobrag` (torch) vs `--backend diffbragg` (legacy).
- Refinement path: inline `run_nanobrag_refinement` vs `RefinementEngine` delegation (optional flag).
- Warm-cache: planned but blocked (ENV-CUDA-001); current runs are cold per panel/ROI.
- Stage gating: Stage B/C only when `--use-engine-delegation` plus `--enable-stage-b/--enable-stage-c`.

## Telemetry and Artifacts
- HDF5 datasets per ROI: data, model, bragg, bg, variance; per-ROI `score`, `bragg_scale`.
- `/torch_diagnostics` attrs: masked_mse, loss_mask_coverage, n_rois, target_shape, backend id; HKL telemetry (source, count, mean, path); sigma provenance/reference; calibration source; per-stage refinement telemetry (optimizer params, loss/chi² traces, param deltas, detector distances, ROI sampling, variance-floor clamp fraction).
- Triptych reporting: optional `--report-dir` generates ROI PNGs via `dbex.vis.plot_triptych`.
- DiffBragg path shares ROI datasets/score/variance but lacks torch stage telemetry.

## Devices and Dtypes
- Device selection via `--device` (torch path). Fallback to CPU if CUDA unavailable.
- Dtype: float32 for tensors/outputs; variance math uses float64 intermediates in prep, cast to float32.

## Masks and Sentinels
- Loss mask: `(background >= 0) & trusted`.
- Background sentinel: -1 outside ROI; validated before prep.
- Trusted mask polarity: True=include; enforced at load/prep time.

## Calibration Thread
- sigma_readout: CLI scalar or map, or dxtbx external_lookup; converted to target units (photons if gain provided).
- sigma_floor: clamp in loss and variance export; converted with gain when applicable.
- spot_scale_override: calibration metadata preferred, else CLI, else default 1.0; applied post-sim.
- Structure factors: prefer refined MTZ when provided; else raw MTZ. HKL telemetry records source/path.*** End Patch
