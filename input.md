Summary: Capture TORCH-RUNTIME-002 runtime/testing documentation updates and seed an evidence artifact for planned DB-AT selectors.
Mode: Docs
Focus: TORCH-RUNTIME-002 — Author torch runtime checklist + testing harness seed
Branch: integration
Mapped tests: none — evidence-only
Artifacts: plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/{notes.md,pytest_collect.log}
Do Now:
  1. TORCH-RUNTIME-002 — A1 (plans/active/TORCH-RUNTIME-002/implementation.md) — tests: none; tighten docs/TESTING_GUIDE.md §§1-2 with explicit KMP_DUPLICATE_LIB_OK and NANOBRAGG_DISABLE_COMPILE guidance plus cross-links to spec shards.
  2. TORCH-RUNTIME-002 — A2 (plans/active/TORCH-RUNTIME-002/implementation.md) — tests: none; add runtime-focused "Common Pitfalls" language to docs/development/testing_strategy.md §§1.4-1.6 and note the broken pytorch_runtime_checklist symlink (DOC-RUNTIME-004).
  3. TORCH-RUNTIME-002 — B1 (plans/active/TORCH-RUNTIME-002/implementation.md) — tests: none; synchronize planned DB-AT selectors between docs/TESTING_GUIDE.md and docs/development/TEST_SUITE_INDEX.md, registering TODO callouts where execution gaps remain.
  4. TORCH-RUNTIME-002 — B2 (plans/active/TORCH-RUNTIME-002/implementation.md) — tests: pytest --collect-only -q tests -k DB_AT_001; capture the command output under the artifact path as seed evidence and reference the path in docs/fix_plan.md Metrics/Artifacts lines.
Priorities & Rationale:
  - Enforce runtime environment contract from docs/spec-db-runtime.md:18-21 and surface it in the testing docs so engineers export required flags.
  - Align docs/TESTING_GUIDE.md:5-37 with current torch smoke strategy to keep normative commands discoverable and artifact policy clear.
  - Map DB-AT selectors per docs/spec-db-conformance.md:24-45 and ensure placeholders reflect their future acceptance scope.
  - Keep docs/development/TEST_SUITE_INDEX.md:5-13 synchronized with the testing guide and fix plan entries for selector parity.
  - Reinforce handoff requirements from docs/development/testing_strategy.md:32-43 so Do Now checklists remain executable for runtime work.
How-To Map:
  - export ART=plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z; mkdir -p "$ART"; touch "$ART/notes.md" to log doc deltas.
  - Edit docs/TESTING_GUIDE.md and docs/development/testing_strategy.md with explicit env flag + pitfalls guidance; record summary snippets in "$ART/notes.md".
  - Reflect selector alignment updates in docs/development/TEST_SUITE_INDEX.md and note any remaining TODOs in docs/fix_plan.md Attempts History.
  - KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001 | tee "$ART/pytest_collect.log" (expect 0 tests collected; use log as artifact).
  - Verify docs/index.md and docs/prompt_sources_map.json still reference updated files; adjust if path changes occur.
Pitfalls To Avoid:
  - Do not overwrite the external pytorch_runtime_checklist symlink target; log the broken link instead.
  - Avoid promising active DB-AT coverage—mark selectors as planned until tests exist.
  - Keep docs/index.md and prompt map synchronized if headings change.
  - Preserve Metrics/Artifacts placeholders in docs/fix_plan.md while editing attempts history.
  - Ensure artifact directory only contains lightweight text/command logs.
  - Do not delete existing TORCH-BRIDGE-001 artifacts or implementation plan.
  - Avoid editing external trees (dials/, dxtbx/, simtbx/).
  - Keep environment commands shell-safe (`export` before pytest runs).
  - Note DOC-RUNTIME-004 dependency if runtime checklist restoration blocks clarity.
If Blocked: If the broken pytorch runtime checklist prevents documenting guardrails, append a block note to docs/fix_plan.md Attempts History (Metrics: pending; Artifacts: pending) and log the dependency on DOC-RUNTIME-004 in plans/active/TORCH-RUNTIME-002/implementation.md before returning to planning.
Findings Applied (Mandatory): RUNTIME-001 — plan reiterates NANOBRAGG_DISABLE_COMPILE guard for gradchecks; CONFORMANCE-001 — plan maps KMP_DUPLICATE_LIB_OK flag and DB-AT selectors into the testing docs. No other relevant findings in the knowledge base.
