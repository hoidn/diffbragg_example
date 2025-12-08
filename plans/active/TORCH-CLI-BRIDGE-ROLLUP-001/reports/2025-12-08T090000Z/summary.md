### Turn Summary (Phase C Completion)
Fixed 3 failing CLI tests (MOCK-FIXTURE-001) by repairing multi-layered mock fixture issues: numpy→torch arrays, typed config helpers, hkl_metadata, patch targets, ROI scorer mocks.
Root cause was deeper than initial analysis: production code evolved (JobContext, Detector.__init__, score_roi_payloads) and test mocks hadn't been updated to match new interfaces.
All 15 CLI tests now pass; TORCH-CLI-003 implementation.md and Roll-up Phase C updated. Next: Phase D (TORCH-CLI-004 sync) or Phase E (closure).
Artifacts: plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z/ (pytest_cli.log, collect_cli.log)

---

## Detailed Changes

### Test Fixture Repairs (`tests/dbex/test_refine_one_cli.py`)

**Affected Tests:**
1. `test_nanobrag_backend_accepts_sigma_map`
2. `test_nanobrag_backend_accepts_external_lookup_sigma_map`
3. `test_nanobrag_backend_uses_refined_mtz`

**Issues Found & Fixed:**

| Issue | Root Cause | Fix |
|-------|------------|-----|
| `AttributeError: 'numpy.ndarray' object has no attribute 'device'` | Mock `build_structure_factor_grid` returned numpy arrays | Changed `np.zeros` to `torch.zeros` |
| `TypeError: unsupported operand type(s) for /: 'Mock' and 'Mock'` | Mock `create_detector_config` returned `Mock()` but `Detector.__init__` needs typed config | Used `_make_detector_config()` helper |
| `ValueError: hkl_metadata missing required key 'has_halo'` | Mock metadata dict incomplete | Added `"has_halo": False` to metadata |
| `AssertionError: Expected 'write_torch_outputs' to have been called once. Called 0 times.` | Patch at definition site not import site | Changed to `@patch('dbex.refine_one.write_torch_outputs')` |
| `TypeError: expected str, bytes or os.PathLike object, not Mock` | `args.report_dir` unset | Added `args.report_dir = None` |
| `ValueError: The user-provided objective function must return a scalar value.` | `score_roi_payloads` not mocked, scipy got Mock | Added `@patch('dbex.io.roi_scoring.score_roi_payloads')` with proper `ROIAnalysisPayload` return |

### Files Modified
- `tests/dbex/test_refine_one_cli.py` — Mock fixture repairs (MOCK-FIXTURE-001)
- `plans/active/TORCH-CLI-003/implementation.md` — Marked A0-A2, B1-B2 complete
- `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` — Phase C complete

### Test Results
```
15 passed, 4 warnings in 3.15s
```

---

### Turn Summary (Prior: Phase C Analysis)

Reviewed Phase B completion (TORCH-BRIDGE-001 closeout: 27 passed, 1 skip); discovered 3 CLI test failures in Phase C due to NumPy/torch mock mismatch.
Root cause identified: `test_nanobrag_backend_uses_refined_mtz` at line 793 uses `np.zeros` where `torch.zeros` is required — same MOCK-FIXTURE-001 pattern.
Next: Ralph fixes mock fixture at `test_refine_one_cli.py:793-796`, runs 15 CLI tests, marks TORCH-CLI-003 done.
Artifacts: plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T090000Z/ (input.md prepared)
