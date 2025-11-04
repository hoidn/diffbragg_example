Summary: Implement torch-preserving gradcheck helper + DB_AT_010 acceptance test with logs and metrics.
Mode: none
Focus: DB-AT-010 — Gradient correctness guard
Branch: integration
Mapped tests: tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck
Artifacts: plans/active/DB-AT-010/reports/2025-11-04T065717Z/{pytest_db_at_010.log,collect_db_at_010.log,gradcheck_metrics.json}

Do Now (hard validity contract)
- Focus Item: DB-AT-010
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once (add torch-return + masked loss helper) and tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck (new gradcheck selector).
- Validate: KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=plans/active/DB-AT-010/reports/2025-11-04T065717Z NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1
- Artifacts: plans/active/DB-AT-010/reports/2025-11-04T065717Z/{pytest_db_at_010.log,collect_db_at_010.log,gradcheck_metrics.json}

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBAT010_ARTIFACT_DIR=plans/active/DB-AT-010/reports/2025-11-04T065717Z && mkdir -p "$DBAT010_ARTIFACT_DIR"
3. export NANOBRAGG_DISABLE_COMPILE=1 && export KMP_DUPLICATE_LIB_OK=TRUE
4. Review plans/active/DB-AT-010/implementation.md and reports/2025-11-04T065345Z/summary.md for coverage matrix and helper requirements.
5. Refactor dbex/nanobrag_bridge.py::simulate_forward_once to optionally return torch tensors (no `.detach().numpy()` in grad mode) and add a torch masked-MSE loss helper honoring SCALE-001/002.
6. Implement tests/dbex/test_gradients.py (TestDB_AT_010_Gradcheck) with env guard fixture, gradcheck parameter coverage (crystal cell_a/cell_gamma, detector distance_mm, beam wavelength_A, model fluence or spot scale), and JSON metrics emission into "$DBAT010_ARTIFACT_DIR".
7. Run KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=$DBAT010_ARTIFACT_DIR NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1 | tee "$DBAT010_ARTIFACT_DIR/pytest_db_at_010.log"
8. Run DBAT010_ARTIFACT_DIR=$DBAT010_ARTIFACT_DIR NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010 | tee "$DBAT010_ARTIFACT_DIR/collect_db_at_010.log"
9. After success, update docs/TESTING_GUIDE.md and docs/development/TEST_SUITE_INDEX.md with selector details and artifact paths, then append Attempts History + findings references.

Pitfalls To Avoid
- Do not detach or convert gradients to NumPy in the gradcheck path; keep operations in torch.float64 (RUNTIME-001).
- Make SCALE-002 sqrt application differentiable (use torch operations) and avoid double scaling (SCALE-001/002).
- Ensure masks/targets move to the same device/dtype as simulator before loss computation (device neutrality).
- Guard tests with `pytest.skip` when canonical assets missing to avoid false failures.
- Keep metrics/JSON confined to "$DBAT010_ARTIFACT_DIR"; no stray files elsewhere.
- Use tight gradcheck tolerances (eps=1e-6, atol=1e-5, rtol≈5e-2) per testing_strategy.md §4.1.
- Mark any slow tests with `@pytest.mark.slow_gradient` and document expected runtime ceiling (905s) if needed.
- Preserve existing simulate_forward_once API for DB-AT-024 callers (default numpy behavior maintained).
- Synchronize selector docs only after pytest and collect-only logs exist (TESTING-003).
- Record new findings only if novel guardrails emerge; otherwise reference existing IDs.

If Blocked
- Capture failing command + traceback, archive under "$DBAT010_ARTIFACT_DIR", add blocked note to docs/fix_plan.md Attempts History, and log next steps in galph_memory.
- If nanobrag_torch import fails (environment freeze), halt implementation, document the ImportError signature, and mark focus blocked.

Findings Applied (Mandatory)
- RUNTIME-001 — Set NANOBRAGG_DISABLE_COMPILE=1 to prevent torch.compile interference with gradcheck.
- TESTING-003 — Collect-only proof and documentation sync before marking selector Active.
- SCALE-001 — Keep structure factors unscaled in forward helper; scaling handled post-sim.
- SCALE-002 — Apply sqrt(spot_scale_override) as differentiable torch op during masking loss.

Pointers
- docs/development/testing_strategy.md:338 — Gradcheck targets, tolerances, and env guard.
- docs/pytorch_runtime_checklist.md:7 — Runtime compile/disabling guidance for gradient tests.
- dbex/nanobrag_bridge.py:602 — Current simulate_forward_once detaches to NumPy (refactor target).
- nanoBragg/tests/test_gradients.py:1 — Reference implementation for gradcheck patterns.
- docs/spec-db-conformance.md:24 — Gradient-safe profile expectations (DB-AT-010, DB-AT-011).
- plans/active/DB-AT-010/implementation.md:1 — Phase checklist for this initiative.
- docs/TESTING_GUIDE.md:68 — Selector registry update location (will add DB_AT_010 row).

Next Up (optional)
- DB-AT-011 — Graph-break runtime guard once DB-AT-010 passes.

Doc Sync Plan (Conditional)
- After tests pass, run DBAT010_ARTIFACT_DIR=$DBAT010_ARTIFACT_DIR NANOBRAG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010, archive log, then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with selector status, commands, env flags, and artifact references before closing the loop.

Mapped Tests Guardrail
- Verify `pytest --collect-only tests -k DB_AT_010` reports ≥1 test; if it collects 0, author the missing test before finishing the loop.
