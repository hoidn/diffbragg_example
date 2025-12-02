Summary:
- Consume the pre-scored ROI payloads inside the torch writer so ROI scoring lives entirely in the helper while keeping `/torch_diagnostics` schema and variance telemetry unchanged.

Mode: Parity

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/

Do Now:
- Implement: dbex/io/writer.py::write_torch_outputs — remove the inline Nelder–Mead loop, require non-None `roi_payloads`, populate the score/scale/data/model/variance datasets directly from each `ROIAnalysisPayload`, and add `/torch_diagnostics` attrs (`roi_scoring_method="nelder_mead"`, `roi_checker="score_trainer.roi_check.roiCheck"`). Keep the existing dataset names/shape semantics and still emit the sigma_reference datasets so DIAGNOSTICS-001 stays intact.
- Implement: tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata (plus its ROI fixtures) — build a minimal `ROIAnalysisPayload` with populated `model`/`variance`, pass it to `write_torch_outputs`, and assert the new telemetry attrs exist. Make sure all CLI tests that patch `score_roi_payloads` keep passing typed payloads (no SciPy dependency) so the writer never sees `None`.
- Implement: docs/architecture/dbex/io/writer.idl.md & docs/data_dependency_manifest.md — document that Phase B requires `roi_payloads` (no inline scoring) and that the writer now records `roi_scoring_method`/`roi_checker` telemetry.
- Validate: run the targeted CLI + writer selectors and capture logs under the artifact directory:
  1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/pytest_cli_runs_simulator.log`
  2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/pytest_cli_calibration.log`
  3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/pytest_writer_metadata.log`

How-To Map:
1. In `dbex/io/writer.py`, assert `roi_payloads is not None`, iterate over each payload to collect the triptych arrays, precomputed `model`, `variance`, score, and optimal scale, and raise a descriptive error if any payload omits those fields. Drop the local `scipy.optimize` import entirely and keep the sigma datasets sourced from `sigma_readout_reference_value`. Add the two telemetry attrs once per run (strings) so downstream tools know which scoring path produced the numbers.
2. In `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`, construct a simple ROI payload via `ROITriptych`/`ROIAnalysisPayload` (np arrays are fine), pass `[payload]` into `write_torch_outputs`, and assert that `/torch_diagnostics` now exposes `roi_scoring_method == "nelder_mead"` and `roi_checker == "score_trainer.roi_check.roiCheck"` alongside the existing score/bragg datasets. Ensure the fixtures used by `test_nanobrag_backend_runs_simulator` and `test_nanobrag_backend_applies_calibration` still mock `score_roi_payloads` to return typed payloads with `model`/`variance` so the writer never tries to recompute variance.
3. Update `docs/architecture/dbex/io/writer.idl.md` to move the Phase B description into the normative contract (writer requires `roi_payloads`, no inline scoring) and add the new telemetry attrs; mirror the same state in `docs/data_dependency_manifest.md` so dependency consumers know the writer now depends on the scoring helper output rather than raw arrays.
4. Run the three pytest selectors, tee each output into the artifact directory, and record any new artifacts (e.g., updated HDF5 snippet) next to the logs. Review the logs to confirm the writer is consuming the payloads and that the CLI tests still detect the `roi_payloads` kwarg.

Pitfalls To Avoid:
- Do not leave a silent fallback path when `roi_payloads` is None; fail loudly so upstream wiring is fixed instead of reintroducing inline scoring.
- Keep dataset names and dtypes identical to the legacy writer so DIAGNOSTICS-001 remains satisfied—only the source of the arrays should change.
- Require `ROIAnalysisPayload.model` and `.variance`; if a payload lacks them, raise an actionable `ValueError` instead of recomputing them ad hoc.
- Maintain Environment Freeze: continue importing SciPy/score_trainer only inside `dbex/io/roi_scoring.py`, not in the writer module.
- Update every test fixture that touches the writer to pass real payloads; otherwise `test_torch_diagnostics_metadata` will fail with the new guard.
- When adding telemetry attrs, store simple strings (no complex objects) so HDF5 attribute serialization stays trivial.

If Blocked:
- If the writer still sees `roi_payloads=None` from an unexpected code path, capture the full stack trace plus the offending call signature, drop it into `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/blockers.md`, and update docs/fix_plan.md + this plan with the blocker summary before stopping work.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — Preserve the existing `/torch_diagnostics` schema while routing ROI data through typed payloads and recording the scoring method explicitly.
- PHYSICS-LOSS-001 — Keep the variance arrays used for ROI datasets aligned with the canonical `V = max(I_model + sigma_readout^2, sigma_floor^2)` definition supplied by the helper.
- PHYSICS-LOSS-003 — Ensure stage telemetry continues to carry the spec-defined chi-squared/variance mix; the writer must not change how those metrics are serialized while swapping data sources.

Pointers:
- docs/architecture/dbex/io/writer.idl.md:1 — authoritative writer contract and ROI payload requirements.
- docs/data_dependency_manifest.md:112 — ROI analysis + writer dependency entries that need updating alongside the code.
- dbex/io/writer.py:1 — current inline scoring implementation slated for removal during Phase B.3.
- tests/dbex/test_refine_one_cli.py:111 — CLI tests that patch `score_roi_payloads` and the metadata test that exercises the real writer.

Next Up:
- Once Phase B.3 passes, plan Phase B.4 to refresh the pytest collect-only logs and sync the test registry if selector names changed.
