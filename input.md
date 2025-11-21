# Input

- Summary: Enforce the DB-AT detector guard so parity selectors fail fast unless the canonical refGeom footprint is used, then rerun Stage A/B/C smokes on the full detector to capture telemetry.
- Mode: Parity
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for smoke tests
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py -k 'test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip' --smoke-detector-size=full`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mask_semantics.py -k DB_AT_021 --smoke-detector-size=full`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/

## Do Now
- Focus Item: PERF-SMOKE-DETSIZE
- Implement: `tests/conftest.py::{pytest_addoption,pytest_runtest_setup}` (factor the dataset-size resolver and add a guard that fails DB-AT*/workflow selectors unless the resolved smoke-detector-size is `"full"`, referencing `docs/spec-db-workflow.md`), `docs/TESTING_GUIDE.md` (call out the enforced guard + updated DB-AT command lines), and `docs/development/TEST_SUITE_INDEX.md` (note the new guard + artifact expectations under the Stage smoke row).
- Test: capture Stage A/B/C smokes on the full detector — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py -k 'test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip' --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log`
- Test: verify the DB-AT guard path succeeds when run correctly — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mask_semantics.py -k DB_AT_021 --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_db_at_021_full.log`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/

## How-To Map
1. Update `tests/conftest.py`: add a helper (e.g., `_resolve_smoke_dataset_size(pytestconfig)`) shared by the fixture + new guard, then implement `pytest_runtest_setup` that inspects `item.keywords`/`item.name` for `db_at` or `DB_AT` substrings. If a DB-AT/workflow test is about to run and the resolved size != `"full"`, raise `pytest.UsageError` with a message citing `docs/spec-db-workflow.md` (“DB-AT selectors SHALL assert --smoke-detector-size=full”).
2. Document the guard: in `docs/TESTING_GUIDE.md` §1.1 + §2 (Stage smokes & DB-AT rows) and `docs/development/TEST_SUITE_INDEX.md`, add language that DB-AT selectors now enforce the canonical detector footprint, include the required CLI/env knobs, and mention the new guard failure mode.
3. (Optional but recommended) Demonstrate the guard: run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mask_semantics.py -k DB_AT_021 --smoke-detector-size=small > plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_db_at_021_small_guard.log` and confirm it fails immediately with the new error; keep the log for evidence.
4. Full-detector telemetry sweep: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py -k 'test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip' --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log` and capture the runtime/perf counters (append telemetry JSON if `$DBEX_SMOKE_TELEMETRY_PATH` is set).
5. DB-AT smoke (passing) confirmation: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mask_semantics.py -k DB_AT_021 --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_db_at_021_full.log` to show the guard allows canonical runs. If feasible, capture an additional DB-AT selector log (e.g., DB_AT_020) after the guard lands.

## Pitfalls To Avoid
- Guard must only target DB-AT/workflow selectors; do not block regular Stage smoke/perf runs that intentionally use the small dataset.
- Reuse the same dataset-size resolution logic everywhere; don’t drift between env-only vs CLI-only checks.
- Keep the failure message actionable (cite `docs/spec-db-workflow.md` §“Stage Smoke Dataset Policy” and mention `--smoke-detector-size=full` / `DBEX_SMOKE_DETECTOR_SIZE=full`).
- Do not relax Stage A/B/C thresholds when running the full dataset; parity gates stay at the legacy ≥0.2 % / Stage-specific limits.
- Avoid editing runtime code (`dbex/*`); all changes stay in tests/docs per Environment Freeze.
- Capture `pytest --version`/selector logs only under the artifacts directory; no stray files in repo root.
- Remember to reset `DBEX_SMOKE_DETECTOR_SIZE` between guard tests so the failure run does not poison later commands.
- Keep env flags (`KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`) consistent with `docs/TESTING_GUIDE.md`.

## If Blocked
- If the pytest guard fires for non-DB-AT selectors or cannot reliably inspect node IDs, capture the failure trace, log the regex/keyword issue in `docs/fix_plan.md`, and pause instead of shipping a brittle heuristic.
- If Stage smokes on the full detector regress (e.g., LBFGS fails or runtimes explode), archive the failing log + telemetry JSON, mark the fix-plan item blocked with the telemetry summary, and stop rather than downgrading gates.

## Findings Applied (Mandatory)
- CONFORMANCE-001 — DB-AT selectors must enforce canonical acceptance profiles; the guard ensures we cannot run cropped assets during conformance runs.
- CONFIG-001 — Detector geometry/mask polarity invariants depend on the original refGeom footprint, so the guard prevents small-detector metadata from leaking into uptake tests.
- TESTING-003 — Update selector documentation/logs in lockstep so collection evidence references the guard-enabled commands.

## Pointers
- docs/spec-db-workflow.md:46 — Stage Smoke Dataset Policy (DB-AT selectors SHALL assert `--smoke-detector-size=full`).
- docs/TESTING_GUIDE.md:30 — Environment flags + Stage smoke selector table that now need the guard details.
- docs/development/TEST_SUITE_INDEX.md:12 — Registry entry describing Stage smokes/DB-AT parity workflow.
- tests/conftest.py:1 — Existing pytest option + fixtures where the guard and shared resolver live.
- plans/active/PERF-SMOKE-DETSIZE/implementation.md:25 — Phase B3/C1 checklist tracking the guard + documentation deliverables.

## Next Up (optional)
1. Once DB-AT guard + telemetry reruns land, unblock PHYSICS-LOSS-001 to resume the variance-weighted helper work on the cropped fixture.

## Mapped Tests Guardrail
- Before running the Stage smokes on the full detector, execute `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_a_expansion --smoke-detector-size=full` and ensure ≥1 test is collected.
- Do the same for the DB-AT selector: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_mask_semantics.py -k DB_AT_021 --smoke-detector-size=full`; if either collects 0, fix the guard/configuration before running the full suites.
