Summary:
- Repair the two nanobrag CLI tests so they use real `DetectorConfig` snapshots and keep the Phase B.3 writer change green with the expected `/torch_diagnostics` telemetry.

Mode: Parity

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: main

Mapped tests:
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/

Do Now:
- Implement: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator — stop returning a bare `Mock` from `create_detector_config`; instead build a small helper that returns a real `nanobrag_torch.config.DetectorConfig` populated with deterministic `distance_mm`, `pixel_size_mm`, `beam_center_{s,f}`, `spixels/fpixels=100`, and a float32 torch `mask_array` matching the ROI shape. Keep the existing assertions that verify writer inputs but update them to operate on the typed config object.
- Implement: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration — reuse the same helper so the calibration-positive path also feeds a typed `DetectorConfig` with a real mask tensor; ensure any mask slicing or ROI adjustments mirror what the CLI would do and keep the mocks for `score_roi_payloads` returning fully-populated `ROIAnalysisPayload` objects.
- Refactor: if duplicated detector-fixture logic remains, factor it into a local `_make_detector_config(mask_shape=(slow, fast))` utility inside the test module to keep both selectors consistent and to guarantee the mask tensor shape always matches `spixels/fpixels`.
- Validate: run the mapped selectors with authoritative env flags and capture logs:
  1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/pytest_cli_runs_simulator.log`
  2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/pytest_cli_calibration.log`
  3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/pytest_writer_metadata.log`

How-To Map:
1. Add a fixture/helper inside `tests/dbex/test_refine_one_cli.py` that instantiates `DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=100, fpixels=100, beam_center_s=5.0, beam_center_f=5.0, detector_convention=DetectorConvention.DIALS, detector_pivot=DetectorPivot.BEAM, ...)` and sets `mask_array=torch.ones((slow, fast), dtype=torch.float32)` so `create_unified_simulator` can normalize masks without touching numpy→torch conversion edge cases.
2. Update both CLI tests to set `mock_detector_config.side_effect=lambda *args, **kwargs: make_detector_config()` (or similar) rather than assigning a `Mock`. Preserve the current guard assertions (`mask_array` dtype, values) but adapt them to inspect the concrete dataclass fields you just created.
3. Keep `score_roi_payloads` patched to return properly-initialized `ROIAnalysisPayload` objects so the writer still receives typed payloads; no changes should be necessary for the metadata test beyond re-running it to ensure the telemetry attrs remain present.
4. Execute the three pytest commands under the documented env flags, teeing the logs into the artifact directory so the supervisor can confirm the selectors now complete end-to-end with the Phase B.3 writer semantics.

Pitfalls To Avoid:
- Do not leave residual `Mock` attributes for `distance_mm` or `mask_array`; the detector config must be a real dataclass so future helpers can introspect it safely.
- Ensure the mask tensor shape equals `(spixels, fpixels)`; mismatches will throw inside `create_unified_simulator` before the writer telemetry assertions run.
- Keep ROI bbox semantics (`(x0, x1, y0, y1)` exclusive) intact when slicing masks for the helper so ROI/panel math stays canonical.
- Leave the writer code untouched this loop; focus strictly on the test fixtures so no additional production semantics change.
- Keep SciPy imports confined to `dbex/io/roi_scoring.py`; do not introduce new dependencies into the test module beyond `nanobrag_torch.config`.
- Maintain `KMP_DUPLICATE_LIB_OK=TRUE` on pytest invocations to avoid PyTorch runtime warnings.

If Blocked:
- If the typed DetectorConfig still causes `Detector` instantiation failures (missing pivot or convention), capture the exact exception, note which fields were access, and log the traceback plus helper definition into `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/blockers.md`, then update docs/fix_plan.md with the blocker summary.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — Keep `/torch_diagnostics` schema/telemetry untouched; the tests should verify writer attrs without mutating production code.
- PHYSICS-LOSS-001 / PHYSICS-LOSS-002 / PHYSICS-LOSS-003 — By feeding real detector configs and mask tensors into the simulation helper, the tests continue to enforce the canonical variance-weighted chi-squared path before asserting writer outputs.

Pointers:
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md:74 — Phase B.3 checklist now requires typed DetectorConfig fixtures before rerunning the selectors.
- docs/fix_plan.md:116 — Ledger attempts history describing the current CLI test failures and expected remediation.
- tests/dbex/test_refine_one_cli.py:180 — Location of the failing simulator smoke test that needs the typed config helper.
- problems.md:36 — Original ledger entry tying this work to the writer/bridge responsibility split initiative.

Next Up (optional):
- If time remains after the selectors pass, start drafting the Phase B.4 doc/test-registry update so the writer change is fully documented.
