Summary: Hand off helper extraction + DB_AT_024 acceptance test with diagnostic artifacts.
Mode: none
Focus: DB-AT-024 — Mapping consistency guard
Branch: integration
Mapped tests: pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/DB-AT-024/reports/2025-11-04T070000Z/{pytest_db_at_024.log,collect_db_at_024.log,mapping_metrics.json,summary.md}

Do Now (hard validity contract)
- Focus Item: DB-AT-024
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once — extract the zero-iteration helper returning per-panel tensors + diagnostics and author `tests/dbex/test_mapping_consistency.py` (DB_AT_024 selector) to consume it with artifact logging and provisional xfail messaging until thresholds improve.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/2025-11-04T070000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
- Artifacts: plans/active/DB-AT-024/reports/2025-11-04T070000Z/{pytest_db_at_024.log,collect_db_at_024.log,mapping_metrics.json,summary.md}

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/2025-11-04T070000Z && mkdir -p "$DBAT024_ARTIFACT_DIR"
3. Review plans/active/DB-AT-024/implementation.md and reports/2025-11-04T063053Z/summary.md for baseline metrics + script usage.
4. Use plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py to sanity-check helper output (timeout 120 python … --artifact-dir "$DBAT024_ARTIFACT_DIR") before wiring pytest.
5. Refactor run_nanobrag_backend to delegate zero-iteration work to new helper while preserving HDF5 emission; ensure helper exposes `(bragg, inputs, diagnostics)` plus `global_scale_hint`.
6. Implement DB_AT_024 pytest: compute ROI metrics via tests/fixtures/parity_loader.py::compute_parity_metrics, write mapping_metrics.json (and CSV) into "$DBAT024_ARTIFACT_DIR", and mark the test xfail with measured thresholds + remediation note.
7. Run KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=$DBAT024_ARTIFACT_DIR pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee "$DBAT024_ARTIFACT_DIR/pytest_db_at_024.log"
8. Run DBAT024_ARTIFACT_DIR=$DBAT024_ARTIFACT_DIR pytest --collect-only tests -k DB_AT_024 | tee "$DBAT024_ARTIFACT_DIR/collect_db_at_024.log"
9. After tests pass, update docs/TESTING_GUIDE.md §2, docs/development/TEST_SUITE_INDEX.md, docs/spec-db-conformance.md, and docs/fix_plan.md Attempts History with artifact paths + findings.

Pitfalls To Avoid
- Keep helper device-neutral and disable torch.compile via NANOBRAGG_DISABLE_COMPILE=1 (RUNTIME-001).
- Do not rescale targets twice; use `global_scale_hint` only for diagnostic messaging (SCALE-002).
- Preserve loss mask polarity (MASKING-001) and return numpy arrays for artifact emission.
- Ensure pytest xfail reason cites current metrics instead of failing hard (CONFORMANCE-001 guidance).
- Gate test on canonical asset availability before running heavy simulation.
- Avoid writing outside "$DBAT024_ARTIFACT_DIR"; no temp artifacts in repo root.
- Maintain deterministic ROI ordering so metrics compare cleanly over time.
- Keep helper pure (no HDF5 writes) to avoid interfering with CLI workflows.

If Blocked
- Capture failure signature + command, archive logs in "$DBAT024_ARTIFACT_DIR", add blocked entry to docs/fix_plan.md, and note next steps in galph_memory.
- If helper import fails (missing nanobrag_torch), stop and record blocker—environment freeze prohibits installs.

Findings Applied (Mandatory)
- CONFORMANCE-001 — Selector must emit actionable diagnostics with env flag noted.
- TESTING-003 — Collect-only confirmation + doc sync required before marking Active.
- PARITY-001 — Reuse parity utilities for ROI diagnostics and artifact layout.
- DIAGNOSTICS-001 — Include metrics JSON within parity_harness-style structure.
- MASKING-001 — Loss mask coverage expectations inform assertions.
- CONFIG-001 — Maintain bridge-derived detector/beam configs inside helper.
- RUNTIME-001 — Disable torch.compile for deterministic CPU execution.

Pointers
- docs/spec-db-conformance.md:43 — DB_AT_024 acceptance contract.
- docs/forward_equivalence.md:48 — Correlation/localization definitions.
- docs/spec-db-tracing.md:10 — Artifact policy for diagnostics.
- docs/TESTING_GUIDE.md:68 — Selector registry and env flags.
- plans/active/DB-AT-024/implementation.md:1 — Phase breakdown.
- plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py:1 — Baseline probe script.
- plans/active/DB-AT-024/reports/2025-11-04T063053Z/summary.md:1 — Current metrics + context.
- dbex/refine_one.py:141 — run_nanobrag_backend entry point to refactor.
- dbex/nanobrag_bridge.py:48 — RefinementInputs definition + helper context.
- tests/fixtures/parity_loader.py:362 — compute_parity_metrics utility for ROI checks.

Next Up (optional)
- If helper/test land quickly, begin drafting scaling strategy to lift correlation above 0.2 for future loop.

Doc Sync Plan (Conditional)
- After test passes, run pytest --collect-only tests -k DB_AT_024 (logged to "$DBAT024_ARTIFACT_DIR/collect_db_at_024.log") and update docs/TESTING_GUIDE.md §2 + docs/development/TEST_SUITE_INDEX.md rows before flipping selector to Active.
