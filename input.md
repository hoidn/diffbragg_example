Summary: Capture CLI backend test evidence and sync ledgers/docs so TORCH-CLI-003 can close cleanly.
Mode: TDD
Focus: TORCH-CLI-003 — Wire torch backend flag into CLI
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py
Artifacts: plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/
Do Now:
1. TORCH-CLI-003 (plans/active/TORCH-CLI-003/implementation.md — C1): mkdir -p plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/, run KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py | tee plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/pytest_cli.log, confirm all six tests pass, then update Phase A/B checkboxes once evidence captured.
2. TORCH-CLI-003 (plans/active/TORCH-CLI-003/implementation.md — C2): Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the CLI selector + environment flags, run KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log, and reference the log in both docs.
3. TORCH-CLI-003 (plans/active/TORCH-CLI-003/implementation.md — C3): Refresh docs/fix_plan.md Attempts History with Metrics:/Artifacts: for this loop, update docs/spec-db-interfaces.md status note to reflect implemented --backend flag, and capture git diff --stat > plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/doc_diff.log (tests: none).
Priorities & Rationale:
- docs/fix_plan.md:49-58 keeps TORCH-CLI-003 in-progress until torch CLI smoke + docs/tests are validated; closing requires fresh evidence.
- docs/spec-db-interfaces.md:6-12 still claims --backend is unimplemented, so we must update the normative status to match reality.
- docs/TESTING_GUIDE.md:56-80 and docs/development/TEST_SUITE_INDEX.md:7-24 lack the new CLI selector; syncing them keeps registry accuracy per exit criteria.
- docs/pytorch_runtime_checklist.md:39-45 mandates exporting KMP_DUPLICATE_LIB_OK=TRUE for torch flows; plan enforces this in commands and documentation.
- plans/active/TORCH-CLI-003/implementation.md Phase C (C1-C3) provides the checklist we must execute before marking the initiative done.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE before any pytest command.
- ART=plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z; mkdir -p "$ART".
- KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py | tee "$ART/pytest_cli.log".
- KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee "$ART/collect_cli.log".
- git diff --stat > "$ART/doc_diff.log" after doc updates.
- Update docs via apply_patch, keeping ASCII and concise rationale comments only where needed.
Pitfalls To Avoid:
- Forgetting to set KMP_DUPLICATE_LIB_OK=TRUE will cause torch imports to fail the CLI tests.
- Do not mark CLI selector Active unless collect-only shows >0 tests.
- Avoid editing external mirrors (dials/, dxtbx/, simtbx/).
- Keep artifact filenames consistent with the plan path to simplify ledger references.
- Ensure docs/spec-db-interfaces.md status text matches implemented behavior; no stale caveats.
- Update both testing docs together to maintain selector parity.
- Capture pytest exit code in logs; rerun if failures occur before updating ledgers.
- Keep repo clean (no staged leftovers) before handing off.
If Blocked: If CLI test fails or dependencies missing, capture the failing log in $ART, describe the failure in docs/fix_plan.md Attempts History with Metrics:/Artifacts: placeholders, and mark the initiative blocked with root cause; alert supervisor before switching focus.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Plan keeps CLI selector documentation aligned with DB-AT acceptance infrastructure and enforces required KMP flags.
Doc Sync Plan (Mandatory):
- Add `pytest -v tests/dbex/test_refine_one_cli.py` as Active selector in docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with environment note (`KMP_DUPLICATE_LIB_OK=TRUE`); command: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log.
- Reference the same artifact path when updating both documents and ensure selector status reflects actual collection count (>0).
