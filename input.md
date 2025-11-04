Summary: Enforce CLI failure when refined structure factors are requested but not consumed, with regression tests and doc sync.
Mode: none
Focus: MAP-SCALE-005 — CLI refined telemetry enforcement
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors
- pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors --maxfail=1
- pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1
Artifacts: plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/
Do Now:
- MAP-SCALE-005: Implement: dbex/refine_one.py::run_nanobrag_backend — raise a RuntimeError (or SystemExit with code 1) when `--refined-mtz` is supplied but refined structure factors are not loaded or telemetry downgrades to "raw"; extend tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors to cover the failure path (expecting the new error) and keep test_nanobrag_backend_uses_refined_mtz asserting telemetry remains "refined". Validate: pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors; pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors --maxfail=1; pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1. Capture stdout/stderr via tee into the new artifact directory and update docs/TESTING_GUIDE.md plus docs/development/TEST_SUITE_INDEX.md with the guard behavior.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. MAPSCALE005_ARTIFACT_DIR=plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors | tee plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/collect_refined_mtz_guard.log
3. MAPSCALE005_ARTIFACT_DIR=plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors --maxfail=1 | tee plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_refined_mtz_guard.log
4. MAPSCALE005_ARTIFACT_DIR=plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 | tee plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_refined_mtz_success.log
Pitfalls To Avoid:
- Do not allow `run_nanobrag_backend` to silently fall back to raw MTZ when `--refined-mtz` is requested.
- Keep the error message actionable (reference the flag and expected asset path) without exposing stack traces.
- Preserve legacy behavior when `--refined-mtz` is absent; only enforce for refined requests.
- Ensure new tests rely on mocks (no real nanobrag_torch execution) and clean up temp files.
- Capture logs under the specified artifact directory; no ad-hoc paths.
- Maintain telemetry field names and existing diagnostics structure.
- Update docs/test registries in the same loop once code passes; no TODO deferrals.
- Respect Environment Freeze—no package installs or tooling changes.
- Avoid `sys.exit` without message; prefer raising RuntimeError that tests can assert.
- Keep pytest selectors deterministic (no `-k` wildcards that could miss new tests).
If Blocked: Document the failure cause in plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/blocked.md, add a blocked entry to docs/fix_plan.md Attempts History (include minimal error signature), update galph_memory.md with block status, and pivot per loop discipline.
Findings Applied:
- SCALE-003 — Refined |F| amplitudes must be used for calibrated parity; CLI guard enforces ingestion.
- SCALE-004 — Calibration metadata and refined structure factors travel together; falling back to raw violates this pairing.
- SCALE-007 — Telemetry must fail fast when refined assets report `raw`; CLI now mirrors DB_AT_024 guard.
- TESTING-003 — New selector coverage requires collect-only evidence and synchronized documentation.
Pointers:
- dbex/refine_one.py:218 — Current warning-based fallback logic for refined MTZ ingestion.
- dbex/refine_one.py:347 — Telemetry payload passed to `_write_torch_outputs`.
- tests/dbex/test_refine_one_cli.py:357 — Existing refined MTZ regression test structure to extend.
- docs/findings.md:20 — SCALE-007 guardrail definition.
- docs/TESTING_GUIDE.md:86 — CLI selector row that must reflect the new failure behavior.
Next Up (optional): 1) After guard lands, audit user-facing CLI docs to describe the refined MTZ failure mode.
Doc Sync Plan (Conditional): After tests pass, rerun `pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors` with logs archived to the artifact directory, then update docs/TESTING_GUIDE.md and docs/development/TEST_SUITE_INDEX.md to document the enforced failure (include log paths and refined telemetry notes) before marking the initiative ready for closure.
