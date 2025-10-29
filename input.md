Summary: Advance Phase B of PARITY-HARNESS-001 by drafting the DB-AT-001/002 harness spec and aligning the checklist with parity metrics requirements.
Mode: Docs
Focus: PARITY-HARNESS-001 — Author DB-AT parity harness specs
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/
Do Now:
1. PARITY-HARNESS-001 B1 — Draft docs/parity_harness_spec.md with normative DB-AT-001/002 datasets, env flags, metrics, and trace workflow (plans/active/PARITY-HARNESS-001/implementation.md §Phase B) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001
2. PARITY-HARNESS-001 B2 — Update plans/active/PARITY-HARNESS-001/implementation.md Phase B checklist with sub-tasks tied to the new spec and artifact schema — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
3. PARITY-HARNESS-001 B3 — Publish metrics/trace template and artifact layout snippet in docs/parity_harness_spec.md and capture copies under the report path — tests: none — evidence-only
Priorities & Rationale:
- docs/spec-db-conformance.md:10-28 mandates DB-AT-001/002 thresholds and commands, so the harness spec must codify datasets, metrics, and env guards.
- docs/development/testing_strategy.md:168-180 requires standardized parity metrics and artifact-backed closure, guiding the metrics template deliverable.
- docs/spec-db-tracing.md:10-19 prescribes the trace-first workflow we must embed in the harness blueprint.
- docs/TESTING_GUIDE.md:58-67 lists DB_AT selectors that the spec must reference to keep guidance unified.
- docs/development/TEST_SUITE_INDEX.md:7-13 expects selector metadata to mirror the guide; plan updates ensure future doc sync.
How-To Map:
- export ART=plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z; mkdir -p "$ART/parity"
- KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001 | tee "$ART/collect_DB_AT_001.log"
- KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002 | tee "$ART/collect_DB_AT_002.log"
- Use $EDITOR docs/parity_harness_spec.md to author normative sections citing docs/spec-db-conformance.md, testing_strategy.md, TESTING_GUIDE.md, and spec-db-tracing.md
- Update plans/active/PARITY-HARNESS-001/implementation.md Phase B checklist entries when B1-B3 deliverables land
- Copy finalized metrics schema and trace checklist into "$ART/parity/metrics_template.json" and "$ART/parity/trace_requirements.md" for evidence
Pitfalls To Avoid:
- Skipping correlation ≥0.99 requirement or tolerances from specs when drafting the harness.
- Forgetting determinism env flags (`CUDA_VISIBLE_DEVICES=''`, `TORCHDYNAMO_DISABLE=1`, `NANOBRAGG_DISABLE_COMPILE=1`) for DB-AT-002 guidance.
- Assuming nanoBragg2 golden data exists locally without documenting verification steps.
- Leaving docs/index.md or prompt_sources_map.json without hooks to the new spec once published.
- Marking checklist items complete without artifacts in the report directory.
- Omitting trace capture workflow mandated by spec-db-tracing.md in the spec draft.
- Diverging metrics schema from proposed correlation/MSE/RMSE/max|Δ|/sum_ratio core fields.
If Blocked: Document the blocker in plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/blockers.md, update docs/fix_plan.md Attempts History with the issue and `Status: blocked`, then pivot per dwell guard.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Harness spec keeps DB-AT selectors and KMP_DUPLICATE_LIB_OK=TRUE canonical (docs/findings.md:7).
- RUNTIME-001 — Determinism guidance reiterates NANOBRAGG_DISABLE_COMPILE=1 and related flags (docs/findings.md:6).
