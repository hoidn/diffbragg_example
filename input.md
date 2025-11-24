Summary: Finish DB-AT-027 Phase D.B by wiring artifact logging + selector registration so the zero-point probe is reproducible before calibration fixes land.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/

Do Now
- Implement: tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity + docs/TESTING_GUIDE.md::§2 DB-AT table + docs/development/TEST_SUITE_INDEX.md::Implementation Coverage — add DBAT027 artifact plumbing (env var `DBAT027_ARTIFACT_DIR`, JSON/command logs, env capture), keep the strict xfail reason tied to STAGEA-001, and register the selector in both docs with the exact command/env knobs + artifact expectations so DB-AT-027 becomes a first-class gate.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/db_at_027 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/pytest_db_at_027.log
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/{stage_a_engine_probe/stage_a_engine_zero_point.json,stage_a_engine_probe/cli_stage_a_engine_zero_point.log,db_at_027/db_at_027_metrics.json,db_at_027/db_at_027_env.json,pytest_db_at_027.log,pytest_db_at_027_collect.log,summary.md}

How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `export DBAT027_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/db_at_027`; create both `stage_a_engine_probe` and `db_at_027` subdirs under the artifacts root.
2. Run the plan-local CLI to capture raw metrics: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/stage_a_engine_probe | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/stage_a_engine_probe/cli_stage_a_engine_zero_point.log` (expect exit 1 until calibration lands; keep JSON/log even on failure).
3. Extend `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` to require `DBAT027_ARTIFACT_DIR`, emit `db_at_027_metrics.json` (result dict) and `db_at_027_env.json` (sigma source, detector size, git head) in that directory, and keep ROI CC samples + tolerances in the JSON. Continue to xfail strictly with STAGEA-001 in the reason string.
4. Rerun the pytest selector with the env vars listed in Do Now; tee stdout to `pytest_db_at_027.log` and ensure the artifact JSONs are written inside `db_at_027/`.
5. Collect-only verification: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/pytest_db_at_027_collect.log`.
6. Update `docs/TESTING_GUIDE.md` §2 with a DB-AT-027 row (command, env vars, artifacts, tolerance summary) and add a matching row to `docs/development/TEST_SUITE_INDEX.md` noting status `xfail (known Stage A zero-point gap, STAGEA-001)`.
7. Sync `plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/summary.md` with the Turn Summary (CLI metrics, pytest status, doc updates) and stage artifacts for supervisor review.

Pitfalls To Avoid
- Do not run pytest/CLI without `DBEX_SMOKE_SIGMA_SOURCE=metadata` and `DBEX_SMOKE_DETECTOR_SIZE=full`; DB-AT selectors must adopt the canonical environment.
- Never drop the strict xfail: it encodes the STAGEA-001 calibration gap and guards against silent XPASS before calibration plumbing lands.
- Artifact JSONs must include tolerances + ROI CC samples; omitting fields makes comparisons impossible.
- Keep the helper/test CPU-only with `NANOBRAGG_DISABLE_COMPILE=1`; CUDA variance may hide zero-point drift.
- Ensure artifact dirs exist before writing; missing directories will fail the test.
- Docs/TESTING_GUIDE entries must cite the exact env vars + artifact filenames; vague references won’t meet the registry standard.
- Treat CLI/test failures as blocking until logged; don’t rerun with modified tolerances.
- Do not edit simulator calibration plumbing in this loop—focus strictly on instrumentation.
- Preserve Environment Freeze; no package installs to chase missing imports.
- Make sure `pytest_db_at_027_collect.log` shows at least 1 collected test; otherwise halt and triage.

If Blocked
- If CLI/test fails before producing telemetry (e.g., missing assets or torch import breakage), capture the stack trace in `stage_a_engine_zero_point.json`, upload the log to `plans/active/TOOLING-VIS-001/reports/2025-11-24T221459Z/`, mark TOOLING-VIS-001 `blocked` in docs/fix_plan.md with the error signature, and ping supervisor before changing tolerances.

Findings Applied (Mandatory)
- STAGEA-001 — Reminds us the zero-point miscalibration is expected; keep the strict xfail and document metrics to show the gap.
- CONFORMANCE-001 — DB-AT selectors need env guards + artifact capture; follow the Testing Guide contract when adding DB-AT-027.
- PHYSICS-LOSS-001 — Ensure chi² metrics come from the canonical variance-weighted helper so tolerances remain faithful to the spec.
- GEOMETRY-003/004 — Mapping context + incremental UB invariants mean the helper/test must reuse `build_mapping_stage_a_context` and `_build_final_bragg_from_stage_a_telemetry` without re-deriving geometry.
- POLICY-001 — Environment Freeze stays in effect; document blockers rather than patching upstream deps.

Pointers
- docs/spec-db-conformance.md:200 — Normative DB-AT-027 tolerances (mean/max |Δ|, chi² rel diff, masked pixel counts).
- docs/TESTING_GUIDE.md:118 — DB-AT selector registry format + env flag policy (mirror this when adding DB-AT-027).
- docs/development/TEST_SUITE_INDEX.md:1 — Table schema for registering selectors + statuses.
- plans/active/TOOLING-VIS-001/implementation.md:180 — Phase D checklist outlining D.B expectations.
- plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/summary.md — Previous loop’s nucleus + next actions for DB-AT-027 instrumentation.

Next Up (optional)
- Phase D.C plumbing: thread calibration payload (spot_scale_override, flux/exposure, N_cells) through Stage A engine once the instrumentation is stable.

Doc Sync Plan (Conditional)
- After pytest passes/xfails, run the collect-only command above, archive the log, then update both `docs/TESTING_GUIDE.md` (§2 DB-AT table) and `docs/development/TEST_SUITE_INDEX.md` with the new selector entry (status `xfail`, env vars, artifact set). Keep doc diffs in the same commit.

Mapped Tests Guardrail
- `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` must collect (>0 tests) even when xfail; treat a zero-collection result as a hard block and stop immediately.

Hard Gate
- Do not downgrade DB-AT-027: if the selector or CLI collects 0 or artifacts are missing, the loop cannot finish as done. Keep the tolerances tight and leave the xfail reason untouched until calibration plumbing ships.

Normative Math/Physics
- Reference `docs/spec-db-conformance.md:200-239` verbatim for zero-point parity equations and `docs/spec-db-core.md:86-90` for the variance-weighted chi² helper; no ad-hoc derivations.
