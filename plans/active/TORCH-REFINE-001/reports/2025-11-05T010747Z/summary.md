### Turn Summary
Confirmed the Stage A smoke currently trips on numpy masks in the LBFGS path, captured failing pytest output, and set up a ready-for-implementation Do Now targeting the tensor conversion fix.
Diffed against the zero-iteration bridge to pinpoint the missing mask coercion and logged collect-only evidence under the new report directory.
Next: convert panel masks to torch tensors inside `run_nanobrag_refinement`, rerun the refinement smoke/CLI tests, and snapshot `/torch_diagnostics` telemetry.
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T010747Z/ (collect_refine_smoke.log, pytest_refine_smoke_fail.log)

Micro probes:
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_loss_decreases` → collected 1 test (Stage A smoke selector).
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1` → failed with `AttributeError: 'numpy.ndarray' object has no attribute 'to'` inside `nanobrag_torch.simulator.Simulator`.
