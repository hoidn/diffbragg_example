Summary: Publish IDL contracts for the torch writer + physics helpers and update their docstrings/tests so telemetry specs cite the right locations.
Mode: Docs
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata; pytest --collect-only tests/dbex/test_gradients.py -k DB_AT_010; pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata; pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T142116Z/
Do Now:
- Implement: dbex/io/writer.py::write_torch_outputs — refresh the module/function docstrings so they cite docs/architecture/dbex/io/writer.idl.md (new) and restate DIAGNOSTICS-001/PHYSICS-LOSS-001 telemetry responsibilities without touching runtime logic.
- Implement: dbex/physics/forward.py::simulate_forward_torch and dbex/physics/loss.py::compute_masked_mse_loss — mirror the writer update by pointing the docstrings to their respective IDLs, noting DB-AT-010 usage, and keeping the helpers explicitly TEST-ONLY.
- Document: docs/architecture/dbex/io/writer.idl.md; docs/architecture/dbex/physics/forward.idl.md; docs/architecture/dbex/physics/loss.idl.md — add IDL files covering signature, inputs/outputs, dependencies, normative spec citations, and change logs for each helper.
- Document: docs/architecture/module_map.md — add links to the new IDLs in the Telemetry + Physics rows and mark Phase D.1 completion so future readers know these modules are the canonical owners.
- Validate: capture the telemetry + gradcheck selectors (`AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` for all commands, plus `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, and `DBAT010_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T142116Z/db_at_010` for DB-AT-010) by running the four mapped pytest commands and teeing logs into the report directory listed above.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T142116Z/ db_at_010` to stage artifacts.
2. Update `dbex/io/writer.py`, `dbex/physics/forward.py`, and `dbex/physics/loss.py` docstrings so each references its new IDL path (e.g., “See docs/architecture/dbex/io/writer.idl.md §API & Contracts”) and reiterates the applicable findings (DIAGNOSTICS-001, PHYSICS-LOSS-001, REFINE-010) without changing logic.
3. Author the three IDL files under `docs/architecture/dbex/{io,physics}/` with headers (module, status, normative refs), API tables (inputs, outputs, telemetry), dependency notes, and change logs; mirror the structure used in `docs/architecture/dbex/refinement/context.idl.md`.
4. Extend `docs/architecture/module_map.md` so the Telemetry section links to `docs/architecture/dbex/io/writer.idl.md` and the Physics section links to the two new files; note that ARCH-REFINE-001 Phase D.1 completed the writer/physics documentation migration.
5. Capture doc diffs with `git diff docs/architecture > plans/active/ARCH-REFINE-001/reports/2025-12-01T142116Z/docs_diff.md` once edits are staged.
6. Run the mapped selectors (collect-only first, then full runs) with the env vars listed above, saving each log (`collect_cli_torch_diag.log`, `pytest_cli_torch_diag.log`, `collect_db_at_010.log`, `pytest_db_at_010.log`) plus gradcheck outputs under the artifact directory.
Pitfalls To Avoid:
- Do not change the runtime behavior or signature of write_torch_outputs / simulate_forward_torch / compute_masked_mse_loss; this loop is docs-only.
- Keep `/torch_diagnostics` schema untouched (DIAGNOSTICS-001) and avoid new datasets/attributes.
- Maintain the TEST-ONLY warning on the physics helpers; no production callers should start importing them.
- Follow the IDL template from docs/architecture/dbex/refinement/context.idl.md (Status/Normative refs/API tables/change log) for consistency.
- Preserve Environment Freeze (POLICY-001): no dependency installs or nanobrag upgrades.
- When running DB-AT-010, ensure required assets (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`, sigma metadata) exist; missing assets must be logged as blockers instead of re-generated.
- Capture collect-only logs before running each pytest selector to prove selectors still register tests.
- Ensure docstrings reference the new IDLs by relative path so IDEs surface the link; avoid absolute filesystem paths.
- Do not delete the existing context IDL or reword its change log—only add the new files.
If Blocked:
- If DB-AT-010 cannot find required assets, stop, copy the pytest log to the artifacts directory, add the failure signature to docs/fix_plan.md Attempts History + galph_memory.md, and wait for supervisor guidance.
- If the CLI telemetry test fails after docstring edits, preserve the failing log, revert only the offending change, and record the issue as a new finding or blocker before retrying.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` schema and telemetry provenance must stay byte-for-byte compatible while adding documentation references.
- PHYSICS-LOSS-001 — variance-weighted chi-squared + sigma provenance remain normative; IDLs/docstrings must cite these rules.
- REFINE-010 — Stage A ROI auto-panel telemetry guardrails stay in force; documentation must mention the finding where relevant.
- POLICY-001 — Environment Freeze forbids pip/conda installs; only repo-local files may change.
Pointers:
- docs/architecture/dbex/refinement/context.idl.md:1 — reference structure for new IDL files (Status/Normative refs/API tables/change log).
- docs/spec-db-workflow.md:70 — canonical telemetry + staging clauses to cite inside writer.idl.md.
- docs/spec-db-core.md:57 — variance/loss equations that the physics IDLs must reference.
- docs/data_dependency_manifest.md:1 — reminder of DB-AT-010 data assets required for the gradcheck selector.
- docs/TESTING_GUIDE.md:120 — selector definitions and env vars for the CLI telemetry + DB-AT-010 tests.
Next Up (optional): Create docs/architecture/dbex/refinement/engine.idl.md + JobContext-to-writer call diagrams once the IDLs in this loop land.
Mapped Tests Guardrail: Confirm both selectors collect (>0 tests) before full runs; keep the collect-only logs under the artifact path even if failures occur.
