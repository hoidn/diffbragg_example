Summary: Extract `_write_torch_outputs` into `dbex/io/writer.py` so the torch backend uses a shared writer module and CLI/tests continue to emit `/torch_diagnostics` with the canonical schema.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz; pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/
Do Now:
- Implement: dbex/io/writer.py::write_torch_outputs — create `dbex/io/` with `__init__.py`, move the existing `_write_torch_outputs` body into a reusable `write_torch_outputs` function, keep ROI datasets/variance math/`/torch_diagnostics` serialization identical, and document the module per Phase C.2 plan.
- Implement: dbex/refine_one.py::run_nanobrag_backend — import the new writer module, drop the inline helper (or leave a one-line proxy that delegates), and ensure CLI calls still pass `hkl_telemetry`, sigma provenance, and stage telemetry dicts unchanged.
- Implement: tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata — update direct imports and every `@patch('dbex.refine_one._write_torch_outputs')` to reference `dbex.io.writer.write_torch_outputs`, keeping telemetry mocks intact so the shared module is exercised.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz > plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/collect_cli_refined_writer.log`.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/pytest_cli_refined_writer.log`.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata > plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/collect_cli_torch_diag.log`.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/pytest_cli_torch_diag.log`.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z` to pin artifact locations; all subsequent commands capture logs in that directory.
2. Copy `_write_torch_outputs` from `dbex/refine_one.py` into `dbex/io/writer.py`, keeping helper closures (`_coerce_scalar`, ROI score coercion, JSON serialization) intact; import stdlib deps locally (h5py, numpy, scipy, score_trainer) just as the CLI currently does.
3. Replace the inline helper in `dbex/refine_one.py` with `from dbex.io.writer import write_torch_outputs` (optionally provide `_write_torch_outputs = write_torch_outputs` for legacy callers) and update the `run_nanobrag_backend` call site to invoke the shared function.
4. Search for `_write_torch_outputs` usage (e.g., `rg -n "_write_torch_outputs" tests/dbex/test_refine_one_cli.py`) and update every patch/import to point at `dbex.io.writer.write_torch_outputs`; ensure fixtures still spy on the function via the new path.
5. Run the mapped selectors with collect-only first, then full pytest, using the env knobs above so the CLI harness stays deterministic; stash all logs in the artifacts directory.
Pitfalls To Avoid:
- Preserve every dataset/attribute name under `/torch_diagnostics`; no schema drift or field reordering (DIAGNOSTICS-001).
- Keep ROI scoring prints and variance computations identical (score coercion, sigma floor math) to avoid altering operator-facing metrics.
- Do not touch diffBragg writer paths or `_generate_triptych_report`; this loop only relocates the torch writer.
- Maintain lazy imports to avoid circular dependencies (especially `score_trainer`); new module should not import heavy torch code at import time.
- Respect Environment Freeze (POLICY-001); no package installs or pip edits.
- When updating tests, keep mocks returning real floats so `numpy` comparisons continue to work.
- Ensure the new `dbex/io/` package has `__init__.py` so import discovery works in both CLI and tests.
- Continue writing artifacts to `plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/`; do not overwrite prior logs.
If Blocked:
- Capture the failing collect/pytest log into the artifacts directory (e.g., `blocked_cli_writer.log`), note the stack trace plus hypothesis in docs/fix_plan.md Attempts History and galph_memory.md, then pause for supervisor guidance.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` schema must stay byte-for-byte compatible; validate via CLI tests.
- PHYSICS-LOSS-001 / PHYSICS-LOSS-003 — sigma provenance + variance-weighted chi² fields in RefinementTelemetry must continue flowing through the writer.
- ARCH-ENGINE-003 — shared RefinementTelemetry enrichment depends on a single serialization path; the new module must consume the canonical dataclass without reintroducing monolith imports.
Pointers:
- docs/architecture/live_backend.md:23 — states the torch backend must migrate to `dbex/io/writer.py`.
- docs/spec-db-workflow.md:33 — outlines the RefinementEngine/telemetry contract the writer must honor.
- docs/TESTING_GUIDE.md:119 — CLI diagnostics selector instructions (env vars + artifact policy).
- docs/data_dependency_manifest.md:52 — confirms Stage B/C assets already exist; CLI tests remain hermetic.
Next Up (optional): Phase C.3 — extract shared loss/physics helpers once the writer module exists.
Doc Sync Plan (Conditional): none — no new selectors added.
Mapped Tests Guardrail: Collect-only for both CLI selectors must report ≥1 test before running full pytest; if either collects 0, stop, log the evidence, and mark the loop blocked.
