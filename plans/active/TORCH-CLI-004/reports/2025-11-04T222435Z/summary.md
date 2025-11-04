# TORCH-CLI-004 — Torch diagnostics ROI score coercion (analysis)

## Context
- `pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` fails in the latest full-suite run (see `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_full_suite.log`).
- Failure trace: `_write_torch_outputs` attempts `sum([s >= 0.5 for s in scores])` where `s` is a `MagicMock`, because mocked ROI scoring returns non-scalar values.
- Resulting exception: `TypeError: '>=' not supported between instances of 'MagicMock' and 'float'` at `dbex/refine_one.py:449`.
- Additionally, `np.mean(scores)` emits `nan` diagnostics when `scores` is empty or contains non-numeric objects, masking real regressions.

## Immediate Findings
- The CLI metadata helper assumes ROI scores are plain floats; unit tests patch `score_trainer.roi_check` with mocks, exposing the lack of coercion/guards.
- Real pipelines still produce floats, but lack of explicit casting allows fragile behavior whenever mocks or alternate implementations are used.
- Guarding `CHECKER.score` results (and derivative aggregates) to concrete floats and handling the empty-ROI edge case will harden the CLI diagnostics path and unblock the test.

## Next Steps
- Define fix plan entry `TORCH-CLI-004` targeting `_write_torch_outputs` to coerce ROI scores to `float`, skip aggregation when `scores` is empty, and ensure the HDF5 payload remains numeric.
- Update associated tests to assert the new behavior (no TypeError, correct telemetry metadata, stable fractions for mocked scores).
- Capture targeted pytest + collect-only logs under a new report directory after implementation.
