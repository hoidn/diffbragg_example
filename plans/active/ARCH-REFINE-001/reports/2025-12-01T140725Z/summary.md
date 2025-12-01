### Turn Summary
Retired the legacy `_write_torch_outputs` alias from `dbex/refine_one.py` and refreshed architecture docs so they cite `dbex/io/writer.py` + `dbex/physics/{forward,loss}.py` as canonical owners; no telemetry schema changes.
Enhanced `test_torch_diagnostics_metadata` to assert the alias is absent and fixed mock_args initialization to prevent TypeError; both parametrized variants pass.
Next: Phase C (writer extraction + physics helpers + docs sync) is complete; ready to advance to Phase D doc sync (architecture IDLs) or pivot to remaining Stage refinements as prioritized.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/ (collect_cli_writer.log, pytest_cli_writer.log, docs_diff.md)
