Summary: Harden `_write_torch_outputs` so CLI diagnostics always emit numeric ROI scores and stable aggregates.
Mode: none
Focus: TORCH-CLI-004 — Torch diagnostics ROI score coercion
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
- pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1
Artifacts: plans/active/TORCH-CLI-004/reports/2025-11-04T222435Z/
Do Now:
- TORCH-CLI-004: Implement: dbex/refine_one.py::_write_torch_outputs — coerce ROI scores to floats before aggregating, guard empty-score collections, and keep telemetry attributes numeric; update tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata to assert the stabilized diagnostics. Validate: pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata; pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1. Capture logs in the artifact directory and confirm HDF5 payload reflects numeric scores.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. TORCHCLI004_ARTIFACT_DIR=plans/active/TORCH-CLI-004/reports/2025-11-04T222435Z pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee "$TORCHCLI004_ARTIFACT_DIR/collect_torch_diag.log"
3. TORCHCLI004_ARTIFACT_DIR=plans/active/TORCH-CLI-004/reports/2025-11-04T222435Z pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1 | tee "$TORCHCLI004_ARTIFACT_DIR/pytest_torch_diag.log"
Pitfalls To Avoid:
- Keep `_write_torch_outputs` telemetry schema intact (attributes + datasets) to preserve downstream tooling.
- Do not swallow real runtime errors; only guard the aggregation for empty lists or non-scalars.
- Respect Environment Freeze—no new dependencies or external tooling.
- Ensure mocks in the test still exercise telemetry fields; avoid hard-coding production paths.
- Maintain deterministic prints/logs so existing diagnostics remain readable.
- Leave MAP-SCALE-005 guard behavior untouched (refined MTZ enforcement must keep raising on failure).
- Refrain from loosening test assertions; strengthen them to cover numeric coercion instead.
- Keep pytest selectors deterministic—no wildcard `-k` usage.
- Update documentation only if behavior description changes; otherwise verify existing entries remain accurate.
If Blocked: Log minimal error signature in plans/active/TORCH-CLI-004/reports/2025-11-04T222435Z/blocked.md, add Attempts History entry to docs/fix_plan.md, update galph_memory.md with `state=blocked`, and pivot per loop discipline.
Findings Applied:
- DIAGNOSTICS-001 — Maintain `/torch_diagnostics` metadata contract while adjusting score coercion.
- SCALE-003 — Preserve refined/raw HKL telemetry attributes when editing diagnostics.
- TESTING-002 — Use deterministic mocks within CLI tests to validate behavior without real simulator runs.
- TESTING-003 — Capture collect-only evidence for documented selectors.
Pointers:
- dbex/refine_one.py:384 — ROI scoring aggregation and diagnostics emission logic.
- tests/dbex/test_refine_one_cli.py:520 — Torch diagnostics metadata test harness to update.
- docs/spec-db-tracing.md:22 — Telemetry payload expectations for torch diagnostics.
- plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_full_suite.log — Source TypeError trace.
Next Up (optional): 1) Re-run full CLI module pytest (`pytest -v tests/dbex/test_refine_one_cli.py`) to confirm broader coverage once the fix lands.
