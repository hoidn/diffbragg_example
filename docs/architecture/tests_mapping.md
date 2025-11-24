# Tests, Probes, and Selectors — Coverage Map
Scope: descriptive of current implementation; normative behavior lives in docs/spec-db*.md.

Purpose: map selectors/probes to the code they exercise and the artifacts they produce for the current implementation.

## Quick Table
| Selector / Probe | Purpose | Modules Exercised | Artifacts |
| --- | --- | --- | --- |
| DB-AT-024 (mapping parity) | Torch mapping parity (Stage A zero-point) | `refine_one.py`, `nanobrag_bridge.py`, `nanobrag_refinement.py`, `refinement/helpers.py` | Test logs, HDF5 outputs |
| DB-AT-026 (UB round-trip) | A* parity at zero params | `nanobrag_refinement.py` (incremental UB), `geometry/crystallography.py` | Test logs |
| DB-AT-027/028/029 (Stage A mapping parity) | Mapping vs Stage A parity and diagnostics | `nanobrag_refinement.py`, `tools/stage_a_adam.py`, `vis/mapping.py` | Probe JSON, logs, PNGs |
| Forward equivalence (tests/dbex/test_forward_equivalence*.py) | Forward sim parity (DiffBragg vs nanobrag_torch) | `refine_one.py`, `nanobrag_bridge.py`, `refinement/helpers.py`, nanobrag_torch Simulator | Logs, optional traces |
| Smoke: `test_torch_refine_smoke.py` | Stage A/B/C smoke on fixtures | `refine_one.py`, `nanobrag_refinement.py`, `refinement/engine.py` | Test logs, HDF5 |
| Smoke: `test_nanobrag_smoke.py` | Basic torch sim path sanity | `nanobrag_bridge.py`, `refinement/helpers.py` | Test logs |
| CLI: `test_refine_one_cli.py` | CLI parsing and end-to-end HDF5 write | `refine_one.py`, `data_load.py`, torch/diffbragg paths | HDF5 outputs |
| Geometry: `test_geometry_current.py`, `test_mapping_consistency.py`, `test_ub_parameterization_roundtrip.py` | Geometry helpers and mapping parity | `geometry/crystallography.py`, `nanobrag_bridge.py`, `nanobrag_refinement.py` | Logs |
| Loss/physics: `test_physics_loss_current.py` | Variance-weighted loss and clamp | `physics/loss.py` | Logs |
| Bridge: `test_nanobrag_bridge*.py`, `test_mask_semantics.py`, `test_background_semantics.py` | Input prep, masks, sentinels | `nanobrag_bridge.py`, `data_load.py` | Logs |
| Engine: `test_refinement_engine.py` | Protocol engine sequencing | `refinement/engine.py`, stage wrappers | Logs |
| Stage B per-reflection: `test_stage_b_asu_mapping.py` | Per-reflection modifiers | `nanobrag_refinement.py` Stage B | Logs |
| Tooling probes: `test_stage_a_adam_tooling.py` | Stage A probe utilities | `tools/stage_a_adam.py`, `vis/stage_a.py` | Logs, probe outputs |
| Vis: `test_vis_triptych*.py` | Triptych rendering | `vis/triptych.py` | PNGs in tmp |

## Gaps / Blockers
- Warm-cache perf selectors (PERF-WARM-SIM-001) blocked by ENV-CUDA-001.
- Engine Phase C consolidation tests pending (ARCH-REFACTOR-001 Phase C deferred).

## How to Rerun
- Use `pytest` selectors noted above; see `docs/TESTING_GUIDE.md` for canonical env flags (e.g., `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, small-detector fixtures).*** End Patch
