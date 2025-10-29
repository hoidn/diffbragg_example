Summary: Capture torch bridge/CLI lessons from recent artifacts and publish them in the knowledge base with synced cross-references.
Mode: Docs
Focus: FINDINGS-LEDGER-002 — Extend knowledge base with torch experiment lessons
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py
Artifacts: plans/active/FINDINGS-LEDGER-002/reports/2025-10-29T010945Z/
Do Now:
1. FINDINGS-LEDGER-002 (plans/active/FINDINGS-LEDGER-002/implementation.md — A1-A3): mkdir -p plans/active/FINDINGS-LEDGER-002/reports/2025-10-29T010945Z/, inventory `plans/active/TORCH-BRIDGE-001/` and `plans/active/TORCH-CLI-003/` reports, and record key metrics/diagnostics in $ART/notes_phase_a.md (tests: none).
2. FINDINGS-LEDGER-002 (plans/active/FINDINGS-LEDGER-002/implementation.md — B1-B2): Draft at least three new finding entries with IDs/tags/summaries citing specs or code, update docs/findings.md, and capture git diff > $ART/findings_diff.log (tests: none).
3. FINDINGS-LEDGER-002 (plans/active/FINDINGS-LEDGER-002/implementation.md — C1-C3): Update docs (testing guide, testing index, architecture/index as needed) to reference the new findings, run `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee $ART/collect_cli.log` and `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py | tee $ART/collect_bridge.log`, and ensure selectors remain Active.
4. FINDINGS-LEDGER-002 (plans/active/FINDINGS-LEDGER-002/implementation.md — D1-D3): Update docs/fix_plan.md Attempts History with Metrics:/Artifacts:, write $ART/summary.md outlining lessons + cross-links, and confirm galph_memory.md reflects the loop outcome (tests: none).
Priorities & Rationale:
- docs/spec-db-core.md:20-41 mandates precise detector/beam/crystal mappings; extracting bridge metrics into findings keeps these geometry rules visible for future work.
- docs/spec-db-tracing.md:10-19 defines parity/tracing workflow expectations, so new findings must align with these diagnostic requirements.
- docs/index.md:45-52 establishes the knowledge base ledger as authoritative; updating it ensures documentation remains discoverable.
- docs/development/testing_strategy.md:169-174 requires artifact-backed closure for parity work, guiding how we summarize evidence in findings.
- docs/TESTING_GUIDE.md:56-68 keeps selector metadata in sync with acceptance plans; cross-linking new findings there maintains registry accuracy.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE before any pytest command; add NANOBRAGG_DISABLE_COMPILE=1 if gradient cases emerge.
- ART=plans/active/FINDINGS-LEDGER-002/reports/2025-10-29T010945Z; mkdir -p "$ART".
- Capture artifact inventories with `ls`/`sed` > "$ART/notes_phase_a.md" while noting key metrics.
- Use apply_patch to edit docs/findings.md and related docs, keeping table formatting intact.
- Record diffs via `git diff docs/findings.md > "$ART/findings_diff.log"` and aggregate doc diffs into "$ART/doc_updates.log".
- Run `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee "$ART/collect_cli.log"` and `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py | tee "$ART/collect_bridge.log"`.
- Summarize outcomes in "$ART/summary.md" and update docs/fix_plan.md Attempts History with metrics counts and artifact references.
Pitfalls To Avoid:
- Do not duplicate existing finding IDs or restate GEOMETRY-001/CONFORMANCE-001 verbatim; extend with new lessons.
- Maintain Markdown table alignment in docs/findings.md; misaligned pipes break renderers.
- Validate docs/prompt_sources_map.json with python -m json.tool after edits to avoid invalid JSON.
- Keep pytest --collect-only commands under the 10-module ceiling; reuse selectors already documented.
- Reference authoritative spec line numbers in each finding to prevent ambiguous guidance.
- Ensure collect-only logs show >0 tests before labeling selectors Active.
- Avoid editing external mirrors (`dials/`, `dxtbx/`, `cctbx_project/simtbx/`); findings should reference DBEX artifacts only.
- Leave repo clean (no staged leftovers) before handoff.
- Capture summary + diff artifacts in the new reports directory so ledger references stay accurate.
If Blocked: If artifacts needed for findings are missing or inconsistent, document the gap in $ART/notes_phase_a.md, add a blocking Attempts History entry with Metrics:/Artifacts: placeholders, and set focus status to blocked until the missing evidence is produced.
Findings Applied (Mandatory):
- GEOMETRY-001 — Plan verifies new lessons build on the existing beam center/pixel pitch guardrails from the bridge work.
- RUNTIME-001 — Commands retain required torch env flags so any runtime-focused findings remain reproducible.
- CONFORMANCE-001 — Selector documentation and collect-only evidence stay aligned with the acceptance test framework.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee $ART/collect_cli.log` (docs/TESTING_GUIDE.md §2, docs/development/TEST_SUITE_INDEX.md selector row remains Active).
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py | tee $ART/collect_bridge.log` (update notes in docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md if findings reference bridge tests).
