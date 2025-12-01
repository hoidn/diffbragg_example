Summary: Relocate the DB-AT-010 forward/loss helpers into `dbex.physics` so gradcheck exercises the shared physics layer instead of the bridge monolith.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests -k DB_AT_010; pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/
Do Now:
- Implement: dbex/physics/forward.py::simulate_forward_torch — create a physics-forward module that owns the gradcheck helper (lazy imports, tensor-valued overrides, ROI stacking) and replace the bridge definition with a thin re-export so tests no longer import the entire nanobrag bridge.
- Implement: dbex/physics/loss.py::compute_masked_mse_loss — move the variance-weighted chi-squared helper next to `_compute_variance_weighted_loss`, reuse its validation/clamp logic, and update `__all__`/bridge imports so all stages/tests share the same function.
- Implement: tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck — point fixtures at `dbex.physics.forward/loss`, keep float64 tensors + override dicts intact, and refresh docstrings so gradcheck users know the helpers moved under `dbex.physics`.
- Implement: docs/TESTING_GUIDE.md::DB_AT_010 entry — update the selector row to reference `dbex.physics.forward`/`dbex.physics.loss`, reiterate the float64 + NANOBRAGG_DISABLE_COMPILE guard, and keep findings/spec citations intact.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT010_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/db_at_010 pytest --collect-only tests -k DB_AT_010 > plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/collect_db_at_010.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT010_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/db_at_010 pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/pytest_db_at_010.log`
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `export DBAT010_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/db_at_010`; `mkdir -p "$DBAT010_ARTIFACT_DIR"` plus the parent report directory before editing.
2. Copy `simulate_forward_torch` from `dbex/nanobrag_bridge.py` into `dbex/physics/forward.py`, wrap it with the existing docstring/spec references, keep lazy imports, and replace the bridge definition with `from dbex.physics.forward import simulate_forward_torch`.
3. Move `compute_masked_mse_loss` into `dbex/physics/loss.py`, reuse `_compute_variance_weighted_loss`, and update `dbex/physics/__init__.py` plus `dbex/nanobrag_bridge.py` to import the shared helper.
4. Update `tests/dbex/test_gradients.py` imports + fixtures to consume the new module path; adjust `docs/TESTING_GUIDE.md` so the DB-AT-010 entry cites `dbex.physics.forward/loss`.
5. Run the collect-only and full DB-AT-010 selectors with `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and capture logs under the report directory.
Pitfalls To Avoid:
- Do not call the new helpers from production LBFGS closures; they remain DB-AT-010 only.
- Preserve tensor-valued overrides (no `.item()` or numpy conversions) so gradcheck keeps differentiability.
- Keep lazy imports inside helper bodies to avoid boot-time nanobrag_torch costs.
- Maintain the existing variance/clamp semantics and error messages; no schema drift.
- Respect Environment Freeze (POLICY-001); no new dependencies or pip installs.
- Ensure DB-AT-010 still runs in float64 with `NANOBRAGG_DISABLE_COMPILE=1` set before importing torch.
- Update docs/tests atomically so selector descriptions match the new module paths.
- Do not delete bridge re-exports until downstream plans confirm nothing else imports them.
If Blocked:
- If DB-AT-010 cannot collect or fails due to missing data, log the error signature into `plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/blocked_db_at_010.log`, append the blocker details to docs/fix_plan.md Attempts History, and ping Galph for guidance before retrying.
Findings Applied (Mandatory):
- PHYSICS-LOSS-001 — shared variance-weighted loss must remain the single source used by Stage A/B/C and gradcheck.
- ARCH-FACTORY-001 — forward helpers may use `create_unified_simulator` but MUST NOT route optimization closures through the factory.
- RUNTIME-001 — DB-AT-010 stays float64-only with `NANOBRAGG_DISABLE_COMPILE=1` and strict gradcheck tolerances.
Pointers:
- docs/spec-db-core.md §§57-68 — variance-weighted chi-squared definition for `compute_masked_mse_loss`.
- docs/spec-db-workflow.md §§30-45 — forward helper + telemetry expectations for gradcheck utilities.
- docs/TESTING_GUIDE.md:132 — DB-AT-010 selector details (env vars, findings, metrics) to mirror in code/docs.
- docs/data_dependency_manifest.md §Sigma/Calibration Sources — canonical refGeom assets + sigma map requirements for DB-AT-010.
Next Up (optional): Phase C.4 documentation/test-registry sync once physics helpers migrate into `dbex.physics`.
Doc Sync Plan (Conditional): none — no new selectors added (only description updates).
Mapped Tests Guardrail: Ensure `pytest --collect-only tests -k DB_AT_010` reports the 5 gradcheck tests before running the full selector; capture the collect log even on failure.
