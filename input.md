Summary: Move PARITY-HARNESS-001 into Phase C by syncing parity harness guidance across testing docs and prompt sources.
Mode: Docs
Focus: PARITY-HARNESS-001 — Author DB-AT parity harness specs
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/
Do Now:
1. PARITY-HARNESS-001 C1 — Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md parity rows with harness metrics, env flags, and artifact requirements (plans/active/PARITY-HARNESS-001/implementation.md §Phase C) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001
2. PARITY-HARNESS-001 C2 — Add docs/parity_harness_spec.md to docs/index.md and docs/prompt_sources_map.json so prompts surface the harness blueprint (plans/active/PARITY-HARNESS-001/implementation.md §Phase C) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
3. PARITY-HARNESS-001 C3 — Capture doc diff summary + pytest collect logs under the new report path and append Metrics/Artifacts lines in docs/fix_plan.md Attempts History (plans/active/PARITY-HARNESS-001/implementation.md §Phase C) — tests: none — evidence-only
Priorities & Rationale:
- docs/parity_harness_spec.md:7 anchors the normative harness requirements we must propagate into downstream guidance.
- docs/TESTING_GUIDE.md:61 still lists DB_AT_001/002 as planned without harness details; Phase C requires synchronizing these entries.
- docs/development/TEST_SUITE_INDEX.md:17 mirrors the taxonomy and must advertise the same parity metadata to stay authoritative.
- docs/index.md:137 currently omits the new harness spec, so readers cannot discover the blueprint without this update.
- docs/spec-db-tracing.md:10 enforces the trace-first workflow that needs to be reflected in the updated documentation.
How-To Map:
- export ART=plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z; mkdir -p "$ART"
- KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001 | tee "$ART/collect_DB_AT_001.log"
- KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002 | tee "$ART/collect_DB_AT_002.log"
- python -m json.tool docs/prompt_sources_map.json >/dev/null  # run after edits to validate JSON
- git diff docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md docs/index.md docs/prompt_sources_map.json > "$ART/doc_diffs.log"
- printf "Phase C doc sync summary\n" > "$ART/summary.md"  # expand with key updates before handoff
Pitfalls To Avoid:
- Do not mark DB_AT selectors Active while they still collect 0 tests.
- Keep docs/TESTING_GUIDE.md and docs/development/TEST_SUITE_INDEX.md tables perfectly synchronized.
- Preserve all environment guards (`KMP_DUPLICATE_LIB_OK`, `NANOBRAGG_DISABLE_COMPILE`, `CUDA_VISIBLE_DEVICES=''`) when updating guidance.
- Maintain JSON validity in docs/prompt_sources_map.json (no trailing commas).
- Reference docs/parity_harness_spec.md with correct relative paths in both index and prompt map.
- Use the new artifact directory (2025-10-29T002248Z) for every log and summary; avoid mixing with earlier runs.
- Capture pytest collect logs even though selectors remain planned (0 tests expected).
- Avoid rewriting unrelated selectors or sections when editing documentation tables.
If Blocked: Record the issue in plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/blockers.md, set the fix-plan item to `blocked` with rationale, log the block in galph_memory.md, and pivot focus per FSM dwell rules.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Plan keeps DB-AT selectors canonical and uses KMP_DUPLICATE_LIB_OK=TRUE in every command (docs/findings.md:7).
- RUNTIME-001 — Determinism updates will reiterate NANOBRAGG_DISABLE_COMPILE=1 and related guards for DB-AT-002 (docs/findings.md:6).
Doc Sync Plan (Mandatory):
- DB_AT_001 — KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001 (expected 0; keep Planned) → plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/collect_DB_AT_001.log
- DB_AT_002 — KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002 (expected 0; keep Planned) → plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/collect_DB_AT_002.log
