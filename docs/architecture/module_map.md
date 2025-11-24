# Module Responsibility Map (Current Implementation)
Scope: descriptive of current implementation; normative behavior lives in docs/spec-db*.md.

Use this as a quick navigation guide; status reflects current intent (active vs legacy/deprecated).

| Module / Path | Responsibility | Key Entry / API | Tests / Specs | Status |
| --- | --- | --- | --- | --- |
| `dbex/refine_one.py` | CLI front door, backend switch, calibration flags, HDF5 write, triptych hook | `main()`, `run_nanobrag_backend()`, `run_diffbragg_backend()` | `test_refine_one_cli.py`, `docs/spec-db-interfaces.md` | Active |
| `dbex/data_load.py` | MTZ/Experiment/Reflections ingestion, background/ROI, trusted mask, sigma map | `DataLoad` | `test_data_load_sigma_map.py`, `test_mask_semantics.py`, `test_background_semantics.py` | Active |
| `dbex/nanobrag_bridge.py` | Input prep (target/loss mask), config builders (Detector/Beam/Crystal), HKL grid, baseline misset | `prepare_refinement_inputs`, `create_*_config`, `build_structure_factor_grid` | `test_nanobrag_bridge*.py`, `test_mapping_consistency.py` | Active |
| `dbex/refinement/helpers.py` | Unified simulator factory, cache helpers | `create_unified_simulator` | `test_sim_factory.py`, forward-equivalence tests | Active |
| `dbex/nanobrag_refinement.py` | Inline staged refinement (Stage A/B/C), LBFGS closures, telemetry assembly | `run_nanobrag_refinement`, Stage helpers | `test_torch_refine_smoke.py`, `test_stage_b_asu_mapping.py`, `test_ub_parameterization_roundtrip.py` | Active (inline path slated for deprecation post-Phase C) |
| `dbex/refinement/engine.py` | Protocol engine sequencing, telemetry aggregation | `RefinementEngine.run` | `test_refinement_engine.py`, ARCH-REFINE-FLOW-001 | Active (delegation optional) |
| `dbex/refinement/stage_a.py` / `stage_b.py` / `stage_c.py` | Stage wrappers over core helpers, stage telemetry | `StageA.run`, `StageB.run`, `StageC.run` | `test_refinement_engine.py`, stage smokes | Active |
| `dbex/physics/loss.py` | Variance-weighted chi² and masked MSE | `_compute_variance_weighted_loss` | `test_physics_loss_current.py`, PHYSICS-LOSS-001 | Active |
| `dbex/geometry/crystallography.py` | U/B geometry helpers (leaf) | `derive_u_matrix_from_mosflm_a_star` | `test_geometry_current.py` | Active |
| `dbex/refinement/helpers.py` | Simulator wiring seam | `create_unified_simulator` | `test_sim_factory.py`, forward-equivalence | Active |
| `dbex/tools/stage_a_adam.py` | Stage A probes/tooling | `build_dataload`, `run_forward_model_probe`, etc. | `test_stage_a_adam_tooling.py`, TOOLING-VIS-001 | Active |
| `dbex/vis/*` | Triptych/residual/mapping visuals | `plot_triptych`, `build_mapping_stage_a_context` | `test_vis_triptych*.py` | Active |
| `dbex/run_diffbragg.py` | Legacy DiffBragg pipeline | `run_diffbragg` | `test_diffbragg_tmp.py` (legacy) | Legacy (kept for compatibility) |
| `dbex/diffbragg_tmp.py` | Legacy helper for DiffBragg | Functions for temporary pipelines | Legacy tests | Legacy |

Notes:
- Engine delegation is implemented but not default; inline refinement path remains until ARCH-REFACTOR-001 Phase C completes.
- Warm-cache reuse is blocked (PERF-WARM-SIM-001) and not reflected above.
- Quaternion/U-matrix parameterization is deprecated (TORCH-GEOMETRY-PARITY-002/003); incremental UB is current.*** End Patch
