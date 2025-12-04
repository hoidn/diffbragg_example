---
summary: Align build_final_bragg_from_stage_a_telemetry’s cold path with the Stage A telemetry baseline so DB-AT-028/029 see the same masked-intensity scale even when StageAArtifacts are absent.
mode: Parity
initiative_type: architecture
focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
branch: integration
artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/
mapped_tests:
  - pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/pytest_db_at_028_029.log
do_now:
  - implement: dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry
    details: "When stage_a_ctx is missing for param_state='initial', compute the cold-path masked mean (`np.mean(bragg_full[inputs.loss_mask])`), compare it against `telemetry_a.model_mean_masked`, and multiply `bragg_full` by the correction factor so the reconstruction matches Stage A telemetry (log correction + debug print) instead of returning the 1.46× oversized stack captured on 2025-12-17. Preserve the warm-cache fast path so cache hits still short-circuit."
  - implement: tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline
    details: "Extend the artifact parity suite with a scenario that drops stage_a_ctx before calling the helper (both initial + final states) and asserts the masked mean (and optionally per-pixel values) match the cached Stage A artifacts within ≤1e-6 relative error. This will fail on main and prove the fix."
  - implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main
    details: "Log whether the cold path needed the telemetry correction (`baseline_alignment_factor`), include it in the JSON, and surface cache-hit vs cold-path status so future probes/reporting can spot regressions quickly."
  - validate: run the mapped tests above and capture artifacts under plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/.
how_to_map:
  - Warm cache absent path reproduced by removing `stage_a_ctx` before calling `build_final_bragg_from_stage_a_telemetry`; use the same `inputs.loss_mask` numpy mask that Stage A created to compute masked means.
  - Correction factor should be `telemetry_model_mean_masked / cold_path_model_mean_masked`; guard against divide-by-zero and skip when telemetry lacks the field.
  - Baseline probes should be run twice (`--geometry-mode baseline` and default perturbed) if time permits; at minimum capture the baseline run proving the correction engaged when `_artifacts["stage_a"]` is cleared in the probe.
pitfalls_to_avoid:
  - Do **NOT** multiply by `sqrt(spot_scale_override)` again; the correction must be a near-unity adjustment derived from masked means, not a reapplication of spot_scale.
  - Keep mask handling identical to Stage A (`inputs.loss_mask.astype(bool)`); mixing torch/numpy masks will skew pixel counts and defeat the correction.
  - Remember that Stage A telemetry stores floats; guard for `None`/`NaN` before computing ratios to avoid spraying `nan` through the final Bragg stack.
if_blocked:
  - If the correction oscillates or `telemetry.model_mean_masked` is unavailable, capture `baseline_stats.json` + console logs showing both masked means and fall back to the cache path, then flag the initiative as blocked in docs/fix_plan.md and galph_memory with the evidence so we can open a dedicated telemetry initiative.
findings_applied:
  - SCALE-008 — mapping-provided baseline overrides must be honored to keep warm cache authority intact (docs/findings.md line 41).
  - SCALE-009 — reconstruction helpers must mirror Stage A scaling semantics when rebuilds run cold (docs/findings.md line 42).
pointers:
  - docs/fix_plan.md:136 — ARCH-SIM-CONSTRUCTION-001 status + Attempts History.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md — Phase C.14 checklist for this task.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/stage_a_baseline_probe_baseline.json — Evidence of the 1.46× cold-path mismatch that this fix must eliminate.
---
