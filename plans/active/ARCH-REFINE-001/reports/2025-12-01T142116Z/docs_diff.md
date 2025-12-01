diff --git a/docs/architecture/module_map.md b/docs/architecture/module_map.md
index d1f27bf2..8734b15e 100644
--- a/docs/architecture/module_map.md
+++ b/docs/architecture/module_map.md
@@ -12,7 +12,9 @@ Use this as a quick navigation guide; status reflects current intent (active vs
 | `dbex/nanobrag_refinement.py` | Legacy inline staged refinement (Stage A/B/C helpers kept for compatibility) | `run_nanobrag_refinement`, Stage helpers | `test_torch_refine_smoke.py`, `test_stage_b_asu_mapping.py`, `test_ub_parameterization_roundtrip.py` | Legacy (kept until ARCH-REFINE-001 removes inline path) |
 | `dbex/refinement/engine.py` | Protocol engine sequencing, telemetry aggregation | `RefinementEngine.run` | `test_refinement_engine.py`, ARCH-REFINE-FLOW-001 | Active (target path) |
 | `dbex/refinement/stage_a.py` / `stage_b.py` / `stage_c.py` | Stage wrappers over core helpers, stage telemetry | `StageA.run`, `StageB.run`, `StageC.run` | `test_refinement_engine.py`, stage smokes | Active |
-| `dbex/physics/loss.py` | Variance-weighted chi² and masked MSE | `_compute_variance_weighted_loss` | `test_physics_loss_current.py`, PHYSICS-LOSS-001 | Active |
+| `dbex/io/writer.py` | HDF5 telemetry writer, `/torch_diagnostics` schema | `write_torch_outputs` | `test_torch_diagnostics_metadata` | Active ([IDL](dbex/io/writer.idl.md)) |
+| `dbex/physics/forward.py` | Forward simulation helpers (TEST-ONLY, DB-AT-010) | `simulate_forward_torch` | `test_gradients.py::TestDB_AT_010_Gradcheck` | Active ([IDL](dbex/physics/forward.idl.md)) |
+| `dbex/physics/loss.py` | Variance-weighted chi² and masked MSE | `_compute_variance_weighted_loss`, `compute_masked_mse_loss` | `test_physics_loss_current.py`, PHYSICS-LOSS-001 | Active ([IDL](dbex/physics/loss.idl.md)) |
 | `dbex/geometry/crystallography.py` | U/B geometry helpers (leaf) | `derive_u_matrix_from_mosflm_a_star` | `test_geometry_current.py` | Active |
 | `dbex/refinement/helpers.py` | Simulator wiring seam | `create_unified_simulator` | `test_sim_factory.py`, forward-equivalence | Active |
 | `dbex/tools/stage_a_adam.py` | Stage A probes/tooling | `build_dataload`, `run_forward_model_probe`, etc. | `test_stage_a_adam_tooling.py`, TOOLING-VIS-001 | Active |
@@ -24,4 +26,5 @@ Notes:
 - RefinementEngine is the target path; inline helpers remain only as a compatibility shim until ARCH-REFINE-001 completes.
 - Warm-cache reuse is blocked (PERF-WARM-SIM-001) and not reflected above.
 - Quaternion/U-matrix parameterization is deprecated (TORCH-GEOMETRY-PARITY-002/003); incremental UB is current.
+- ARCH-REFINE-001 Phase D.1 complete: IDL contracts published for `dbex/io/writer.py`, `dbex/physics/forward.py`, `dbex/physics/loss.py`. See [writer.idl.md](dbex/io/writer.idl.md), [forward.idl.md](dbex/physics/forward.idl.md), [loss.idl.md](dbex/physics/loss.idl.md).
 - ARCH-REFINE-001 Phase C complete: `dbex/io/writer.py` (HDF5 telemetry writer), `dbex/physics/{forward,loss}.py` (shared physics helpers) are now active. `refinement/context.py` and `JobContext` remain in progress (Phase B).
