Summary: Restore DB-AT-010 gradcheck coverage by keeping differentiable tensors alive through the bridge helper.
Mode: Parity
Focus: DB-AT-010 — Gradient correctness guard (regression recovery)
Branch: integration
Mapped tests:
- tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck
- tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a
Artifacts: plans/active/DB-AT-010/reports/2025-11-04T225149Z/
Do Now:
- DB-AT-010: Implement: dbex/nanobrag_bridge.py::simulate_forward_torch — introduce a tensor-preserving override path for gradcheck inputs and update tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a to consume it (no `.item()`/`.numpy()` detaches). Validate: pytest --collect-only tests -k DB_AT_010; pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1. Archive logs in the artifact directory.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBAT010_ARTIFACT_DIR=plans/active/DB-AT-010/reports/2025-11-04T225149Z
3. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010 | tee "$DBAT010_ARTIFACT_DIR/collect_db_at_010.log"
4. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1 | tee "$DBAT010_ARTIFACT_DIR/pytest_db_at_010_wrapper.log"
5. If the wrapper still fails, rerun the focused case: env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --maxfail=1 | tee "$DBAT010_ARTIFACT_DIR/pytest_db_at_010_cell_a.log"
Pitfalls To Avoid:
- Do not call `.item()`/`.numpy()` on tensors that should retain gradients; rely on torch-native overrides.
- Keep SCALE-001/002 contracts intact—no premature scaling changes when threading overrides.
- Preserve existing simulator defaults (device, dtype) and keep overrides opt-in to avoid regressing other callers.
- Maintain `NANOBRAGG_DISABLE_COMPILE=1` for every gradcheck run; verify the env var before running pytest.
- Avoid introducing new dependencies or touching environment configuration (Environment Freeze).
- Ensure updated tests remain deterministic and reuse canonical assets; no random seeds without documentation.
- Leave MAP-SCALE selectors untouched; any telemetry adjustments belong to this initiative only if required for gradients.
- Keep doc ledgers accurate—if behavior stays the same, simply confirm existing entries rather than rewriting.
- Watch runtime: gradcheck is slow; use targeted selectors instead of full-suite runs for validation.
If Blocked: Capture the exact gradcheck traceback and offending parameter in a new `blocked.md` under the artifact path, update docs/fix_plan.md Attempts History with the failure signature, set galph_memory state=blocked for DB-AT-010, and coordinate on dependencies before reattempting.
Findings Applied (Mandatory):
- RUNTIME-001 — Enforce `NANOBRAGG_DISABLE_COMPILE=1` for reliable gradchecks.
- SCALE-001 — Keep structure factors unscaled while introducing overrides.
- SCALE-002 — Apply sqrt(spot_scale_override) inside torch so gradients remain differentiable.
- GRADIENT-001 — Never detach gradcheck tensors via `.item()`/`.numpy()`; use bridge helpers that preserve autograd graphs.
Pointers:
- dbex/nanobrag_bridge.py:1101 — `simulate_forward_torch` implementation to extend.
- tests/dbex/test_gradients.py:202 — `.item()` usage breaking the gradient graph.
- docs/development/testing_strategy.md:416 — Guidance on avoiding `.item()` in gradient flows.
- plans/active/DB-AT-010/implementation.md:31 — Phase D regression recovery checklist.
Next Up (optional): 1) Audit detector/beam override patterns once crystal overrides land, ensuring gradients propagate for distance and wavelength parameters without custom per-test patches.
