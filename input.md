Summary: Recast DB_AT_001 around the forward-equivalence smoke test and outline evidence capture for DiffBragg vs torch forward comparisons.
Mode: TDD
Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_smoke.py
Artifacts: plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/
Do Now:
1. FORWARD-EQUIV-001 (docs/spec-db-conformance.md; plans/nanobrag_integration_plan.md §Phase 1) — Catalogue required metrics/overlays for the forward equivalence smoke (ROI correlation, localization stats, optional residual visuals) and record notes in $ART/forward_equiv_requirements.md (tests: none).
2. FORWARD-EQUIV-001 — Draft a minimal pytest scaffold (`tests/dbex/test_forward_equivalence.py`) that orchestrates DiffBragg + torch forward passes via existing helpers, capturing coarse ROI metrics without refinement and optional trace/config dumps per `docs/forward_equivalence.md`; tee dry-run output to $ART/pytest_forward_equiv.log.
3. FORWARD-EQUIV-001 — Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the new selector details (forward_equiv/) and ensure docs/spec-db-conformance.md references the updated expectations; summarize doc changes in $ART/doc_sync.md.
4. TORCH-BRIDGE-001 — Re-run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_smoke.py | tee $ART/pytest_smoke.log` to confirm bridge smoke remains green after forward-equivalence scaffolding lands.
Priorities & Rationale:
- plans/nanobrag_integration_plan.md:80-120 defines the forward equivalence smoke thresholds (median ROI correlation ≥0.2, localized peaks); A1-A3 translate them into actionable selectors.
- docs/spec-db-conformance.md:18-40 now centers on the forward equivalence profile, so documentation must reflect the updated expectations.
- docs/spec-db-tracing.md:10-26 requires trace-ready harness utilities; even the minimal test must respect trace workflow scaffolding.
- docs/TESTING_GUIDE.md:62-77 keeps DB_AT_001/002 marked Planned pending implementation; documenting the new manifest prevents drift.
- docs/development/TEST_SUITE_INDEX.md:18-36 mirrors selector status and artifact expectations, so new collect-only logs must slot into that registry.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE before any pytest invocation; keep NANOBRAGG_DISABLE_COMPILE=1 ready if grad utilities surface.
- export ART=plans/active/FORWARD-EQUIV-001/reports/$(date -u +%Y-%m-%dT%H%M%SZ); mkdir -p "$ART"
- Use the legacy DiffBragg CLI (`python -m dbex.refine_one ...`) to capture forward-only outputs without refinement; stash resulting HDF5/CSV references under `$ART/legacy_forward/`.
- Prototype torch forward call via a small script (e.g., `python -m scripts.forward_equiv_smoke`) that hydrates the bridge inputs, runs a single `sim.run()`, and writes metrics JSON plus optional overlays/trace logs to `$ART/torch_forward/` per `docs/forward_equivalence.md`.
- Implement pytest scaffold in `tests/dbex/test_forward_equivalence.py`; capture log via `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001 | tee "$ART/pytest_forward_equiv.log"` and collect-only output to `$ART/collect_forward_equiv.log`.
- Re-run baseline guard `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_smoke.py | tee "$ART/pytest_smoke.log"` and collect-only `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_smoke.py | tee "$ART/collect_smoke.log"` to keep docs selectors honest.
- Update docs/fix_plan.md Attempts History with Metrics:/Artifacts:, dropping references to $ART as evidence for A1-A4.
Pitfalls To Avoid:
- Avoid re-using golden datasets or storing legacy parity assets; rely on live forward simulations for comparisons.
- Maintain `[panel, slow, fast]` ordering assumptions when stitching torch outputs before metric computation.
- Ensure metric computation uses coarse thresholds (correlation ≥0.2) and records diagnostics when values fall below expectations.
- Preserve existing smoke fixtures—new parity helpers must not mutate shared state in dbex/tests.
- Avoid editing external mirrors (`dials/`, `dxtbx/`, `cctbx_project/simtbx/`); store new data under `tests/fixtures/` only.
- Keep DB_AT_001 selector marked Planned until correlation thresholds are enforced; note interim status in docs.
- Verify new scripts/tests import locally (no `sys.path` hacks); rely on editable install per AGENTS.md.
- Capture artifacts in $ART to satisfy ledger policy before updating Attempts History.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests -k DB_AT_001 | tee $ART/collect_forward_equiv.log` — Keep docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md aligned with the forward-equivalence selector details.
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_smoke.py | tee $ART/collect_smoke.log` — Reconfirm existing Active selector evidence and append log paths in both docs if filenames change.
If Blocked: If the golden dataset cannot be mirrored or generated, record the failure mode in $ART/notes_phase_a.md, add a blocking Attempts History entry with Metrics:/Artifacts: placeholders in docs/fix_plan.md, and mark PARITY-HARNESS-002 as blocked with the dependency (e.g., awaiting upstream dataset) noted in galph_memory.md.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Plan reinforces DB_AT selector contracts and documents environment flag usage per spec.
- DIAGNOSTICS-001 — Artifact capture (forward-equivalence overlays and metrics) aligns with diagnostics expectations for reproducible physics comparisons.
- TESTING-003 — Collect-only commands and artifact logging keep selector documentation synchronized with actual pytest collection results.
- GEOMETRY-001 — Loader template enforces pixel pitch and `[panel, slow, fast]` ordering metadata, preserving geometry guardrails from bridge work.
