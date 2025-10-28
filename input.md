Summary: Add the `--backend` flag to `dbex.refine_one`, wire the torch dispatch, and update docs/tests so the CLI can select the nanobrag path.
Mode: TDD
Focus: TORCH-CLI-003 — Wire torch backend flag into CLI
Branch: integration
Mapped tests: python -m dbex.refine_one --help ; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py ; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge.py
Artifacts: plans/active/TORCH-CLI-003/reports/2025-10-28T234618Z/{notes.md,cli_help.log,pytest.log,diagnostics.json}
Do Now:
  1. TORCH-CLI-003 — A1 (plans/active/TORCH-CLI-003/implementation.md) — tests: python -m dbex.refine_one --help; refactor `dbex/refine_one.py` into testable entry points, add the `--backend {diffbragg,nanobrag}` option defaulting to diffbragg, and ensure help text documents backend usage without triggering imports at module load.
  2. TORCH-CLI-003 — A2 (plans/active/TORCH-CLI-003/implementation.md) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py; implement backend dispatch so diffbragg reuses the existing path while `nanobrag` hydrates `DataLoad` outputs via `prepare_refinement_inputs`, generates a Bragg tensor (stub until real simulator), writes ROI/HDF5 outputs, and saves torch diagnostics under `/torch_diagnostics`.
  3. TORCH-CLI-003 — B1 (plans/active/TORCH-CLI-003/implementation.md) — tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata; log masked-MSE and ROI coverage metrics for the torch path, surface them via CLI logging, and update `--help` examples accordingly.
  4. TORCH-CLI-003 — B2 (plans/active/TORCH-CLI-003/implementation.md) — tests: none — evidence-only; refresh `docs/index.md` CLI section and any related docs to describe the backend flag and cite the torch diagnostics artifact expectations.
Priorities & Rationale:
  - Honor the CLI contract in docs/spec-db-interfaces.md:7-16 by introducing the `--backend` selector and preserving diffbragg as the default until torch stabilizes.
  - Follow the architectural guidance in docs/architecture.md:28-55 and plans/nanobrag_integration_plan.md:168-184 so the CLI delegates to bridge inputs and the torch refinement stack cleanly.
  - Maintain tensor and mask contracts from docs/spec-db-core.md:20-56 when the CLI plumbs DataLoad outputs into the torch backend.
  - Map acceptance coverage per docs/TESTING_GUIDE.md:60-68 by documenting CLI smoke commands and planning pytest coverage for the new dispatcher.
  - Keep runtime guardrails (env flags, device neutrality) compliant with docs/spec-db-runtime.md:18-20 during CLI invocation.
How-To Map:
  - export ART=plans/active/TORCH-CLI-003/reports/2025-10-28T234618Z; mkdir -p "$ART"; touch "$ART/notes.md"
  - python -m dbex.refine_one --help | tee "$ART/cli_help.log"
  - KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py | tee "$ART/pytest.log"
  - KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge.py | tee -a "$ART/pytest.log"
  - Capture torch diagnostics snapshot (e.g., JSON dump) from the nanobrag path into "$ART/diagnostics.json" and summarize metrics in notes.md
Pitfalls To Avoid:
  - Do not run DataLoad or heavy imports at module import time; gate work inside `main()`.
  - Preserve `--backend diffbragg` as the default and keep legacy behavior bit-for-bit.
  - Guard nanobrag dispatch with existing square-pixel checks and mask polarity assertions from the bridge.
  - Keep stubbed torch outputs deterministic so new tests remain stable without real simulator installs.
  - Ensure HDF5 writes stay under the documented ROI layout and add diagnostics to a separate group to avoid schema regressions.
  - Set required env vars (`KMP_DUPLICATE_LIB_OK=TRUE`) before invoking pytest or CLI torch paths.
  - Avoid touching external tool trees (dials/, dxtbx/, cctbx_project/).
  - Capture Metrics/Artifacts entries before exiting the loop.
If Blocked: If torch dispatch requires unavailable data or simulator installs, record the blocker in docs/fix_plan.md Attempts History (Metrics: pending; Artifacts: pending), update galph_memory.md with `state=blocked`, and pivot per dwell rules.
Findings Applied (Mandatory):
  - GEOMETRY-001 — Plan routes CLI torch path through bridge helpers that enforce square pixels and geometry mapping.
  - DXTBX-001 — Dispatch leverages crystal config hydration so `get_A()` tuples reshape correctly before simulator calls.
  - CONFORMANCE-001 — CLI smoke command and pytest selector mapping maintain DB-AT readiness with env flags documented.
  - RUNTIME-001 — Plan exports runtime guardrails (`KMP_DUPLICATE_LIB_OK`, compile toggles) ahead of torch execution to avoid runtime instability.
