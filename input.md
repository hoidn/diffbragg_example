Summary: Publish the Phase D architecture doc update ledger so downstream teams can cite a single summary, and keep the Stage A selector evidence current.
Mode: Docs
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity; pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity; pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry; pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/
Do Now:
- Implement: plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/architecture_doc_update.md — synthesize the completed D1–D4 edits (live_backend, data_telemetry_flow, module_map, testing guide, test suite index, IDLs) into a concise report with section refs + spec/finding citations (DIAGNOSTICS-001, ARCH-ENGINE-003, REFINE-010) so future initiatives can cite one artifact.
- Implement: docs/fix_plan.md — add the Phase D.5 entry referencing the new architecture_doc_update.md once it exists, and note any doc nits resolved while compiling the summary.
- Document: plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/docs_diff.md — capture `git diff docs` output (or explicit snippets if the diff is empty) alongside a short annotation describing what changed between D2 completion and this ledger.
- Validate: run the Stage A zero-point parity selector and the Stage A telemetry smoke (collect-only first, then full) with `AUTHORITATIVE_CMDS_DOC`, `DBAT027_ARTIFACT_DIR`, `KMP_DUPLICATE_LIB_OK=TRUE`, and `NANOBRAGG_DISABLE_COMPILE=1` set; tee the logs into the artifacts directory listed above.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `export DBAT027_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/db_at_027`; create the artifacts directory (`mkdir -p .../2025-12-01T150955Z/db_at_027`).
2. Draft `architecture_doc_update.md`: enumerate each doc touched in D1–D4, cite the relevant sections (e.g., live_backend.md §§Entrypoints & Implementation Interfaces, data_telemetry_flow.md §Pipeline, module_map table row updates, TESTING_GUIDE §2.1, TEST_SUITE_INDEX §Stage A selectors, the new IDLs) plus the spec/finding they align with. Close with a verification note pointing to the Stage A selectors being refreshed this loop.
3. Record the doc diff snapshot by running `git diff -- docs` after the summary edits (if empty, state "no changes") and saving it to `docs_diff.md` with a one-line explanation per file.
4. Update `docs/fix_plan.md` Phase D Attempts History to reference the new report path once both the summary and doc diff files exist; mention that selector evidence lives in the same timestamped directory.
5. Tests:
   a. `pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity > plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/collect_db_at_027.log`
   b. `pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity | tee .../pytest_db_at_027.log`
   c. `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry > .../collect_stage_a_engine_telemetry.log`
   d. `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry | tee .../pytest_stage_a_engine_telemetry.log`
Pitfalls To Avoid:
- Do not modify production Stage A/B/C code paths; this loop is documentation-only aside from ledger updates.
- Keep references to specs/findings exact—quote section numbers instead of paraphrasing math from spec-db-core/workflow.
- Maintain Environment Freeze (POLICY-001): no package installs or dataset regeneration while collecting selector evidence.
- Stage A parity selectors depend on `sp.proc/refGeom*` assets; verify `DBAT027_ARTIFACT_DIR` exists before running pytest or the tests will overwrite prior evidence.
- Capture collect-only logs before each pytest run to preserve selector health per TESTING_GUIDE §1.4.
- If the doc diff is empty, explicitly say so in docs_diff.md rather than omitting the file.
- Reuse the same timestamped artifacts directory; don’t scatter logs across prior runs.
- When editing docs/fix_plan.md, do not remove historical Attempts entries—append the new reference instead.
If Blocked:
- If either Stage A selector fails or assets are missing, stop, archive the failing log under the artifacts directory, and log the failure signature (error text, env vars) in docs/fix_plan.md + galph_memory.md before yielding.
- If you uncover additional stale docs that require content edits beyond the planned summary, note the file and scope in docs/fix_plan.md and pause for supervisor guidance.
Findings Applied (Mandatory):
- ARCH-ENGINE-003 — document that telemetry enrichment sits on the engine-only path; selectors prove the guard remains green.
- REFINE-010 — remind readers that Stage A auto-panel threshold is in effect when citing detector-size behavior.
- DIAGNOSTICS-001 — `/torch_diagnostics` writer ownership must stay explicit in the summary.
- POLICY-001 — reaffirm Environment Freeze while running selectors and editing docs.
Pointers:
- docs/architecture/live_backend.md:1 — Entrypoints/Modes + Implementation Interfaces sections that the summary must cite.
- docs/architecture/data_telemetry_flow.md:1 — Pipeline description needing updated prose reference.
- docs/TESTING_GUIDE.md:160 — Selector registry row for `test_stage_a_engine_delegation_telemetry`.
- docs/development/TEST_SUITE_INDEX.md:19 — Stage A selector entry requiring cross-reference.
- docs/findings.md:75 — ARCH-ENGINE-003 guardrail text to cite.
Next Up (optional):
- Kick off the next ARCH-REFINE-001 phase (e.g., RefinementContext/JobContext enforcement in CLI) once the doc ledger is published.
Mapped Tests Guardrail:
- Both selectors must report `collected 1 item`; if collection returns 0, fix immediately (or mark blocked) before attempting the test run.
