Summary: Plan helper + acceptance test for DB_AT_024 mapping consistency.
Mode: Parity
Focus: DB-AT-024 — Mapping consistency guard
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mapping_consistency.py -k DB_AT_024
Artifacts: plans/active/DB-AT-024/reports/2025-11-04T061500Z/{pytest_db_at_024.log,collect_db_at_024.log,mapping_metrics.json}

Do Now (hard validity contract)
- DB-AT-024
  - Implement: dbex/nanobrag_bridge.py::simulate_forward_once (new helper returning zero-iteration tensors + metadata)
  - Implement: tests/dbex/test_mapping_consistency.py::TestDB_AT_024::test_mapping_consistency
  - Validating pytest: KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=$DBAT024_ARTIFACT_DIR pytest -v tests/dbex/test_mapping_consistency.py -k DB_AT_024
  - Artifacts: plans/active/DB-AT-024/reports/2025-11-04T061500Z/{pytest_db_at_024.log,collect_db_at_024.log,mapping_metrics.json}

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/2025-11-04T061500Z && mkdir -p "$DBAT024_ARTIFACT_DIR"
3. Study plans/active/DB-AT-024/implementation.md (Phases A-C) and reports/2025-11-04T054053Z/summary.md for baseline metrics + references.
4. Refactor dbex/refine_one.py:141-247 to delegate zero-iteration work into new helper in dbex/nanobrag_bridge.py; helper should reuse prepare_refinement_inputs (line 70) and return target arrays, loss mask, panel slices, and sqrt(spot_scale) metadata without writing HDF5.
5. Update run_nanobrag_backend to call simulate_forward_once and keep existing diagnostics/HDF5 emission intact.
6. Implement tests/dbex/test_mapping_consistency.py using parity_loader.compute_parity_metrics (tests/fixtures/parity_loader.py:362) and write_parity_artifacts (line 512) to compute ROI correlation/localization vs data-background.
7. Ensure test writes mapping_metrics.json (and optional CSV) into "$DBAT024_ARTIFACT_DIR"; gate on canonical assets with skips referencing docs/TESTING_GUIDE.md §2.
8. Run KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=$DBAT024_ARTIFACT_DIR pytest -v tests/dbex/test_mapping_consistency.py -k DB_AT_024 | tee "$DBAT024_ARTIFACT_DIR/pytest_db_at_024.log"
9. Run pytest --collect-only tests -k DB_AT_024 | tee "$DBAT024_ARTIFACT_DIR/collect_db_at_024.log"
10. After tests pass, update docs/TESTING_GUIDE.md, docs/development/TEST_SUITE_INDEX.md, and docs/spec-db-conformance.md with new selector status/artifacts; log Attempt in docs/fix_plan.md and tighten findings if needed.

Pitfalls To Avoid
- Maintain ADU vs photon semantics (docs/spec-db-workflow.md) — do not double scale targets.
- Preserve loss mask polarity (MASKING-001); never invert trusted_mask when returning helpers.
- Do not bypass parity utilities; reusing compute_parity_metrics avoids drift.
- Keep helper deterministic (use CPU device, fixed ROI sampling order).
- Avoid writing new files outside artifact dir; no temp outputs under repo root.
- Environment freeze: no package installs or rebuilds.
- Ensure pytest selector remains deterministic—seed ROI sampling if randomness introduced.
- Collect-only must succeed (>0 tests) per TESTING-003 before closing loop.
- Ensure ValueError messages remain actionable per CONFORMANCE-001 when thresholds fail.
- Keep helper returning numpy arrays to ease JSON serialization (PARITY-001 guard).

If Blocked
- Capture failure signature (command, error) and add Attempts History row in docs/fix_plan.md with status=blocked.
- Archive logs under $DBAT024_ARTIFACT_DIR even on failure; note remediation ideas in summary.md.
- Ping supervisor via galph_memory next_action update with block rationale.

Findings Applied (Mandatory)
- CONFORMANCE-001 — selector env flag + actionable errors honored for DB_AT_024.
- TESTING-003 — collect-only verification and doc sync required.
- CONFIG-001 — reuse bridge config mapping when returning helper outputs.
- MASKING-001 — preserve expected loss-mask coverage semantics in metrics.
- SCALE-002 — retain sqrt(spot_scale_override) application within helper to keep parity with canonical tensors.
- PARITY-001 — leverage existing parity diagnostics for ROI metrics + artifact layout.
- POLICY-001 — no environment changes; document blockers instead.

Pointers
- docs/spec-db-conformance.md:43 — DB_AT_024 setup + thresholds.
- docs/forward_equivalence.md:46 — ROI correlation/localization definitions.
- docs/spec-db-tracing.md:10 — tracing + diagnostics policy.
- plans/active/DB-AT-024/implementation.md:1 — phased work breakdown.
- plans/active/DB-AT-024/reports/2025-11-04T054053Z/summary.md:1 — baseline notes & micro probes.
- dbex/refine_one.py:141 — current run_nanobrag_backend implementation to refactor.
- dbex/nanobrag_bridge.py:48 — RefinementInputs dataclass.
- dbex/nanobrag_bridge.py:70 — prepare_refinement_inputs helper to reuse.
- tests/fixtures/parity_loader.py:362 — compute_parity_metrics utility.
- tests/fixtures/parity_loader.py:512 — write_parity_artifacts helper.

Next Up (optional)
1. Once DB_AT_024 passes, revisit DB-AT-025 (runtime vectorization) backlog item if documented.

Doc Sync Plan (Conditional)
- After implementing DB_AT_024, run pytest --collect-only tests -k DB_AT_024 and archive log; update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md rows from Planned→Active with artifact path + env flags before closing loop.
