Summary: Bootstrap the DB_AT parity harness by documenting the missing parity dataset, drafting manifest stubs, and adding a skip-aware DB_AT_001 scaffold.
Mode: TDD
Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_smoke.py
Artifacts: plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/
Do Now:
1. PARITY-HARNESS-002 (plans/active/PARITY-HARNESS-002/implementation.md — A1) — Audit parity dataset availability, record findings and gap analysis in $ART/notes_phase_a.md, and catalogue any potential sources or blockers (tests: none).
2. PARITY-HARNESS-002 (plans/active/PARITY-HARNESS-002/implementation.md — A2) — Draft `tests/fixtures/parity_manifest_template.json` plus schema/README stubs that encode checksum fields and expected metadata, capturing template output in $ART/manifest_template.json (tests: none).
3. PARITY-HARNESS-002 (plans/active/PARITY-HARNESS-002/implementation.md — A3) — Implement loader/fixture that reads the manifest template, skips with reason `parity dataset unavailable` when no dataset is present, and author minimal `tests/dbex/test_db_at_001_parity.py::test_manifest_template_is_documented`; run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001 | tee $ART/pytest_DB_AT_001.log`.
4. PARITY-HARNESS-002 (plans/active/PARITY-HARNESS-002/implementation.md — A4) — Run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_smoke.py | tee $ART/pytest_smoke.log` to confirm bridge smoke remains green after fixture integration.
Priorities & Rationale:
- docs/parity_harness_spec.md:28-111 now records the dataset gap and manifest requirements; A1-A3 keep harness scaffolding aligned without duplicating nonexistent data.
- docs/spec-db-conformance.md:24-26 sets the DB-AT-001 parity contract (correlation ≥0.99, RMSE thresholds once data exists), so a skip-aware scaffold accelerates later enforcement.
- docs/spec-db-tracing.md:10-26 requires trace-ready harness utilities; even the minimal test must respect trace workflow scaffolding.
- docs/TESTING_GUIDE.md:62-77 keeps DB_AT_001/002 marked Planned pending implementation; documenting the new manifest prevents drift.
- docs/development/TEST_SUITE_INDEX.md:18-36 mirrors selector status and artifact expectations, so new collect-only logs must slot into that registry.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE before any pytest invocation; keep NANOBRAGG_DISABLE_COMPILE=1 ready if grad utilities surface.
- export ART=plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z; mkdir -p "$ART" tests/fixtures/parity
- Create manifest template via `python -m scripts.generate_manifest_stub tests/fixtures/parity > "$ART/manifest_template.json"` (author stub script in loop) so checksum fields exist even without data.
- Implement loader utilities under `tests/fixtures/parity_loader.py` (or similar) and surface pytest fixture `parity_dataset_or_skip` that reads the manifest template, enforces `[panel, slow, fast]` ordering metadata when populated, and skips with reason `parity dataset unavailable` until data arrives.
- Author `tests/dbex/test_db_at_001_parity.py` targeting the new fixture and verifying manifest presence + skip reason; capture log via `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001 | tee "$ART/pytest_DB_AT_001.log"` and collection via `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001 | tee "$ART/collect_DB_AT_001.log"`.
- Re-run baseline guard `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_smoke.py | tee "$ART/pytest_smoke.log"` and collect-only `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_smoke.py | tee "$ART/collect_smoke.log"` to keep docs selectors honest.
- Update docs/fix_plan.md Attempts History with Metrics:/Artifacts:, dropping references to $ART as evidence for A1-A4.
Pitfalls To Avoid:
- Avoid introducing placeholder binary data; keep the manifest template empty of tensors until the dataset lands.
- Maintain `[panel, slow, fast]` ordering metadata within the template so future datasets align with bridge assumptions.
- Ensure manifest template generation is deterministic; sort field names and include schema version to prevent churn.
- Preserve existing smoke fixtures—new parity helpers must not mutate shared state in dbex/tests.
- Avoid editing external mirrors (`dials/`, `dxtbx/`, `cctbx_project/simtbx/`); store new data under `tests/fixtures/` only.
- Keep DB_AT_001 selector marked Planned until correlation thresholds are enforced; note interim status in docs.
- Verify new scripts/tests import locally (no `sys.path` hacks); rely on editable install per AGENTS.md.
- Capture artifacts in $ART to satisfy ledger policy before updating Attempts History.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001 | tee $ART/collect_DB_AT_001.log` — Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with manifest template + skip rationale (status remains Planned until thresholds met).
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_smoke.py | tee $ART/collect_smoke.log` — Reconfirm existing Active selector evidence and append log paths in both docs if filenames change.
If Blocked: If the golden dataset cannot be mirrored or generated, record the failure mode in $ART/notes_phase_a.md, add a blocking Attempts History entry with Metrics:/Artifacts: placeholders in docs/fix_plan.md, and mark PARITY-HARNESS-002 as blocked with the dependency (e.g., awaiting upstream dataset) noted in galph_memory.md.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Plan reinforces DB_AT selector contracts and documents environment flag usage per spec.
- DIAGNOSTICS-001 — Artifact capture (manifest template, skip logs) aligns with diagnostics expectations for reproducible parity debugging.
- TESTING-003 — Collect-only commands and artifact logging keep selector documentation synchronized with actual pytest collection results.
- GEOMETRY-001 — Loader template enforces pixel pitch and `[panel, slow, fast]` ordering metadata, preserving geometry guardrails from bridge work.
