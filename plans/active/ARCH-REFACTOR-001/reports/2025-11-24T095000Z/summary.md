### Turn Summary

Extracted reusable Stage A debug utilities from 1849-line monolithic script into `dbex/tools/stage_a_adam.py` module (1898 lines) with 15 functions and 3 classes, all with comprehensive docstrings.
Refactored CLI to thin 340-line argparse shim delegating to module functions; CLI smoke test PASSED (Phase 1, cpu, seed=42) producing expected JSON artifacts with 92 ROIs.
Next: Phase D D2.3+D2.4 (test suite + documentation).

Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/ (extraction_mapping.md, cli_smoke_test.log)
