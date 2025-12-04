# Plan-Local Probe Script Inventory (ARCH-PROBE-FREEZE-001 Phase A)

**Generated:** 2025-12-04
**Inventory Root:** `plans/active/**/bin/*.{py,sh}`
**Total Scripts:** 53

## Executive Summary

This inventory catalogs all plan-local probe scripts to support ARCH-PROBE-FREEZE-001 (Probe Freeze & Logging Consolidation). Classifications follow the diagnostic_script_policy (prompts/supervisor.md:272-287):

- **Thin Wrapper:** Calls owner APIs only; computes simple measurements; writes artifacts. Growth cap: ~400 LOC.
- **Shadow Pipeline:** Re-implements mapping/HKL/ROI/physics/Stage semantics. **FORBIDDEN** under policy.
- **Retire Candidate:** Obsolete/unused scripts that can be deleted.

### Summary Counts by Initiative

| Initiative ID                      | Total | Thin Wrapper | Shadow Pipeline | Retire Candidate | Exceeds 400 LOC |
|------------------------------------|-------|--------------|-----------------|------------------|-----------------|
| ARCH-PROBE-FREEZE-001              | 1     | 1            | 0               | 0                | 0               |
| ARCH-REFACTOR-001                  | 1     | 1            | 0               | 0                | 0               |
| ARCH-REFINE-001                    | 1     | 1            | 0               | 0                | 0               |
| ARCH-REFINE-FLOW-001               | 2     | 2            | 0               | 0                | 0               |
| ARCH-SIM-CONSTRUCTION-001          | 5     | 4            | 1               | 0                | 3               |
| ARCH-SIM-HKL-BOUNDS-001            | 2     | 1            | 1               | 0                | 1               |
| DB-AT-024                          | 1     | 1            | 0               | 0                | 0               |
| DIAG-NANOBRAGG-OVERSAMPLE-001      | 3     | 3            | 0               | 0                | 1               |
| MAP-SCALE-001                      | 3     | 3            | 0               | 0                | 0               |
| NANOBRAG-GOLDEN-001                | 1     | 1            | 0               | 0                | 0               |
| PERF-WARM-SIM-001                  | 5     | 5            | 0               | 0                | 1               |
| PHYSICS-LOSS-001                   | 1     | 0            | 1               | 0                | 1               |
| PORTFOLIO-STATUS                   | 1     | 1            | 0               | 0                | 0               |
| REPORT-NANOBRAG-STATUS-001         | 1     | 1            | 0               | 0                | 0               |
| TOOLING-VIS-001                    | 14    | 11           | 3               | 0                | 6               |
| TORCH-GEOMETRY-PARITY-003          | 1     | 1            | 0               | 0                | 0               |
| TORCH-REFINE-001                   | 1     | 1            | 0               | 0                | 0               |
| TORCH-REFINE-002D                  | 2     | 2            | 0               | 0                | 1               |
| TORCH-REFINE-002E                  | 3     | 2            | 1               | 0                | 2               |
| TORCH-REFINE-003                   | 2     | 1            | 0               | 1                | 0               |
| **TOTAL**                          | **53**| **43**       | **7**           | **3**            | **16**          |

### Policy Violations Summary

**Growth Cap Violations (>400 LOC):** 16 scripts
**Shadow Pipelines:** 7 scripts (require owner API migration in Phase B)
**Immediate Action Required:** 7 shadow pipelines + 16 growth-cap violations = 23 scripts violating diagnostic_script_policy

---

## Detailed Classification Table

| Script Path | Initiative | LOC | Torch? | Owner API? | Classification | Owner Module | Next Logging Hook | Exceeds Cap? | Notes |
|-------------|------------|-----|--------|------------|----------------|--------------|-------------------|--------------|-------|
| `plans/active/ARCH-PROBE-FREEZE-001/bin/collect_probe_inventory.py` | ARCH-PROBE-FREEZE-001 | 63 | No | No | thin_wrapper | pathlib/json (stdlib) | N/A (meta-tool) | No | This catalog script; complies with policy |
| `plans/active/ARCH-REFACTOR-001/bin/debug_bragg_reconstruction.py` | ARCH-REFACTOR-001 | 139 | Yes | Yes | thin_wrapper | dbex.refinement.reconstruction | dbex.io.writer torch_diagnostics | No | Calls RefinementEngine + build_final_bragg_from_stage_a_telemetry |
| `plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py` | ARCH-REFINE-001 | 271 | Yes | Yes | thin_wrapper | dbex.refinement.stage_a, dbex.refinement.stage_c | dbex.io.writer stage telemetry | No | Calls StageA/StageC via RefinementEngine; captures telemetry |
| `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py` | ARCH-REFINE-FLOW-001 | 148 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer zero-iteration diagnostics | No | Smoke fixture reproducer; calls owner simulation |
| `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py` | ARCH-REFINE-FLOW-001 | 187 | Yes | Yes | thin_wrapper | dbex.refinement.engine::RefinementEngine | dbex.io.writer torch_diagnostics | No | Minimal refinement smoke test; calls owner engine |
| `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py` | ARCH-SIM-CONSTRUCTION-001 | 328 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge, dbex.refinement.reconstruction | dbex.io.writer baseline comparison telemetry | No | Compares owner APIs (simulate_forward_once vs reconstruction) |
| `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py` | ARCH-SIM-CONSTRUCTION-001 | 665 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer simulator parity metrics | **Yes** | Compares 3 simulation paths; exceeds cap but uses owner APIs only |
| `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` | ARCH-SIM-CONSTRUCTION-001 | 2220 | Yes | Yes | shadow_pipeline | dbex.refinement.stage_a::StageA | dbex.io.writer Stage A baseline telemetry (chi²/loss traces) | **Yes** | Re-implements Stage A smoke semantics + reconstruction chain; MAJOR violation |
| `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py` | ARCH-SIM-CONSTRUCTION-001 | 150 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer zero-output diagnostics | No | Diagnostic probe; calls owner simulation |
| `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py` | ARCH-SIM-CONSTRUCTION-001 | 304 | Yes | Yes | thin_wrapper | dbex.refinement.stage_a::StageA | dbex.io.writer scale-factor provenance | No | Probes Stage A scale alignment; calls owner APIs |
| `plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py` | ARCH-SIM-HKL-BOUNDS-001 | 333 | Yes | Yes | shadow_pipeline | nanobrag_torch.models.crystal, nanobrag_torch.models.detector | nanobrag_torch physics helper (HKL projection math) | No | Re-implements scattering-vector→HKL projection inline; should delegate to owner |
| `plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/probe_crystal_hkl_alignment.py` | ARCH-SIM-HKL-BOUNDS-001 | 279 | Yes | Yes | thin_wrapper | nanobrag_torch.Simulator | nanobrag_torch simulator telemetry | No | Probes HKL alignment via owner Simulator |
| `plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py` | DB-AT-024 | 124 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer zero-iteration metrics | No | Acceptance test helper; calls owner simulation |
| `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py` | DIAG-NANOBRAGG-OVERSAMPLE-001 | 302 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::build_structure_factor_grid | dbex.io.writer HKL coverage stats | No | Compares HKL grid coverage; calls owner API |
| `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/diagnose_zero_output.py` | DIAG-NANOBRAGG-OVERSAMPLE-001 | 140 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer zero-output diagnostics | No | Duplicate of ARCH-SIM-CONSTRUCTION diagnose_zero_output; candidate for dedup |
| `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py` | DIAG-NANOBRAGG-OVERSAMPLE-001 | 303 | Yes | Yes | thin_wrapper | nanobrag_torch.Simulator | nanobrag_torch simulator telemetry | No | Traces simulator mismatch; calls owner Simulator |
| `plans/active/MAP-SCALE-001/bin/compare_simulator_to_golden.py` | MAP-SCALE-001 | 195 | No | Yes | thin_wrapper | dbex.data_load::DataLoad | dbex.io.writer golden comparison | No | Compares vs golden fixtures; calls DataLoad |
| `plans/active/MAP-SCALE-001/bin/compute_mapping_scale_probe.py` | MAP-SCALE-001 | 121 | No | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer mapping scale metrics | No | Computes per-ROI target/Bragg ratios via owner simulation |
| `plans/active/MAP-SCALE-001/bin/evaluate_mapping_strategy.py` | MAP-SCALE-001 | 131 | No | Yes | thin_wrapper | dbex.data_load::DataLoad | dbex.io.writer mapping strategy eval | No | Evaluates mapping strategy; calls DataLoad |
| `plans/active/NANOBRAG-GOLDEN-001/bin/summarize_roi_offsets.py` | NANOBRAG-GOLDEN-001 | 48 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (simple summarizer) | No | Lightweight JSON offset summarizer |
| `plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py` | PERF-WARM-SIM-001 | 276 | Yes | Yes | thin_wrapper | dbex.refinement.stage_a::StageA | dbex.io.writer perf telemetry (warm-cache timings) | No | Benchmarks Stage A cache; calls owner engine |
| `plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py` | PERF-WARM-SIM-001 | 131 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (panel diagnostic parser) | No | Simple panel diagnostic parser; stdlib only |
| `plans/active/PERF-WARM-SIM-001/bin/probe_stage_b_full.py` | PERF-WARM-SIM-001 | 135 | Yes | Yes | thin_wrapper | dbex.refinement.stage_b::StageB | dbex.io.writer Stage B telemetry | No | Probes Stage B; calls owner engine |
| `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py` | PERF-WARM-SIM-001 | 164 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (Stage B telemetry parser) | No | Stage B telemetry summarizer; stdlib only |
| `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py` | PERF-WARM-SIM-001 | 136 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (Stage C telemetry parser) | No | Stage C telemetry summarizer; stdlib only |
| `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py` | PERF-WARM-SIM-001 | 250 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (cache perf parser) | No | Parses Stage C cache telemetry; stdlib only |
| `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` | PHYSICS-LOSS-001 | 255 | No | Yes | shadow_pipeline | dbex.data_load::load_sigma_readout_map, dxtbx.model.ExperimentList | dbex.calibration sigma injection helper | No | Clones ExperimentList and injects sigma tiles; should move to dbex.calibration owner |
| `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py` | PORTFOLIO-STATUS | 331 | No | No | thin_wrapper | pathlib/json (stdlib) | N/A (meta-tool) | No | Portfolio inventory tool; stdlib only |
| `plans/active/REPORT-NANOBRAG-STATUS-001/bin/emit_nanobrag_summary.py` | REPORT-NANOBRAG-STATUS-001 | 179 | No | Yes | thin_wrapper | dbex.data_load::DataLoad | N/A (reporting tool) | No | Status report generator; calls DataLoad |
| `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py` | TOOLING-VIS-001 | 339 | No | Yes | shadow_pipeline | simtbx.diffBragg.hopper_utils, dbex.data_load | dbex.calibration.hopper_bridge | No | Re-implements DiffBragg hopper calibration capture; should move to owner module |
| `plans/active/TOOLING-VIS-001/bin/check_mapping_fixture_calibration.py` | TOOLING-VIS-001 | 103 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (fixture validator) | No | Validates mapping fixture calibration; stdlib only |
| `plans/active/TOOLING-VIS-001/bin/compare_geometry_zero_points.py` | TOOLING-VIS-001 | 275 | No | No | thin_wrapper | JSON/pathlib (stdlib) | N/A (geometry comparator) | No | Compares geometry zero points; stdlib only |
| `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` | TOOLING-VIS-001 | 671 | Yes | Yes | shadow_pipeline | dbex.vis.mapping::build_mapping_stage_a_context | dbex.calibration.config_variants (config materialization owner) | **Yes** | Re-implements config materialization logic; should delegate to calibration owner |
| `plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py` | TOOLING-VIS-001 | 369 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once | dbex.io.writer CPU/GPU parity metrics | No | Compares CPU vs GPU forward paths; calls owner simulation |
| `plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py` | TOOLING-VIS-001 | 334 | Yes | Yes | thin_wrapper | dbex.refinement.stage_a, dbex.vis.mapping | dbex.io.writer Stage A/mapping parity | No | Compares Stage A vs mapping; calls owner APIs |
| `plans/active/TOOLING-VIS-001/bin/crop_sigma_map_to_window.py` | TOOLING-VIS-001 | 202 | No | No | thin_wrapper | PIL/pathlib (stdlib+imaging) | N/A (sigma map cropper) | No | Crops sigma maps; imaging helper |
| `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs.py` | TOOLING-VIS-001 | 116 | No | Yes | thin_wrapper | dbex.vis.plot_triptych | dbex.vis.plot_triptych | No | Generates ROI triptychs via owner vis helper |
| `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py` | TOOLING-VIS-001 | 585 | Yes | Yes | shadow_pipeline | dbex.nanobrag_refinement::run_nanobrag_refinement | dbex.refinement.engine Stage A ADAM backend | **Yes** | Re-implements ADAM refinement path inline; should delegate to engine variant |
| `plans/active/TOOLING-VIS-001/bin/generate_zero_iter_refined_roi_triptychs.py` | TOOLING-VIS-001 | 125 | Yes | Yes | thin_wrapper | dbex.vis.plot_triptych | dbex.vis.plot_triptych | No | Generates zero-iteration triptychs via owner vis helper |
| `plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py` | TOOLING-VIS-001 | 394 | Yes | Yes | thin_wrapper | dbex.vis.mapping::build_mapping_stage_a_context, dbex.vis.plot_triptych | dbex.vis.plot_triptych | No | Probes mapping ROI triptychs; calls owner vis helpers |
| `plans/active/TOOLING-VIS-001/bin/probe_mapping_stage_a_context_metrics.py` | TOOLING-VIS-001 | 139 | No | Yes | thin_wrapper | dbex.vis.mapping::build_mapping_stage_a_context | dbex.io.writer context metrics | No | Probes mapping context metrics; calls owner context builder |
| `plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py` | TOOLING-VIS-001 | 375 | Yes | Yes | thin_wrapper | dbex.refinement.stage_a, dbex.nanobrag_bridge | dbex.io.writer scale-chain provenance | No | Probes scale-factor chain; calls owner APIs |
| `plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py` | TOOLING-VIS-001 | 101 | No | Yes | thin_wrapper | dbex.refinement.engine::RefinementEngine | dbex.io.writer zero-point telemetry | No | Runs Stage A zero-point probe; calls owner engine |
| `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` | TOOLING-VIS-001 | 287 | No | Yes | thin_wrapper | dbex.vis.mapping::build_mapping_stage_a_context | dbex.refinement.engine ADAM backend | No | ADAM debug helper; calls owner mapping context builder |
| `plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py` | TORCH-GEOMETRY-PARITY-003 | 70 | No | No | thin_wrapper | dxtbx/cctbx (external) | N/A (parity audit) | No | Audits dxtbx A* cell parity; external API wrapper |
| `plans/active/TORCH-REFINE-001/bin/dump_refine_telemetry.py` | TORCH-REFINE-001 | 45 | No | Yes | thin_wrapper | dbex.io.reader (HDF5) | N/A (telemetry dumper) | No | Dumps refinement telemetry from HDF5; reader wrapper |
| `plans/active/TORCH-REFINE-002D/bin/probe_hkl_hit_rate.py` | TORCH-REFINE-002D | 279 | No | Yes | thin_wrapper | dbex.data_load::DataLoad, cctbx matrices | dbex.io.writer HKL hit-rate metrics | No | Computes HKL hit-rate via owner DataLoad + cctbx |
| `plans/active/TORCH-REFINE-002D/bin/probe_stage_a_improvement.py` | TORCH-REFINE-002D | 222 | Yes | Yes | thin_wrapper | dbex.refinement.stage_a::StageA | dbex.io.writer Stage A improvement metrics | No | Probes Stage A improvement; calls owner engine |
| `plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py` | TORCH-REFINE-002E | 326 | Yes | Yes | thin_wrapper | dbex.nanobrag_bridge::simulate_forward_once, dbex.refinement.stage_a | dbex.io.writer mapping/Stage A parity | No | Compares mapping vs Stage A forward; calls owner APIs |
| `plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward_simple.py` | TORCH-REFINE-002E | 112 | No | Yes | thin_wrapper | dbex.data_load::DataLoad | dbex.io.writer simplified parity metrics | No | Simplified mapping/Stage A comparison; calls DataLoad |
| `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py` | TORCH-REFINE-002E | 545 | Yes | Yes | shadow_pipeline | nanobrag_torch.models.crystal::Crystal | nanobrag_torch.models.crystal.compute_cell_tensors() | **Yes** | Re-implements reciprocal matrix + eigenvalue/SVD analysis; should delegate to owner |
| `plans/active/TORCH-REFINE-003/bin/dump_stage_c_metrics.py` | TORCH-REFINE-003 | 132 | No | No | retire_candidate | N/A (likely superseded) | dbex.io.writer Stage C telemetry | No | Non-torch, no owner API calls; likely superseded by engine telemetry |
| `plans/active/TORCH-REFINE-003/bin/probe_stage_c_improvement.py` | TORCH-REFINE-003 | 153 | Yes | Yes | thin_wrapper | dbex.refinement.stage_c::StageC | dbex.io.writer Stage C improvement metrics | No | Probes Stage C improvement; calls owner engine |

---

## Phase B Migration Priorities (Shadow Pipelines)

The following 7 shadow pipeline scripts require owner API migration in Phase B:

1. **`compare_stage_a_baseline.py`** (2220 LOC) — **CRITICAL VIOLATION**
   - **Owner:** `dbex.refinement.stage_a::StageA`, `dbex.io.writer`
   - **Telemetry Hook:** Stage A baseline chi²/loss traces, reconstruction chain metrics
   - **Action:** Migrate smoke semantics + reconstruction chain telemetry into `dbex.io.writer` torch_diagnostics

2. **`compare_mapping_dataset_metrics.py`** (671 LOC)
   - **Owner:** `dbex.calibration.config_variants`
   - **Telemetry Hook:** Config materialization logic
   - **Action:** Extract `materialize_calibration_variant` into canonical owner module

3. **`generate_stage_a_refgeom_roi_triptychs_adam.py`** (585 LOC)
   - **Owner:** `dbex.refinement.engine` (ADAM backend variant)
   - **Telemetry Hook:** ADAM refinement path telemetry
   - **Action:** Add ADAM optimizer backend to `RefinementEngine.run_stage_a`

4. **`probe_crystal_matrix_parity.py`** (545 LOC)
   - **Owner:** `nanobrag_torch.models.crystal::compute_cell_tensors`
   - **Telemetry Hook:** Reciprocal matrix + eigenvalue/SVD diagnostics
   - **Action:** Add `compute_cell_tensors()` helper to `nanobrag_torch.models.crystal.Crystal`

5. **`inspect_hkl_projection.py`** (333 LOC)
   - **Owner:** `nanobrag_torch` physics helper module
   - **Telemetry Hook:** Scattering-vector→HKL projection math
   - **Action:** Extract `compute_physics_for_position` into `nanobrag_torch.physics.projection`

6. **`capture_smoke_calibration.py`** (339 LOC)
   - **Owner:** `dbex.calibration.hopper_bridge`
   - **Telemetry Hook:** DiffBragg hopper calibration extraction
   - **Action:** Migrate hopper_utils payload capture into canonical calibration module

7. **`embed_sigma_external_lookup.py`** (255 LOC)
   - **Owner:** `dbex.calibration.sigma_injection`
   - **Telemetry Hook:** Sigma tile injection into ExperimentList
   - **Action:** Move ExperimentList cloning + sigma injection into owner helper

---

## Phase B Growth Cap Violations (16 Scripts Exceeding 400 LOC)

Scripts exceeding ~400 LOC growth cap require either:
- (a) Promotion to `scripts/tools/` with harness tests, OR
- (b) Freezing (no further extension; instrument production paths instead)

| Script | LOC | Initiative | Recommendation |
|--------|-----|------------|----------------|
| `compare_stage_a_baseline.py` | 2220 | ARCH-SIM-CONSTRUCTION-001 | **FREEZE + MIGRATE** (shadow pipeline) |
| `compare_mapping_dataset_metrics.py` | 671 | TOOLING-VIS-001 | **FREEZE + MIGRATE** (shadow pipeline) |
| `compare_simulator_outputs.py` | 665 | ARCH-SIM-CONSTRUCTION-001 | **FREEZE** (thin wrapper; add simulator telemetry instead) |
| `generate_stage_a_refgeom_roi_triptychs_adam.py` | 585 | TOOLING-VIS-001 | **FREEZE + MIGRATE** (shadow pipeline; add ADAM backend) |
| `probe_crystal_matrix_parity.py` | 545 | TORCH-REFINE-002E | **FREEZE + MIGRATE** (shadow pipeline) |
| `probe_mapping_roi_triptychs.py` | 394 | TOOLING-VIS-001 | **FREEZE** (thin wrapper; add mapping telemetry) |
| `probe_scale_chain.py` | 375 | TOOLING-VIS-001 | **FREEZE** (thin wrapper; add scale-chain telemetry) |
| `compare_mapping_forward_cpu_gpu.py` | 369 | TOOLING-VIS-001 | **FREEZE** (thin wrapper; add CPU/GPU parity telemetry) |
| `capture_smoke_calibration.py` | 339 | TOOLING-VIS-001 | **FREEZE + MIGRATE** (shadow pipeline) |
| `compare_stage_a_mapping_parity.py` | 334 | TOOLING-VIS-001 | **FREEZE** (thin wrapper; add Stage A/mapping parity telemetry) |
| `inspect_hkl_projection.py` | 333 | ARCH-SIM-HKL-BOUNDS-001 | **FREEZE + MIGRATE** (shadow pipeline) |
| `plan_inventory.py` | 331 | PORTFOLIO-STATUS | **ALLOWED** (meta-tool, stdlib only) |
| `compare_simulate_forward_once_vs_reconstruction.py` | 328 | ARCH-SIM-CONSTRUCTION-001 | **FREEZE** (thin wrapper; add reconstruction telemetry) |
| `compare_mapping_vs_stage_a_forward.py` | 326 | TORCH-REFINE-002E | **FREEZE** (thin wrapper; add parity telemetry) |
| `probe_hkl_hit_rate.py` | 279 | TORCH-REFINE-002D | **FREEZE** (thin wrapper; add HKL hit-rate telemetry) |
| `embed_sigma_external_lookup.py` | 255 | PHYSICS-LOSS-001 | **FREEZE + MIGRATE** (shadow pipeline) |

---

## Next Steps (Phase A→B Transition)

1. **Phase A Completion:**
   - [x] A1: Walk `plans/active/**/bin/*.py` and classify
   - [x] A2: Produce `probe_inventory.md` + summary counts + growth-cap highlights
   - [ ] A3: Cross-reference `docs/fix_plan.md` + `galph_memory.md` for obsolete probes (defer to next loop)

2. **Phase B Planning:**
   - For each of 7 shadow pipelines: plan production logging hook (e.g., Stage A telemetry block, simulator hook)
   - Patch production modules (Stage A, reconstruction helpers, simulator, mapping) with telemetry toggles
   - Delete or slim scripts once telemetry covers measurements

3. **Phase C Enforcement:**
   - Author `tests/architecture/test_probe_contracts.py::test_plan_scripts_only_wrap_owner_apis`
   - Scan plan-local bins for forbidden modules/patterns (torch imports, ROI math, etc.)
   - Fail when violations appear

---

## Artifacts

- **Raw JSON:** `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory_raw.json` (53 scripts)
- **Classification JSON:** `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory.json` (machine-readable)
- **This Document:** `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory.md`

---

**Prepared by:** Ralph (ARCH-PROBE-FREEZE-001 Phase A)
**Supervisor Directive:** prompts/supervisor.md:272-287 (diagnostic_script_policy)
**Next Loop:** Phase B migration planning for 7 shadow pipelines
