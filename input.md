Summary: Retire the `_write_torch_outputs` alias, refresh the CLI telemetry test, and align the architecture docs so everyone points at `dbex/io/writer.py` + `dbex/physics` as the canonical owners.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata; pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/
Do Now:
- Implement: dbex/refine_one.py::_write_torch_outputs — remove the legacy alias so only `dbex.io.writer.write_torch_outputs` is exported, update the module docstring/comments, and ensure `run_nanobrag_backend` imports the shared writer directly (DIAGNOSTICS-001, PHYSICS-LOSS-001).
- Implement: tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata — assert `hasattr(dbex.refine_one, "_write_torch_outputs") is False`, keep the HDF5 assertions intact, and verify HKL + sigma provenance still flow through the shared writer path once the alias is gone.
- Document: Refresh docs/architecture/live_backend.md, docs/architecture/data_telemetry_flow.md, and docs/architecture/module_map.md so the Outputs/Telemetry sections cite `dbex/io/writer.py` and `dbex/physics/{forward,loss}.py` (reference DIAGNOSTICS-001, PHYSICS-LOSS-001, REFINE-010) and note Phase C completion.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata > plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/collect_cli_writer.log` and `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/pytest_cli_writer.log`.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/` before editing; keep `DBEX_SMOKE_*` unset so the CLI test stays on its mock fixtures.
2. In `dbex/refine_one.py`, delete `_write_torch_outputs = write_torch_outputs`, update any inline comments/docstrings referencing the old helper, and lint the file (no functional changes beyond the alias removal + doc updates).
3. Extend `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` to import `dbex.refine_one` and assert the alias is absent before calling `dbex.io.writer.write_torch_outputs`; keep the existing telemetry/HDF5 checks unchanged otherwise.
4. Update `docs/architecture/live_backend.md`, `docs/architecture/data_telemetry_flow.md`, and `docs/architecture/module_map.md` so the writer + physics sections mention the new module paths and Phase C completion; capture `git diff -- docs/architecture/live_backend.md docs/architecture/data_telemetry_flow.md docs/architecture/module_map.md > plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/docs_diff.md` once edits are staged.
5. Run the mapped pytest collect-only and full selector commands above, storing logs under the report directory; failures should be copied to the same folder with context if triage is needed before retrying.
Pitfalls To Avoid:
- Do not reintroduce `_write_torch_outputs` imports anywhere; everything should reference `dbex.io.writer` directly.
- Keep `/torch_diagnostics` schema identical (no new attrs/datasets) so DIAGNOSTICS-001 consumers stay stable.
- Tests rely on in-memory mocks—avoid touching real `sp.proc` assets or changing detector-size env vars.
- Maintain the Stage A ROI auto-panel finding (REFINE-010); no changes to ROI behavior should slip into this doc/test loop.
- Environment freeze (POLICY-001) applies—no pip installs or package upgrades.
- Preserve the float64 guardrails in gradcheck helpers; nothing in `dbex/physics` should gain side effects from doc edits.
If Blocked:
- If the CLI test fails or collect-only can’t find fixtures, save the log under the report directory, add a brief blocker note to docs/fix_plan.md Attempts History, and pause until Galph triages the regression.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — ensure `/torch_diagnostics` metadata remains unchanged while moving writer ownership.
- PHYSICS-LOSS-001 — shared loss/telemetry contracts stay centralised in `dbex/physics` + writer.
- REFINE-010 — ROI auto-panel fallback remains documented and untouched during doc updates.
- POLICY-001 — environment freeze forbids installing dependencies; stick to repo-local edits.
Pointers:
- docs/fix_plan.md:542-580 — Phase C.3 summary + new C.4 scope.
- docs/architecture/live_backend.md §§“Outputs” & “Telemetry” — update narrative to mention `dbex/io/writer.py` + `dbex/physics`.
- docs/architecture/data_telemetry_flow.md §§3-5 — pipeline diagrams referencing `_write_torch_outputs` need refresh.
- docs/architecture/module_map.md — add module responsibilities for `dbex/io/writer` and `dbex/physics`.
- docs/TESTING_GUIDE.md §2 — CLI selector expectations/env vars for `test_torch_diagnostics_metadata`.
Next Up (optional): Begin Phase D doc sync (live_backend/data_telemetry_flow/module map IDLs) once the writer/docs update lands.
Doc Sync Plan (Conditional): none — no new selectors are added; existing CLI selector already documented.
Mapped Tests Guardrail: Ensure `pytest --collect-only tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata` reports the single test before running the full selector; capture the collect log even if failures occur.
