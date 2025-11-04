# DB-AT-010 — Gradient Correctness Guard

## Phase A — Evidence & Harness Design
- [ ] A1: Confirm canonical assets (refGeom.expt/refl, scaled.mtz, 747_mask.pkl) load via `DataLoad` on current checkout; capture shapes/ROI counts for gradcheck reproducibility (`plans/active/DB-AT-010/reports/<ts>/summary.md`).
- [ ] A2: Audit `dbex.nanobrag_bridge` helpers (`prepare_refinement_inputs`, `simulate_forward_once`, `build_structure_factor_grid`) for gradient preservation; document required refactors (torch return path, sqrt spot scale handling, masked MSE helper).
- [ ] A3: Draft gradcheck coverage matrix listing required parameters (crystal cell_a/cell_gamma, detector distance_mm, beam wavelength_A, model fluence/spot scale) with expected tolerances, dtype/device guards, and environment prerequisites (`NANOBRAGG_DISABLE_COMPILE=1`).

## Phase B — Implementation & Tests
- [ ] B1: Implement differentiable forward helper (e.g., `simulate_forward_once` torch mode) returning torch tensors with retained graph and masked MSE loss utility honoring SCALE-001/002 and RUNTIME-001.
- [ ] B2: Author `tests/dbex/test_gradients.py` `TestDB_AT_010_Gradcheck` suite with fixtures enforcing compile guard, parameterized gradcheck tests, and JSON metrics emission under `$DBAT010_ARTIFACT_DIR`.
- [ ] B3: Ensure tests expose selectors (`pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck` and `pytest --collect-only tests -k DB_AT_010`), capturing logs in report directory and verifying gradcheck tolerances (eps/atol/rtol) per testing_strategy.md §4.1.

## Phase C — Validation & Documentation
- [ ] C1: Run targeted and full-suite pytest commands with `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAGG_DISABLE_COMPILE=1`; archive stdout/stderr logs and metrics JSON in `plans/active/DB-AT-010/reports/<ts>/`.
- [ ] C2: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to promote DB_AT_010 selector (command, env flags, artifact paths, expected runtime) per TESTING-003; cross-reference findings (RUNTIME-001, SCALE-001/002).
- [ ] C3: Append fix_plan Attempts History with metrics summary, confirm selector Active (>0 tests collected), and log durable lessons in `docs/findings.md` if new gradient guardrails arise.
