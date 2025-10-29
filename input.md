Summary: Document the Environment Freeze blockers for NANOBRAG-GOLDEN-001 and prepare the ledger/docs handoff before marking the initiative blocked.
Mode: Docs
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 (expected ModuleNotFoundError)
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/{planning_notes.md,env_diagnostics.log,collect_db_at_001_parity.log,collect_db_at_001_forward.log}
Do Now:
  1. NANOBRAG-GOLDEN-001::A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Capture PATH, `python3 --version`, and failed `nanobrag_torch`/`simtbx` imports in env_diagnostics.log under the 2025-10-29T061218Z report to document missing dependencies. tests: none.
  2. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Run `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001` and archive stdout/stderr to collect_db_at_001_parity.log so the active selector evidence stays current. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001.
  3. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Attempt `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001`, capture the ModuleNotFoundError in collect_db_at_001_forward.log, and note the blocker in planning_notes.md. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
  4. NANOBRAG-GOLDEN-001::D3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Update docs/fix_plan.md to set status=blocked with the new artifact paths, reconcile docs/TESTING_GUIDE.md §2 taxonomy with the blocked selector, and add the attempts-history entry. tests: none.
Priorities & Rationale:
- plans/active/NANOBRAG-GOLDEN-001/implementation.md:4-6 — Phase A tasks require dependency evidence before any dataset capture can proceed.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 mandates paired DiffBragg/torch metrics, so recording the lack of simtbx keeps the conformance ledger honest.
- docs/TESTING_GUIDE.md:85-86 — Selector registry already marks forward equivalence blocked; the taxonomy table must match to avoid confusing implementers.
- docs/findings.md:13 — TESTING-003 requires synchronized selector status and collection logs whenever documentation changes.
How-To Map:
- `bash -lc '{ echo "PATH=$PATH"; which python3; python3 --version; python3 -c "import simtbx"; python3 -c "import nanobrag_torch"; } |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/env_diagnostics.log'`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/collect_db_at_001_forward.log`
- Use apply_patch to update docs/fix_plan.md status/Attempts History and to align docs/TESTING_GUIDE.md taxonomy with the blocked selector evidence.
Pitfalls To Avoid:
- Do not attempt package installs; Environment Freeze forbids changing the runtime.
- Use `python3`, not `python`, when capturing diagnostics (shim missing).
- Keep all new logs inside the 2025-10-29T061218Z report directory for traceability.
- Avoid rerunning more pytest selectors than the mapped ones; evidence-only loop limit is ≤10 modules.
- Do not delete or overwrite prior reports when adding new artifacts.
- Preserve stderr in the collect-only logs; do not filter the ModuleNotFoundError.
- Update docs in the same loop as ledger changes to prevent drift.
- Note Environment Freeze context explicitly in fix_plan to avoid future rework.
- Confirm commands run from repo root to avoid path mismatches.
- Coordinate doc edits so taxonomy and module tables share the same artifact paths.
If Blocked: Record the exact failing command/output in env_diagnostics.log or collect_db_at_001_forward.log, append the blocker summary plus return condition to docs/fix_plan.md and planning_notes.md, and log the state as `blocked` with next_action=`switch_focus` in galph_memory if progress remains impossible.
Findings Applied (Mandatory):
- TESTING-003 — Ensures selector documentation stays synchronized with fresh collect-only logs.
- CONFIG-001 — Reminds implementers that DiffBragg/nanobrag alignment hinges on proper config hydration once dependencies exist.
- CONFORMANCE-001 — Keeps acceptance criteria central when documenting why DB_AT_001 cannot run.
- DIAGNOSTICS-001 — Motivates capturing detailed stderr/stdout artifacts for traceability.
- PARITY-001 — Preserves first-divergence readiness by maintaining comprehensive parity selector artifacts.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/collect_db_at_001_forward.log`
- Update docs/TESTING_GUIDE.md §2 taxonomy and docs/development/TEST_SUITE_INDEX.md module table to reference the new 2025-10-29T061218Z logs once collected.
