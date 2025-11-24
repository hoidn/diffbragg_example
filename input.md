Summary: Thread mapping calibration payload (spot_scale_override, flux/exposure, N_cells) through Stage A so DB-AT-027 passes without an xfail.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/

Do Now
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_context + _build_stage_a_lbfgs_closure + run_nanobrag_refinement (calibration plumbing + log-scale delta clamp), dbex/refine_one.py::main (pass calibration metadata into RefinementConfig), dbex/tools/stage_a_adam.py::run_engine_zero_point_probe (forward calibration into zero-point probe), docs/TESTING_GUIDE.md::§2 DB-AT table + docs/development/TEST_SUITE_INDEX.md::Implementation Coverage + docs/findings.md::STAGEA-001 — reuse the mapping calibration payload inside Stage A/engine delegation, treat `log_scale` as a ±3 delta around the calibrated baseline, rebuild final Bragg frames with the same beam/crystal configs, and refresh the test registry once DB-AT-027 no longer xfails.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/pytest_db_at_027.log
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/{stage_a_engine_probe/stage_a_engine_zero_point.json,stage_a_engine_probe/cli_stage_a_engine_zero_point.log,db_at_027/db_at_027_metrics.json,db_at_027/db_at_027_env.json,pytest_db_at_027.log,pytest_db_at_027_collect.log,summary.md}

How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and ensure `plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/{stage_a_engine_probe,db_at_027}` exist before running helpers/tests.
2. Update Stage A engine plumbing: extend `RefinementConfig` with calibration/log-scale fields, make `run_nanobrag_refinement` accept those fields (including engine delegation path), reuse calibration metadata inside `_build_stage_a_context`, `_build_stage_a_lbfgs_closure`, `_build_final_bragg_from_stage_a_telemetry`, and clamp `log_scale` to ±3 only when calibration is present while recording the baseline in telemetry.
3. Thread calibration payload from CLI + probes: pass `calibration_metadata` from `dbex/refine_one.py::main` into the new config fields; update `dbex/tools/stage_a_adam.py::run_engine_zero_point_probe` to forward `context.calibration` into `RefinementConfig`, and ensure Stage B CPU fallback contexts also reuse the calibrated beam/crystal configs.
4. Capture zero-point metrics with the calibrated engine: `python plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/stage_a_engine_probe | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/stage_a_engine_probe/cli_stage_a_engine_zero_point.log` (expect exit code 0 once tolerances are met); verify the emitted JSON includes mean/max |Δ|, chi² stats, and ROI CC samples.
5. Run the pytest gate with artifacts enabled: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/pytest_db_at_027.log` (should PASS, not xfail). Immediately follow with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/pytest_db_at_027_collect.log` to show the selector still collects 1 test.
6. Promote DB-AT-027 in the docs: remove the xfail marker in the test, update `docs/TESTING_GUIDE.md` §2 row to status `Active (Stage A zero-point parity enforced)` with the calibrated env/artifact description, add a matching entry to `docs/development/TEST_SUITE_INDEX.md`, and append a resolution note to `docs/findings.md` (STAGEA-001) referencing the new calibration plumbing + artifact path.
7. Update `plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/summary.md` with CLI + pytest outcomes, drop metrics JSON/env dumps into `db_at_027/`, and stage the logs for supervisor review.

Pitfalls To Avoid
- Do not loosen DB-AT-027 tolerances; the fix must honor `docs/spec-db-conformance.md:201-239` exactly.
- Calibration plumbing must cover both warm-cache and cold paths (panel + ROI contexts) plus Stage B CPU fallback; leaving a branch unpatched will reintroduce drift.
- Keep `log_scale` baseline neutral: only treat it as a delta when calibration metadata is present; legacy (uncalibrated) flows should retain the ±10 default.
- Preserve Environment Freeze (POLICY-001); no pip installs or CUDA tweaks to chase missing deps.
- Ensure `_build_final_bragg_from_stage_a_telemetry` rebuilds Bragg frames with the same calibrated beam/crystal configs as the closure; mismatched configs will skew zero-point regression.
- Don’t drop the artifact env guard: `DBAT027_ARTIFACT_DIR` must be required so CLI/pytest runs always emit JSON + env snapshots.
- When updating docs/test index, cite the new artifact path + env flags; vague references will fail CONFORMANCE-001 auditing.
- Keep Stage A parameter tensor shapes/dtypes unchanged; only wrap new calibration scalars so optimizer state checkpoints remain compatible.
- Treat Stage A probe/test failures as blocking; capture JSON + logs instead of re-running with weakened thresholds.

If Blocked
- If Stage A still violates DB-AT-027 tolerances after plumbing the calibration, capture the failing metrics JSON, CLI log, and pytest output in the artifacts directory, add the error signature + measured deltas to docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 `blocked` until the root cause is diagnosed.

Findings Applied (Mandatory)
- STAGEA-001 — Resolve the documented zero-point miscalibration by reusing the mapping calibration payload; remove the xfail only after metrics prove parity.
- PHYSICS-LOSS-001 — Keep the variance-weighted chi² helper as the canonical loss when comparing mapping vs Stage A.
- GEOMETRY-003/004 — Preserve the MappingStageAContext geometry/UB invariants when injecting calibration so the zero-point stays aligned with DB-AT-024.
- CONFORMANCE-001 — Maintain canonical env flags + artifact capture for DB-AT selectors (pytest logs + JSON under the artifacts path).
- POLICY-001 — Environment remains frozen; only source-level changes inside the workspace are permitted.

Pointers
- docs/spec-db-conformance.md:201 — DB-AT-027 tolerances and calibration payload expectations.
- docs/spec-db-core.md:86 — Variance-weighted loss definition used in `_compute_variance_weighted_loss`.
- dbex/vis/mapping.py:34 — `MappingStageAContext` structure showing how calibration metadata is sourced.
- dbex/nanobrag_refinement.py:696 — `_build_stage_a_context` (warm cache) entry point that must reuse calibration metadata.
- docs/TESTING_GUIDE.md:136 — Current DB-AT-027 registry row (needs status bump once the gate passes).

Next Up (optional)
- Phase D.D: Visualization parity + DB-AT-028/029 once zero-point calibration holds.

Doc Sync Plan (Conditional)
- After DB-AT-027 passes, rerun the collect-only command above, attach both execution + collect logs to the artifacts directory, and update `docs/TESTING_GUIDE.md` §2 plus `docs/development/TEST_SUITE_INDEX.md` with the new `Active` selector details.

Mapped Tests Guardrail
- `pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027` must report 1 collected test; treat 0 collection as a hard block.

Hard Gate
- Do not finish unless the calibrated engine probe and pytest selector both meet DB-AT-027 tolerances with artifacts written to `db_at_027/`.

Normative Math/Physics
- Reference `docs/spec-db-conformance.md:201-239` for zero-point equations and `docs/spec-db-core.md:86-90` for the variance-weighted chi²; do not rewrite the formulas.
