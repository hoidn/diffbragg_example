Summary: Recover DB-AT-010 gradcheck by repairing the crystal override gradient path and revalidating the selector.
Mode: Parity
Focus: DB-AT-010 — Gradient correctness guard (regression recovery)
Branch: integration
Mapped tests:
- tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a
- tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck
Artifacts: plans/active/DB-AT-010/reports/2025-11-04T232350Z/
Do Now:
- DB-AT-010: Implement: dbex/nanobrag_bridge.py::simulate_forward_torch — keep `crystal_overrides` tensors differentiable end-to-end (patch any scalar coercion before TorchCrystal) and tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a — add regression guard/asserts ensuring the override tensor stays attached. Validate: env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010; env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1. Artifacts: plans/active/DB-AT-010/reports/2025-11-04T232350Z/.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBAT010_ARTIFACT_DIR=plans/active/DB-AT-010/reports/2025-11-04T232350Z
3. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010 | tee "$DBAT010_ARTIFACT_DIR/collect_db_at_010.log"
4. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --maxfail=1 --durations=1 | tee "$DBAT010_ARTIFACT_DIR/pytest_db_at_010_cell_a.log"
5. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1 --durations=1 | tee "$DBAT010_ARTIFACT_DIR/pytest_db_at_010_wrapper.log"
6. If gradients still mismatch, insert temporary `print` / `torch.autograd.grad` probes inside dbex/nanobrag_bridge.py::simulate_forward_torch (guarded by `if crystal_overrides:`) and capture the snippet/output in `$DBAT010_ARTIFACT_DIR/override_probe.txt` (remove before committing).
Pitfalls To Avoid:
- Keep override tensors on the same device/dtype (`torch.as_tensor` or `.to`)—no implicit CPU copies.
- Do not introduce `.item()`/`.numpy()` anywhere on differentiable tensors (GRADIENT-001).
- Retain SCALE-001/002 semantics; do not reorder scaling or mutate HKL grids while debugging.
- Ensure `NANOBRAGG_DISABLE_COMPILE=1` is set before importing torch; otherwise gradcheck will flake.
- Avoid widening scope to other acceptance tests—stay on DB-AT-010 until the regression clears.
- Preserve existing detector/beam overrides and masks; do not shortcut via new fixtures.
- Drop any debugging prints before final diff; keep artifact logging in reports only.
- No environment/package changes (Environment Freeze).
If Blocked: Capture the exact gradcheck traceback plus any probe output into `$DBAT010_ARTIFACT_DIR/blocked.md`, update docs/fix_plan.md Attempts History with the failure signature, set galph_memory state=blocked for DB-AT-010, and coordinate on upstream dependencies before retrying.
Findings Applied (Mandatory):
- RUNTIME-001 — Always run gradient tests with `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference.
- SCALE-001 — Leave structure factors unscaled prior to the simulator; overrides must respect this contract.
- SCALE-002 — Apply sqrt spot-scale inside torch to keep gradients differentiable (no numpy intermediates).
- GRADIENT-001 — Never detach override tensors; rely on tensor-aware helpers in the bridge.
Pointers:
- dbex/nanobrag_bridge.py:1101 — `simulate_forward_torch` override path to audit for tensor coercion.
- tests/dbex/test_gradients.py:190 — Gradcheck cell_a test invoking the override path.
- docs/TESTING_GUIDE.md:70 — DB_AT_010 selector commands and environment guards.
- docs/development/testing_strategy.md:340 — Gradcheck methodology and tolerances.
- docs/findings.md:31 — GRADIENT-001 guardrail against `.item()` detaches.
- plans/active/DB-AT-010/implementation.md:32 — Phase D checklist for the regression recovery loop.
Next Up (optional): Audit whether other unit-cell overrides (cell_b/c) need the same guard once cell_a passes.
