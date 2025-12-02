Summary:
- Capture fresh ROI scoring helper evidence and update the testing docs/registry so ARCH-BRIDGE-RESP-001 Phase B.4 can close cleanly.

Mode: Docs

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- tests/dbex/test_roi_analysis.py
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/

Do Now:
- Phase B4 — finalize ROI scoring helper documentation before archiving the bridge initiative; reserve the timestamped artifacts directory above.
- Implement: docs/TESTING_GUIDE.md (Test Taxonomy §2 + Implementation Coverage §2.1) and docs/development/TEST_SUITE_INDEX.md (Implementation Coverage table) need new entries describing `tests/dbex/test_roi_analysis.py`, its canonical commands/env, artifact paths, and spec/finding ties (DIAGNOSTICS-001, PHYSICS-LOSS-001/002/003). Mention the new `/torch_diagnostics` telemetry fields (`roi_scoring_method`, `roi_checker`) in the CLI selector row so future engineers know the provenance expectations.
- Implement: While editing the docs, reference the fresh logs you capture this loop (collect-only + pytest runs for both the ROI helper suite and the CLI telemetry selector) so the registry stays reproducible; call out `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/{collect,pytest}_roi_analysis.log` and `{collect,pytest}_cli_metadata.log` explicitly in the tables.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_roi_analysis.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/pytest_roi_analysis.log
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/pytest_cli_metadata.log

How-To Map:
1. `mkdir -p plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_roi_analysis.py > plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/collect_roi_analysis.log`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_roi_analysis.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/pytest_roi_analysis.log`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata > plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/collect_cli_metadata.log`
5. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/pytest_cli_metadata.log`
6. Edit `docs/TESTING_GUIDE.md` around the §2 tables (lines ~121-240) to add a row for the ROI scoring helper (describe the selector, canonical command/env, run time, artifact locations) and append a short note under the CLI selector row noting the `roi_payloads` requirement plus new telemetry fields.
7. Edit `docs/development/TEST_SUITE_INDEX.md` (Implementation Coverage table near the top) to add a row for `tests/dbex/test_roi_analysis.py` with the same spec references, findings, and artifact path so the registry matches the testing guide.
8. Re-read both docs to ensure the new entries cite DIAGNOSTICS-001 and PHYSICS-LOSS-001/002/003, mention the artifacts you just recorded, and keep formatting (pipes/alignment) consistent before saving.

Pitfalls To Avoid:
- This is a docs-only loop; do not touch `dbex/io/*` or other production modules while editing the registries.
- Keep the new table entries synchronized: the Testing Guide and Test Suite Index must describe the same selector, artifacts, and environment flags verbatim.
- Reference the actual artifact filenames you recorded this loop; do not point back to the 2025-12-02 logs.
- Preserve spec/finding citations (DIAGNOSTICS-001, PHYSICS-LOSS-001/002/003) so readers know why the selector exists.
- Maintain table formatting (pipes, alignment, markdown links) to avoid rendering regressions.

If Blocked:
- If pytest fails (e.g., SciPy unavailable) or collect-only output differs, capture the full log under the artifacts directory, note the failure signature in docs/fix_plan.md (ARCH-BRIDGE-RESP-001 row), and mark the initiative `blocked` until the dependency issue is resolved.
- If the tables cannot be updated cleanly (e.g., formatting macros break), record the attempted edits in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T051500Z/notes.md` and pause for supervisor guidance before proceeding.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` metadata (including `roi_scoring_method` and `roi_checker`) must remain documented and validated in the CLI selector entry.
- PHYSICS-LOSS-001 — Sigma/variance provenance for ROI scoring must be referenced when documenting the helper selector.
- PHYSICS-LOSS-002/003 — Variance-floor enforcement and ROI telemetry guardrails inform the ROI helper tests; keep those IDs cited in the docs you update.

Pointers:
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md:70 — Phase B.4 checklist requiring doc/test registry sync.
- docs/fix_plan.md:101 — Initiative ledger entry describing current status/attempt history.
- docs/TESTING_GUIDE.md:121 — Test Taxonomy tables that need the new ROI helper row.
- docs/development/TEST_SUITE_INDEX.md:7 — Implementation Coverage table that must mirror the testing guide updates.

Next Up (optional):
- Once B.4 is complete and the docs reference the fresh artifacts, mark ARCH-BRIDGE-RESP-001 as `done` and archive the initiative so work can shift to ARCH-TELEMETRY-001.
