Summary: Apply mapping calibration (spot_scale_override + flux/exposure/N_cells) to the Stage A engine path so DB-AT-027 zero-point parity passes and the xfail can be removed.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/

Do Now
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_context, dbex/nanobrag_refinement.py::_build_stage_a_lbfgs_closure, dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_a_telemetry, dbex/nanobrag_refinement.py::run_nanobrag_refinement (Stage A final Bragg rebuild), dbex/tools/stage_a_adam.py::run_engine_zero_point_probe, tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity — plumb `spot_scale_override` (and related calibration metadata) through Stage A warm cache and reconstruction, apply the sqrt baseline once in closures + telemetry rebuild, and remove the xfail after DB-AT-027 tolerances pass.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/pytest_db_at_027.log; then AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/pytest_db_at_027_collect.log.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/{stage_a_engine_probe/stage_a_engine_zero_point.json,stage_a_engine_probe/cli_stage_a_engine_zero_point.log,db_at_027/db_at_027_metrics.json,db_at_027/db_at_027_env.json,pytest_db_at_027.log,pytest_db_at_027_collect.log,summary.md}

How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/{stage_a_engine_probe,db_at_027}` before running helpers/tests.
2. Thread spot-scale: plumb `calibration_metadata.spot_scale_override` into Stage A warm cache and Bragg reconstruction (compute/log `log_scale_baseline = log(sqrt(spot_scale_override))`, clamp deltas to ±log_scale_max_delta, scale panel outputs once per panel). Keep flux/exposure/beamsize_mm/N_cells overrides intact and propagate into telemetry.
3. Align Stage A reconstruction paths: ensure `_build_final_bragg_from_stage_a_telemetry` and the inline Stage A Bragg rebuild in `run_nanobrag_refinement` share the same calibrated beam/crystal configs and log-scale baseline math; avoid `create_unified_simulator` inside refinement (ARCH-FACTORY-001).
4. Update probe harness: adjust `run_engine_zero_point_probe` to log spot-scale baseline in its payload and reuse the calibrated scale when reconstructing `bragg_stagea_zero`; keep DB-AT-027 assertions strict.
5. Capture zero-point metrics: `python plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/stage_a_engine_probe | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/stage_a_engine_probe/cli_stage_a_engine_zero_point.log`.
6. Run pytest gate + collect-only with the env from step 1; if tolerances pass, remove the xfail in `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` and rerun to confirm XPASS.
7. Doc sync after pass: mark DB-AT-027 Active in `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md`, and note the calibration resolution in `docs/findings.md` (STAGEA-001).

Pitfalls To Avoid
- Do not use `create_unified_simulator` inside Stage A closures (breaks autograd; see ARCH-FACTORY-001).
- Apply spot_scale baseline exactly once (sqrt), then clamp log-scale deltas; avoid double-scaling or bypassing baseline when calibration is absent.
- Preserve MappingStageAContext geometry/HKL invariants (GEOMETRY-003/004) and sigma semantics (PHYSICS-LOSS-001).
- Keep warm-cache + ROI paths consistent with cold paths; every branch must see the calibrated beam/crystal configs.
- Honor Environment Freeze (POLICY-001); no dependency installs or CLI flag relaxations.

If Blocked
- Save probe JSON/logs and pytest output to the artifacts dir, record the measured mean/max diff + chi² delta in docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked until the spot-scale application bug is understood.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A engine must reuse mapping calibration (spot_scale_override); unxfail only after DB-AT-027 passes.
- GEOMETRY-003/004 — Maintain mapping zero-point geometry/UB invariants when rebuilding Stage A Bragg.
- PHYSICS-LOSS-001 — Use the canonical variance-weighted chi² helper and sigma_floor semantics.
- ARCH-FACTORY-001 — Unified simulator factory is forward-only; refinement closures must instantiate simulators directly.
- POLICY-001 — Environment frozen; code-only edits inside the workspace.

Pointers
- docs/spec-db-conformance.md:201 — DB-AT-027 tolerances and calibration requirements.
- docs/spec-db-core.md:84 — Variance-weighted loss formula and sigma_floor guard.
- dbex/vis/mapping.py:34 — MappingStageAContext calibration payload shape.
- dbex/nanobrag_refinement.py:696 — Stage A context builder where calibration threads in.
- docs/TESTING_GUIDE.md:136 — DB-AT-027 registry row (update to Active after XPASS).

Next Up (optional)
- Phase D.D: DB-AT-028/029 loss-scale and ROI structure once DB-AT-027 is green.

Doc Sync Plan (Conditional)
- After unxfailing, update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md`, archiving execution + collect-only logs under the artifacts path.

Mapped Tests Guardrail
- `pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027` must collect 1 test; treat 0 collection as a blocker.

Hard Gate
- Do not finish until the calibrated engine probe and pytest selector meet DB-AT-027 tolerances with artifacts under `plans/active/TOOLING-VIS-001/reports/2025-11-24T234121Z/db_at_027`.

Normative Math/Physics
- Reference `docs/spec-db-conformance.md:201-239` and `docs/spec-db-core.md:84-90` for the exact equations; do not paraphrase or alter them.
