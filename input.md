Summary: Align `build_final_bragg_from_stage_a_telemetry`’s cold path with Stage A telemetry so DB-AT-028/029 see the same masked-intensity baseline even when `StageAArtifacts` are unavailable.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/

Do Now:
- Implement: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` — when `stage_a_ctx.bragg_zero_iter` is missing for `param_state="initial"`, compute the cold-path masked mean on `inputs.loss_mask`, compare it with `telemetry_a.model_mean_masked`, multiply the tensor by the ratio when both are finite/positive, and record the applied `baseline_alignment_factor` plus cache-hit vs cold-path status in diagnostics so SCALE-008/SCALE-009 remain auditable.
- Implement: `tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline` — drop the Stage A artifact cache before calling the helper and assert that the cold-path reconstruction matches telemetry masked means (and, when available, cached Stage A arrays) within ≤1e-6 relative error.
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main` — extend the report with `baseline_alignment_factor` + cache status so probes immediately show when the telemetry correction fired; include the new metadata in both console output and the JSON summaries consumed by DB-AT evidence.
- Validate: run the mapped probe command plus `pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline` and the DB-AT-028/029 selector with the artifact directories set above, capturing logs under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/`.

How-To Map:
1. After the cold-path simulators fill `bragg_full`, reuse the canonical loss mask (per docs/spec-db-core.md §Data Contracts) to compute the masked mean before any corrections.
2. Read `telemetry_a.model_mean_masked`; if absent, fall back to the mapping diagnostics (`diagnostics["masked_mean_ratio"]` + `StageAContext.baseline_stats`) so the ratio still reflects Stage A’s authoritative baseline.
3. Multiply the tensor by `telemetry / cold` (clamped to sensible bounds) and persist `baseline_alignment_factor`, `cache_status`, and the before/after means in diagnostics to keep parity evidence self-contained.
4. The new artifact-parity test can reuse the Stage A smoke fixture to build artifacts once, drop `StageAArtifacts`, and invoke the helper twice (initial + final) to prove both cache and cold paths align with telemetry.
5. Run the probe in baseline geometry mode first so DB-AT-027 tolerances (docs/spec-db-conformance.md §DB-AT-027) apply, then follow with the perturbed mode if time allows.

Pitfalls To Avoid:
- Do not apply the correction when telemetry or cold-path masked means are zero/NaN; emit a diagnostics warning and return the cold tensor unchanged so we do not introduce NaNs into DB-AT artifacts.
- Keep the correction scalar (single ratio) and avoid recomputing expensive simulators on CPU—this path must remain deterministic for harness tooling.
- Make sure DB-AT selectors log whether they hit the cache or the telemetry correction; silent behavior changes make future regressions impossible to triage.
- Respect the Environment Freeze: no edits to nanobrag_torch or other toolchains; all work is within dbex + plan scripts.
- Ensure the new pytest node is deterministic (fix RNG seeds) so it can run under `-k test_stage_a_cold_path_respects_telemetry_baseline` without flakiness.

If Blocked:
- If telemetry lacks masked-mean data (legacy artifacts), capture the cold-path vs Stage A mismatch via `baseline_stats.json`, note the gap in `docs/fix_plan.md`, and mark the initiative blocked pending telemetry instrumentation rather than guessing.
- If CUDA resources are unavailable, run the probe/tests on CPU and annotate the artifact filenames plus summary.md with the device so future runs know why runtimes changed.

Findings Applied (Mandatory):
- SCALE-008 — Stage A warm-cache authority must be honored; telemetry-provided baselines override any recomputation when cache hits are unavailable.
- SCALE-009 — Reconstruction helpers are required to mirror Stage A scaling semantics; documenting the correction factor and cache-hit state proves we are following the architecture contract.

Pointers:
- dbex/refinement/reconstruction.py:150-260 (cold-path helper where the new alignment logic belongs).
- tests/dbex/test_artifact_parity.py:321-520 (existing artifact parity suite to extend with the cold-path regression test).
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:380-560 (probe instrumentation to update with baseline-alignment metadata).
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/stage_a_baseline_probe_baseline.json (evidence of the 1.46× cold-path mismatch to eliminate).
