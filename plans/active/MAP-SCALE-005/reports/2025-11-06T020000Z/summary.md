# MAP-SCALE-005 Planning Summary — 2025-11-06T020000Z

## Problem Statement
CLI runs currently accept `--refined-mtz` but silently fall back to raw `scaled.mtz` amplitudes when refined assets are missing or fail to load. The telemetry payload (`hkl_source`) records `"raw"`, yet execution continues with only a warning (`[nanobrag backend] WARNING: Could not load refined MTZ ... Falling back to raw MTZ`). This violates SCALE-007, which requires refined telemetry to be enforced so regressions that drop refined |F| usage fail immediately rather than rely on downstream acceptance tests.

## Evidence
- Code path: `dbex/refine_one.py:218-248` sets `hkl_source="refined"` only on successful `load_refined_mtz`. Any exception resets `hkl_source="raw"` and prints a warning before continuing with raw amplitudes.
- Telemetry emission: `_write_torch_outputs` persists the `hkl_telemetry` dict, so downstream diagnostics reflect the fallback but no runtime guard intervenes.
- Existing tests (`tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz`) mock the refined path but do not cover the failure case; there is no regression test ensuring a fatal error when refined ingestion fails.

## Proposed Guardrails
1. Treat refined MTZ load failures (missing file, parser error, ImportError) as hard errors: raise `RuntimeError` with actionable guidance instead of continuing.
2. After simulation, assert telemetry remains `hkl_source="refined"` when `--refined-mtz` was requested; downgrade to raw should also raise, preventing silent regressions.
3. Surface the guard via regression tests covering both success and failure paths, archiving artifacts under `plans/active/MAP-SCALE-005/reports/<timestamp>/`.

## Next Steps
- Update `docs/fix_plan.md` (done) and create implementation plan for MAP-SCALE-005 (done).
- Draft Do Now instructing Ralph to harden `run_nanobrag_backend`, add failure-path tests in `tests/dbex/test_refine_one_cli.py`, and update testing docs/registry.
- Coordinate new artifact directory for CLI guard evidence (failure stderr, pytest logs).

## Findings Applied
- SCALE-003, SCALE-004: refined structure factors + calibration are required for parity; CLI must not regress to raw inputs.
- SCALE-007: telemetry contract mandates failure if refined assets devolve to raw.
- TESTING-003: selector documentation must capture new tests and collect-only evidence.
