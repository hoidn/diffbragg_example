Summary: Plumb the mapping calibration payload into Stage A engine paths so DB-AT-027 zero-point parity passes without xfail.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/

Do Now
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_context, dbex/nanobrag_refinement.py::_build_stage_a_lbfgs_closure, dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_a_telemetry, dbex/refine_one.py::main, dbex/tools/stage_a_adam.py::run_engine_zero_point_probe, tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity — thread calibration metadata (spot_scale_override, beam_flux, beam_exposure, beamsize_mm, N_cells) into Stage A configs/telemetry, treat log_scale as a calibrated ±3 delta, rebuild zero-point Bragg with calibrated configs, and unxfail DB-AT-027 once tolerances pass.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/pytest_db_at_027.log
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/{stage_a_engine_probe/stage_a_engine_zero_point.json,stage_a_engine_probe/cli_stage_a_engine_zero_point.log,db_at_027/db_at_027_metrics.json,db_at_027/db_at_027_env.json,pytest_db_at_027.log,pytest_db_at_027_collect.log,summary.md}

How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/{stage_a_engine_probe,db_at_027}` before running helpers/tests.
2. Implement calibration plumbing: extend `RefinementConfig` + Stage A context/closure builders to accept calibration metadata, pre-scale simulators with `sqrt(spot_scale_override)`, build BeamConfig/CrystalConfig with flux/exposure/beamsize_mm/N_cells when present, and clamp `log_scale` to ±3 deltas around the calibrated baseline while persisting the baseline in telemetry and `_build_final_bragg_from_stage_a_telemetry`.
3. Thread calibration from CLI/probes: pass calibration payload from `dbex/refine_one.py::main` and `MappingStageAContext.calibration` into `RefinementConfig`; update `run_engine_zero_point_probe` to forward calibration and reuse the calibrated beam/crystal configs when reconstructing zero-point Bragg.
4. Capture zero-point metrics: `python plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/stage_a_engine_probe | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/stage_a_engine_probe/cli_stage_a_engine_zero_point.log` (expects mean_abs_diff ≤1e-3, max_abs_diff ≤2e2, |chi2_rel_diff| ≤1e-3 once fixed).
5. Run pytest gate + collect-only: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/pytest_db_at_027.log` then `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/pytest_db_at_027_collect.log`.
6. Promote DB-AT-027 in docs once passing: remove the xfail marker, update `docs/TESTING_GUIDE.md` §2 status to Active with calibrated env/artifact notes, add a row to `docs/development/TEST_SUITE_INDEX.md`, and append a resolution note to `docs/findings.md` (STAGEA-001) with the artifact path and calibration fix summary.

Pitfalls To Avoid
- Do not relax DB-AT-027 tolerances; adhere to `docs/spec-db-conformance.md:201-239`.
- Keep calibration threaded through all Stage A branches (warm cache, cold, engine delegation); missing a branch will reintroduce drift.
- Only clamp `log_scale` when calibration metadata exists; uncalibrated flows keep the legacy ±10 band.
- Preserve tensor shapes/dtypes and MappingStageAContext invariants (GEOMETRY-003/004); avoid reinitializing HKL grids differently from mapping.
- Ensure `_build_final_bragg_from_stage_a_telemetry` rebuilds Bragg using the calibrated beam/crystal configs; mismatched configs invalidate parity.
- Require `DBAT027_ARTIFACT_DIR` for CLI/test runs so metrics/env JSON always land.
- Honor Environment Freeze (POLICY-001); no package installs or toolchain tweaks.
- Treat failing probes/tests as blocking; capture JSON + logs rather than weakening gates.

If Blocked
- Capture failing probe JSON/logs plus pytest output in the artifacts directory, record the error signature and measured deltas in docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked until root cause is diagnosed.

Findings Applied (Mandatory)
- STAGEA-001 — Mapping calibration payload must be reused in Stage A engine; remove xfail only after metrics meet DB-AT-027.
- PHYSICS-LOSS-001 — Use the canonical variance-weighted χ² helper for mapping vs Stage A comparisons.
- GEOMETRY-003/004 — Keep mapping zero-point geometry/UB invariant when applying calibration.
- CONFORMANCE-001 — Maintain canonical env flags + artifact capture for DB-AT selectors.
- POLICY-001 — Environment remains frozen; source-only changes inside workspace.

Pointers
- docs/spec-db-conformance.md:201 — DB-AT-027 calibration + tolerance details.
- docs/spec-db-core.md:86 — Variance-weighted loss definition used for χ² comparisons.
- dbex/vis/mapping.py:34 — MappingStageAContext calibration structure to forward into Stage A.
- dbex/nanobrag_refinement.py:696 — Stage A context builder entry point for calibration threading.
- docs/TESTING_GUIDE.md:136 — Current DB-AT-027 registry row (xfail → Active once passing).

Next Up (optional)
- Phase D.D: DB-AT-028/029 loss-scale and ROI structure once zero-point parity is green.

Doc Sync Plan (Conditional)
- After DB-AT-027 passes, update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with the Active selector entry and archive both execution + collect-only logs under the artifacts path.

Mapped Tests Guardrail
- `pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027` must collect 1 test; treat 0 collection as a blocker.

Hard Gate
- Do not finish until the calibrated engine probe and pytest selector both satisfy DB-AT-027 tolerances with artifacts written under `plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/db_at_027`.

Normative Math/Physics
- Reference `docs/spec-db-conformance.md:201-239` for zero-point equations and `docs/spec-db-core.md:86-90` for the variance-weighted χ²; avoid paraphrasing or altering the formulas.
