diff --git a/docs/architecture/data_telemetry_flow.md b/docs/architecture/data_telemetry_flow.md
index 1d9d2c2c..5b7a88ec 100644
--- a/docs/architecture/data_telemetry_flow.md
+++ b/docs/architecture/data_telemetry_flow.md
@@ -11,7 +11,7 @@ Inputs (Expt/Refl/MTZ, mask, optional refined MTZ, torch_config, sigma map, gain
 → Zero-iteration simulation (per-panel Simulator via unified factory for forward-only paths; spot_scale applied post-sim)
 → `RefinementEngine` stages (Stage A/B/C LBFGS) consuming the contexts; Stage closures keep their direct `Simulator` models for autograd
 → ROI scoring (Nelder–Mead per-ROI optimal scale vs background)
-→ Torch writer (`dbex/io/writer.py`, planned) emits HDF5 + optional triptych PNG export
+→ Torch writer (`dbex/io/writer.py`, ARCH-REFINE-001 Phase C.2/C.4 complete) emits HDF5 + optional triptych PNG export
 
 ## Divergence Points
 - Backend: `--backend nanobrag` (torch target) vs `--backend diffbragg` (legacy baseline).
diff --git a/docs/architecture/live_backend.md b/docs/architecture/live_backend.md
index 5300750a..38eb550d 100644
--- a/docs/architecture/live_backend.md
+++ b/docs/architecture/live_backend.md
@@ -20,7 +20,7 @@ Purpose: Describe the *shipped* pipelines (torch + DiffBragg), where they diverg
 - Zero-iteration sim: loop per panel, runs nanobrag_torch Simulator via the factory; applies `sqrt(spot_scale_override)` post-sim.
 - Refinement: `RefinementEngine` + `StageA/B/C` is the target. Stage A optimizes scale + full crystal (incremental UB param), Stage B optional shell |F| modifiers, Stage C optional detector distance offsets. Inline execution remains only as a compatibility shim until ARCH-REFINE-001 removes it.
 - Loss: variance-weighted chi² + masked MSE (`dbex/physics/loss.py`), sigma_floor clamping, ROI sampling; warm-cache reuse planned but blocked (ENV-CUDA-001; PERF-WARM-SIM-001).
-- Outputs: the torch backend is migrating to a dedicated writer (`dbex/io/writer.py`, ARCH-REFINE-001 Phase C) that emits per-ROI datasets (data/model/bragg/bg/variance), per-ROI optimal scales/scores, sigma metadata, and `/torch_diagnostics` attrs (masked_mse, loss_mask_coverage, HKL source/path, sigma provenance/reference, backend, per-stage telemetry). Until that lands, `_write_torch_outputs` remains embedded in `refine_one.py`.
+- Outputs: the torch backend uses a dedicated writer (`dbex/io/writer.py`, ARCH-REFINE-001 Phase C.2/C.4 complete) that emits per-ROI datasets (data/model/bragg/bg/variance), per-ROI optimal scales/scores, sigma metadata, and `/torch_diagnostics` attrs (masked_mse, loss_mask_coverage, HKL source/path, sigma provenance/reference, backend, per-stage telemetry). Physics helpers for forward simulation and loss computation are centralized in `dbex/physics/forward.py` and `dbex/physics/loss.py` (PHYSICS-LOSS-001).
 
 ## DiffBragg Legacy Backend (default)
 - Path: `dbex/run_diffbragg.py` invoked via `run_diffbragg_backend` in `refine_one.py`.
@@ -42,4 +42,4 @@ Purpose: Describe the *shipped* pipelines (torch + DiffBragg), where they diverg
 - Refinement core: `run_nanobrag_refinement(inputs, detector, beam, crystal, hkl_grid, hkl_metadata, config, use_engine_delegation=False)` → `(Bragg, telemetry_dict)`; `RefinementConfig` carries device/dtype, sigma_floor_value, sigma_readout provenance/reference, stage flags, calibration payload.
 - Engine path: `RefinementEngine(stages, config).run(inputs_dict)` expects stage wrappers `StageA/B/C.run(inputs_dict, telemetry_sink=None)` returning dicts compatible with `RefinementTelemetry`.
 - Telemetry class: `RefinementTelemetry` key fields include optimizer/stage metadata, loss/chi² traces, param_deltas, clamp fractions, ROI sampling counts, canonical detector distances (Stage C), stage_type/mode, engine_protocol/stage_modes; `to_dict()` used for HDF5 serialization.
-- HDF5 writer: `_write_torch_outputs(args, DL, Bragg, inputs, masked_mse, hkl_telemetry, refine_telemetry, sigma_readout_provenance, sigma_readout_reference_value)` writes per-ROI datasets and `/torch_diagnostics` attrs (masked_mse, loss_mask_coverage, n_rois, target_shape, backend, HKL telemetry, sigma provenance/reference, stage telemetry).
+- HDF5 writer: `dbex.io.writer.write_torch_outputs(args, DL, Bragg, inputs, masked_mse, hkl_telemetry, refine_telemetry, sigma_readout_provenance, sigma_readout_reference_value)` writes per-ROI datasets and `/torch_diagnostics` attrs (masked_mse, loss_mask_coverage, n_rois, target_shape, backend, HKL telemetry, sigma provenance/reference, stage telemetry). Canonical location is `dbex/io/writer.py` (DIAGNOSTICS-001, REFINE-010).
diff --git a/docs/architecture/module_map.md b/docs/architecture/module_map.md
index 937ce7fb..d1f27bf2 100644
--- a/docs/architecture/module_map.md
+++ b/docs/architecture/module_map.md
@@ -24,4 +24,4 @@ Notes:
 - RefinementEngine is the target path; inline helpers remain only as a compatibility shim until ARCH-REFINE-001 completes.
 - Warm-cache reuse is blocked (PERF-WARM-SIM-001) and not reflected above.
 - Quaternion/U-matrix parameterization is deprecated (TORCH-GEOMETRY-PARITY-002/003); incremental UB is current.
-- ARCH-REFINE-001 will add `refinement/context.py`, `JobContext`, and a torch-only `dbex/io/writer.py` entry once those modules land.
+- ARCH-REFINE-001 Phase C complete: `dbex/io/writer.py` (HDF5 telemetry writer), `dbex/physics/{forward,loss}.py` (shared physics helpers) are now active. `refinement/context.py` and `JobContext` remain in progress (Phase B).
