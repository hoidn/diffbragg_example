Summary: Establish DB-AT-001/002 parity harness groundwork and evidence audit.
Mode: Docs
Focus: PARITY-HARNESS-001 — Author DB-AT parity harness specs
Branch: main
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/{audit_notes.md,doc_refs.json,pytest_collect_DB_AT_001.log,pytest_collect_DB_AT_002.log}
Do Now:
  1. PARITY-HARNESS-001 A1 — Audit `docs/spec-db-conformance.md`, `docs/development/testing_strategy.md`, and `docs/TESTING_GUIDE.md` for DB-AT-001/002 gaps; capture findings in audit_notes.md (plans/active/PARITY-HARNESS-001/implementation.md) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001 | tee plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/pytest_collect_DB_AT_001.log
  2. PARITY-HARNESS-001 A2 — Review TORCH-BRIDGE-001/TORCH-CLI-003 report artifacts for reusable parity metrics; summarize reusable signals in doc_refs.json (plans/active/PARITY-HARNESS-001/implementation.md) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002 | tee plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/pytest_collect_DB_AT_002.log
  3. PARITY-HARNESS-001 A3 — Define artifact strategy (reports layout, required summary.md/metrics template) and note planned doc skeleton for B-phase handoff (plans/active/PARITY-HARNESS-001/implementation.md) — tests: none
Priorities & Rationale:
- `docs/spec-db-conformance.md:10-44` — Conformance profile outlines DB-AT-001/002 thresholds; audit ensures spec deltas surface before drafting harness.
- `docs/development/testing_strategy.md:120-220` — Parity matrix and artifact policy demand mapping selectors to metrics; audit confirms alignment before blueprinting.
- `docs/TESTING_GUIDE.md:40-120` — Test taxonomy must stay synchronized with harness updates; early gap analysis prevents divergence.
- `docs/spec-db-tracing.md:15-60` — Metrics capture requirements guide artifact schema design for parity runs.
How-To Map:
- `export KMP_DUPLICATE_LIB_OK=TRUE`
- `ART=plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z && mkdir -p "$ART"`
- `pytest --collect-only -q -k DB_AT_001 | tee "$ART/pytest_collect_DB_AT_001.log"`
- `pytest --collect-only -q -k DB_AT_002 | tee "$ART/pytest_collect_DB_AT_002.log"`
- `python scripts/orchestration/plan_lint.py --focus PARITY-HARNESS-001` (sanity check plan references)
- Document findings in `$ART/audit_notes.md` and `$ART/doc_refs.json`
Pitfalls To Avoid:
- Forgetting to export `KMP_DUPLICATE_LIB_OK=TRUE` before pytest.
- Treating zero collected tests as success without recording rationale.
- Missing references to `plans/active/PARITY-HARNESS-001/implementation.md` in artifacts.
- Overwriting previous reports instead of using timestamped directory.
- Skipping reusable metrics from TORCH-* reports or forgetting to note `NANOBRAGG_DISABLE_COMPILE=1` for gradcheck contexts.
- Letting audit notes drift from spec citations.
- Omitting artifact schema for future parity metrics.
- Neglecting to tee pytest output into logs for ledger evidence.
- Using relative paths that break when run outside repo root.
- Editing production code paths during documentation audit.
If Blocked: If golden datasets or prior artifacts are inaccessible, pause implementation, note the missing dependency in audit_notes.md, mark A2 as partial, and record block in `docs/fix_plan.md` Attempts History plus galph_memory with next action "switch_focus".
Findings Applied (Mandatory):
- CONFORMANCE-001 — Audit ensures DB-AT selectors and environment flags stay authoritative during harness planning.
- RUNTIME-001 — Plan enforces exporting `NANOBRAGG_DISABLE_COMPILE` when future gradchecks arise; reminder captured in audit notes.
