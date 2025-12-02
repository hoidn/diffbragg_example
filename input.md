Summary: Phase B.2 — route the CLI/engine path through `score_roi_payloads` so `write_torch_outputs` receives typed ROI payloads while keeping the legacy scoring loop alive for one more loop.
Mode: none
InitiativeType: architecture
Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/

Do Now:
- Implement: dbex/refine_one.py::run_nanobrag_backend — Import `score_roi_payloads`, derive sigma values in target units (`sigma_reference_target_units` fallback or mean of `inputs.sigma_readout`, and `sigma_floor` divided by gain when `--adu-per-photon` is set), convert `DataLoad.pids`/`bbox` to Python lists, call `score_roi_payloads` with the final `Bragg`, and pass the resulting list via a new `roi_payloads` keyword when invoking `write_torch_outputs`.
- Implement: dbex/io/writer.py::write_torch_outputs — Extend the signature/docstring with an optional `roi_payloads` parameter (default `None`) so callers can start threading typed payloads while the legacy optimization loop remains untouched this loop.
- Implement/Tests: tests/dbex/test_refine_one_cli.py::{test_nanobrag_backend_runs_simulator,test_nanobrag_backend_applies_calibration,...} — Patch `dbex.io.roi_scoring.score_roi_payloads` in nanobrag CLI tests to avoid running SciPy, assert that `write_torch_outputs` receives the helper output via the new `roi_payloads` kwarg, and update direct-writer tests (e.g., `test_torch_diagnostics_metadata`) to call the function with the new argument (passing `None` until B3 removes inline scoring).
- Document: docs/architecture/dbex/io/writer.idl.md & docs/data_dependency_manifest.md — Note that `write_torch_outputs` now accepts an optional `roi_payloads` list (Phase B.2) and record that `run_nanobrag_backend` executes `dbex.io.roi_scoring.score_roi_payloads`, including required inputs/artifacts for the helper.
- Validate: run the mapped pytest selectors, capturing `pytest_nanobrag_backend_runs_simulator.log`, `pytest_nanobrag_backend_applies_calibration.log`, and `pytest_torch_diagnostics_metadata.log` under the artifacts directory.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md mkdir -p plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z`
2. `$EDITOR dbex/refine_one.py` — import the helper and thread ROI payload creation before the writer call as described above (keep logging consistent with the existing score loop).
3. `$EDITOR dbex/io/writer.py` — add the optional `roi_payloads` parameter (defaulting to `None`) and mention it in the module docstring/IDL pointer without altering the current ROI scoring logic.
4. `$EDITOR tests/dbex/test_refine_one_cli.py docs/architecture/dbex/io/writer.idl.md docs/data_dependency_manifest.md` — update the nanobrag CLI tests with a `score_roi_payloads` patch + assertions, adjust existing direct writer invocations, and document the new data dependency/API knob.
5. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/pytest_nanobrag_backend_runs_simulator.log`
6. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/pytest_nanobrag_backend_applies_calibration.log`
7. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/pytest_torch_diagnostics_metadata.log`

Pitfalls To Avoid:
- Keep sigma conversions consistent: both `sigma_readout` and `sigma_floor` fed to `score_roi_payloads` must be in the same representation (photons vs ADU) as `Bragg`/`DL.data`.
- `score_roi_payloads` expects Python ints for ROI metadata; convert numpy scalars (`DL.pids`, `DL.bbox`) before passing them to avoid serialization/type surprises.
- Do not remove the legacy scoring loop from `write_torch_outputs` yet; Phase B.3 will delete it once payload plumbing is proven.
- Ensure nanobrag CLI tests patch `score_roi_payloads` so unit tests do not import SciPy/score_trainer or spend time in Nelder–Mead.
- When passing payloads to writer, keep the argument keyworded (`roi_payloads=...`) so downstream callers remain explicit and future refactors are straightforward.
- Updating docs must preserve DIAGNOSTICS-001 guarantees; do not promise behavioral changes (payload-only writer) until Phase B.3 lands.

If Blocked:
- If `score_trainer.roi_check` or SciPy cannot be imported when running `run_nanobrag_backend`, capture the exact ImportError/stack trace in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/blocker.log`, note it in docs/fix_plan.md + galph_memory, and stop rather than swapping in a partial scoring path.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — Keep `/torch_diagnostics` schema and ROI score semantics unchanged while threading the new payload.
- PHYSICS-LOSS-001/PHYSICS-LOSS-002 — Pass sigma inputs in the correct units so the helper’s `variance = max(I_model + sigma_readout^2, sigma_floor^2)` remains spec-compliant.

Pointers:
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md:70 — Phase B checklist (B1 complete, B2 now active).
- dbex/refine_one.py:13 — Current writer import + nanobrag backend where the helper must be threaded.
- dbex/io/writer.py:1 — Legacy ROI scoring loop that will start receiving `roi_payloads` (Phase B.3 will consume them).
- docs/architecture/dbex/io/writer.idl.md:117 — ROI helper/IDL section to update with the new optional argument.
- docs/data_dependency_manifest.md:187 — ROI analysis helper entry that now needs to record CLI usage.
- tests/dbex/test_refine_one_cli.py:110 — Primary nanobrag CLI test that should assert payload threading.

Next Up:
- Phase B.3 — remove the inline Nelder–Mead loop from `write_torch_outputs` and populate ROI datasets directly from the typed payloads once this plumbing proves stable.
