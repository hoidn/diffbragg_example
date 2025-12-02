Analysis question: Why do Stage B shell modifiers and Stage C detector offsets fail to reduce chi-squared on the canonical detector during PERF-SMOKE-DETSIZE smokes?
Fix-plan context: REFINE-007/008 require measurable Stage C detector shrinkage and Stage B non-regression telemetry when `DBEX_SMOKE_DETECTOR_SIZE=full`.

1. tests/dbex/test_torch_refine_smoke.py:716-877 — Stage B/C smoke harness
   - Stage C (`test_stage_c_detector_microslip`) perturbs detector geometry via `create_perturbed_geometry` (line 79) then invokes `run_nanobrag_refinement` with `enable_stage_c=True`, recording gate metrics through `_record_stage_telemetry` (line 34).
   - Stage B (`test_stage_b_shell_modifiers`) loads canonical refGeom assets, enforces haloed HKL metadata, configures `RefinementConfig(enable_stage_b=True, stage_b_n_shells=5, enable_hkl_interpolation=True)` and expects ≥identity telemetry plus ≤1e-6 chi-squared regression.
   - Both selectors rely on `DBEX_SMOKE_TELEMETRY_PATH` to dump chi-squared traces; failures currently stem from flat telemetry (Stage C) and runtime errors (Stage B).

2. dbex/nanobrag_refinement.py:485-1188 — Stage A nucleus feeding later stages
   - Builds Stage A parameters (log-scale, log-cell deltas, orientation vector) and ROI sampler (`sampled_panel_ids`, line 659) reused by Stage B/C.
   - After Stage A LBFGS finishes, persists `best_loss_full`, `chi_squared_best`, and ROI/perf counters referenced when calibrating subsequent stages.
   - Baseline misset tensors + final cell deltas are kept in-scope for Stage B/C closures, so corruption here propagates into detector or shell refinements.

3. dbex/nanobrag_refinement.py:1195-1669 — Stage B shell-modifier refinement
   - Guards enforce haloed HKL grids and tricubic interpolation before freezing Stage A tensors and computing shell lookup via `compute_hkl_shell_lookup` (line 1208).
   - `compute_loss_stage_b` (line 1286) clones HKL grids, applies softplus-clamped modifiers, regenerates per-panel Detector/Crystal configs through `create_detector_config` (dbex/nanobrag_bridge.py:276-355) and `Simulator.run()` (nanobrag_torch/simulator.py:421) on either CPU or CUDA.
   - LBFGS closure accumulates chi-squared + masked-MSE telemetry; however `chi_squared_best_b`, `best_loss_full_b`, and `best_params_snapshot_b` are updated inside the closure without `nonlocal`, yielding the `UnboundLocalError` seen at plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log:486 and preventing any optimizer step.
   - HDF5-ready telemetry is assembled at line 1660, but with Stage B never finishing, the smoke gate compares Stage A vs Stage A (no shell modifiers applied).

4. dbex/nanobrag_refinement.py:1689-2045 — Stage C detector microslip refinement
   - Initializes `distance_offset_raw` tensors (line 1696), binds them to an LBFGS optimizer, and defines `compute_loss_stage_c` (line 1732) which rebuilds per-panel detector configs via `create_detector_config(..., distance_mm_override=distance_override)` so `Detector.distance_mm` receives the perturbation.
   - During loss evaluation each panel reruns the simulator with Stage A’s frozen crystal tensors; `_accumulate_variance_weighted_loss` feeds dual metrics, and telemetry arrays (`chi_squared_trace_full_c`, `variance_floor_*`) capture validation history.
   - Telemetry serialization (line 2017) currently records `param_deltas_c[f'panel_{pid}_distance_offset_mm']` with `'initial': 0.0`, `final=tanh(distance_offset_raw)*max_delta`. Because the injected ±0.25 mm offsets live only inside `perturbed_detector`, the Stage C test compares zero-initialized telemetry values against Stage C’s own trainables, so even a no-op run appears to achieve 100 % reduction, masking the fact that `chi_squared_trace_full` never drops from Stage A’s baseline (telemetry JSON shows flat 2.94089696e8).

5. dbex/nanobrag_bridge.py:276-355 → nanobrag_torch stack
   - `create_detector_config` maps dxtbx panels into torch `DetectorConfig` objects, accepting optional `distance_mm_override` used exclusively by Stage C to push offsets into the simulator.
   - Each Stage B/C loss evaluation instantiates `nanobrag_torch.models.Detector` (models/detector.py:24-189) followed by `nanobrag_torch.Simulator` (simulator.py:421-520), which in turn calls `crystal.get_structure_factor` / `_tricubic_interpolation` (models/crystal.py:210-427). This path re-allocates the full 4×4×4 HKL neighborhoods per ROI; without ROI downsampling Stage B hits CUDA OOM before the LBFGS loop reaches a gradient step (stage_b_fail.log shows `OutOfMemoryError` at models/crystal.py:427 for the full detector grid).

6. Telemetry capture + artifacts
   - `_record_stage_telemetry` (tests/dbex/test_torch_refine_smoke.py:34-55) writes `loss_trace_full` and `chi_squared_trace_full` from the telemetry structs. Because Stage C’s struct never reflects the injected offsets, artifacts like `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/telemetry_probe.json` show repeated entries with zero improvement, validating the need to instrument baseline offsets or per-panel simulator outputs.

Key spec anchors: docs/spec-db-workflow.md:31-41 (staged refinement contracts), docs/architecture.md:20-43 (Stage B/C responsibilities), docs/pytorch_runtime_checklist.md §1.3 (device/dtype neutrality), docs/development/testing_strategy.md §2.1 (smoke telemetry gating).
