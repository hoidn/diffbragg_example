# TORCH-CLI-004 — Torch diagnostics ROI score coercion

## Purpose
Ensure the nanobrag CLI writes deterministic ROI diagnostics by coercing mocked/alternate ROI scores to numeric scalars and guarding empty-ROI aggregation, unblocking `test_torch_diagnostics_metadata` and stabilizing telemetry output.

## References
- Failure log: `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_full_suite.log`
- Code under test: `dbex/refine_one.py::_write_torch_outputs`
- Test suite: `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- Spec shards: `docs/spec-db-tracing.md` §2 (diagnostics payload), `docs/spec-db-workflow.md` §4 (ROI scoring semantics)

## Exit Criteria
1. `_write_torch_outputs` coerces ROI scores to `float` (or `np.nan` with guard) before aggregation and dataset emission, preventing `Mock` objects from propagating into diagnostics.
2. Aggregation handles empty `scores` gracefully (skip mean/std/fraction or emit explicit zero/nan with warning) without raising `ZeroDivisionError` or `RuntimeWarning` cascades.
3. `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` passes with mocks; targeted pytest + collect-only logs captured under `plans/active/TORCH-CLI-004/reports/<timestamp>/`.
4. Ledger synchronized: `docs/fix_plan.md` Attempts History updated; `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` remain accurate (note test stability if changed).

**Status:** done
**Completed:** 2025-11-04T222435Z (implementation), 2025-12-08T100000Z (checklist sync via TORCH-CLI-BRIDGE-ROLLUP-001)

## Phase Breakdown

- **Phase A — Reality check & guard design**
  - [x] A1: Reproduce failure (`pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`) to confirm TypeError signature; archive log.
  - [x] A2: Inspect `_write_torch_outputs` to map score aggregation points and determine coercion strategy (float casting, fallback for NaN, empty ROI guard).
  - [x] A3: Draft patch approach + test assertion updates; record in report summary.

- **Phase B — Implementation & tests**
  - [x] B1: Update `_write_torch_outputs` to coerce ROI scores, guard empty collection, and emit consistent diagnostics (including prints).
  - [x] B2: Extend `test_torch_diagnostics_metadata` to assert absence of TypeError and verify new aggregation behavior (e.g., fraction well-modeled equals expected value for mocked score).
  - [x] B3: Run targeted pytest + collect-only; capture logs under `plans/active/TORCH-CLI-004/reports/<timestamp>/`.

- **Phase C — Documentation & ledger sync**
  - [x] C1: Update `docs/fix_plan.md` Attempts History with metrics/artifacts; mark initiative status appropriately.
  - [x] C2: Confirm `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md` entries remain accurate (note improved diagnostics guard if needed); update if behavior description changes.
  - [x] C3: Append summary to `galph_memory.md` and archive new artifacts.

## Artifacts Index
- Working directory: `plans/active/TORCH-CLI-004/`
- Reports: `plans/active/TORCH-CLI-004/reports/<timestamp>/`
