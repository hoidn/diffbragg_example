# FORWARD-EQUIV-002 Loop Summary — 2025-11-04T034834Z (planning)

## Problem Statement
Forward equivalence test `tests/dbex/test_forward_equivalence_complete.py` still fabricates DiffBragg and torch tensors via stub fixtures and force-xfails when metrics miss thresholds. With the real `nanobrag_torch` backend and canonical golden dataset now available (NANOBRAG-BACKEND-002 done), the selector should operate on production data and assert the DB-AT-001 acceptance thresholds instead of masking them behind xfails.

## Evidence Reviewed
- `tests/dbex/test_forward_equivalence_complete.py:68-194` defines stub fixtures (`stub_diffbragg`, `stub_torch`) and xfail logic keyed to synthetic metrics; artifacts still write to `FORWARD-EQUIV-001` paths.
- `docs/TESTING_GUIDE.md:64-86` documents the selector as stub-based, expects xfail, and references 2025-10-29 artifact paths.
- `docs/development/TEST_SUITE_INDEX.md:12-21` likewise calls out the stub simulator, outdated collection log, and old artifact directory.
- `docs/forward_equivalence.md:12-60` reiterates DB-AT-001 thresholds (correlation ≥0.2, localization ≥90%) and artifact expectations that we can now satisfy with canonical tensors from NANOBRAG-BACKEND-002 / NANOBRAG-GOLDEN-001.

## Plan Outline
1. **Promote harness to real data** — Replace stub fixtures with loaders from `tests/fixtures/parity_loader.py`, consume canonical DiffBragg + nanobrag tensors, and reuse `compute_parity_metrics` / `write_parity_artifacts` to avoid bespoke ROI logic.
2. **Tighten assertions & artifact wiring** — Remove unconditional xfail, point artifacts at `plans/active/FORWARD-EQUIV-002/reports/<timestamp>/forward_equiv/`, and assert DB-AT-001 thresholds using live metrics (correlation≈0.988, localization≈1.0).
3. **Documentation & registry sync** — Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` entries with new artifact paths, pass status, and canonical metrics; refresh `docs/fix_plan.md` Attempts History with run evidence once the selector passes.
4. **Validation** — Run targeted selector `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py::TestForwardEquiv::test_DB_AT_001_forward_equiv` plus `pytest --collect-only` for DB_AT_001, capturing logs under this report.

## Artifacts
- `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T034834Z/summary.md` (this file)
