Summary: Kick off Phase B by implementing a reusable ROI scoring helper (Nelder–Mead + `roiCheck`) plus unit tests so we can migrate `write_torch_outputs` to typed payloads next loop without changing writer behavior yet.
Mode: none
InitiativeType: architecture
Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split
Branch: integration
Mapped tests:
- pytest -q tests/dbex/test_roi_analysis.py
- KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/

Do Now:
- Implement: dbex/io/roi_scoring.py::score_roi_payloads — Add a new helper module that depends on `dbex/io/roi_analysis.py`. Accept full-detector `target`, `background`, `bragg`, ROI `pids/bbox`, and required floats `sigma_readout` + `sigma_floor` (both already in the run’s target units). Optionally accept an injected `roi_checker` instance and `log_fn` callable for per-ROI logging. Reuse `build_roi_payloads_from_arrays` to slice ROIs, run `scipy.optimize.minimize` with the same `roiCheck` objective the writer currently uses (optimize sqrt scale so `optimal_scale = result.x[0]**2`), coerce scores to `float`, and populate the returned `ROIAnalysisPayload` objects with `score`, `optimal_scale`, `model`, and `variance = max(model + sigma_readout**2, sigma_floor**2)` per docs/spec-db-core.md §§86-90. Keep imports local (no torch at module import time) and do not modify `write_torch_outputs` yet.
- Implement: tests/dbex/test_roi_analysis.py::<new tests> — Add a focused test module that (a) constructs a synthetic ROI where `data = background + k * bragg` and asserts `score_roi_payloads` recovers `optimal_scale ≈ k`, `score ≈ 1.0`, and the correct variance floor, and (b) verifies the optional `roi_checker`/`log_fn` hooks (e.g., pass a fake checker returning deterministic scores so you can assert logs and payload contents without hitting SciPy when desired). Keep fixtures numpy-only so the test runs quickly.
- Document: docs/architecture/dbex/io/writer.idl.md & docs/data_dependency_manifest.md — Promote the “future helper” notes to a concrete API description (signature, parameters, telemetry fields such as `roi_scoring_method`/`roi_checker`) and add a manifest entry describing the helper’s inputs (target/background/bragg, ROI metadata, sigma) and generated artifacts (payload list, log files). Note that writer still consumes raw arrays for now but the helper artifacts live in `plans/active/ARCH-BRIDGE-RESP-001/reports/.../`.
- Validate: Run the new ROI analysis test plus the existing CLI telemetry smoke to ensure no regressions, capturing logs in the artifacts directory (`pytest_roi_analysis.log`, `pytest_torch_writer_metadata.log`). Keep existing bridge tests untouched this loop.

How-To Map:
1. Helper: `mkdir -p dbex/io && $EDITOR dbex/io/roi_scoring.py` — create `score_roi_payloads` using `score_trainer.roi_check.roiCheck` + `scipy.optimize.minimize` (guard imports inside the helper), reusing `build_roi_payloads_from_arrays`, and expose it via `__all__`.
2. Tests: `mkdir -p tests/dbex && $EDITOR tests/dbex/test_roi_analysis.py` — add the two tests described above; inject a dummy checker/log function to avoid brittle assertions when verifying hooks.
3. Docs: Edit `docs/architecture/dbex/io/writer.idl.md` to add the helper signature/telemetry section and update the ROI entry in `docs/data_dependency_manifest.md` with the new helper inputs/outputs + artifact requirements.
4. Pytest/Artifacts: `pytest -q tests/dbex/test_roi_analysis.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/pytest_roi_analysis.log` and `KMP_DUPLICATE_LIB_OK=TRUE pytest -q tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/pytest_torch_writer_metadata.log`.

Pitfalls To Avoid:
- Do not change `dbex/io/writer.py` signature, CLI wiring, or HDF5 schema yet; the helper must be unused outside tests until the next loop.
- Keep helper imports local so importing `dbex.io.roi_scoring` stays lightweight (Environment Freeze).
- Always coerce scores to `float` (TORCH-CLI-004) and enforce `variance = max(model + sigma_readout^2, sigma_floor^2)` to satisfy PHYSICS-LOSS-001/002.
- Ensure helper returns new payload objects without mutating caller-provided arrays; rely on numpy slicing only.
- Tests must not rely on GPU/torch tensors; use pure numpy fixtures so they run quickly under pytest -q.

If Blocked:
- If `score_trainer.roi_check` or SciPy is unavailable in this environment, capture the exact ImportError/exception in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/blocker.log`, note the failure in docs/fix_plan.md + galph_memory, and stop—do not replace the helper with a partial implementation.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — New helper must preserve the existing `/torch_diagnostics` schema by feeding the same score/scale semantics once adopted.
- PHYSICS-LOSS-001 & PHYSICS-LOSS-002 — Variance must follow `V = max(I_model + sigma_readout^2, sigma_floor^2)` with provenance recorded for sigma inputs.

Pointers:
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md:1 — Phase B checklist + compliance matrix (current focus is B1).
- dbex/io/roi_analysis.py:1 — Existing dataclasses/helper to reuse when building the scorer.
- dbex/io/writer.py:1 — Reference implementation of the current inline scoring (match math without touching this file).
- docs/architecture/dbex/io/writer.idl.md:1 — Update the ROI helper section with the concrete API and telemetry notes.
- docs/data_dependency_manifest.md:1 — Manifest entry for ROI analysis helpers; extend it with the new scoring helper requirements.
