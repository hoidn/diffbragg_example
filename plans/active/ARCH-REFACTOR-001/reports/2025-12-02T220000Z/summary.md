### Turn Summary
Migrated CLI from run_nanobrag_refinement facade to direct RefinementEngine instantiation; CLI now builds RefinementContext, instantiates conditional stage list, and extracts artifacts from engine._artifacts per 5-step Engine pattern.
All 2/2 CLI test selectors passed; HDF5 /torch_diagnostics schema unchanged, telemetry structure preserved, no behavioral regression vs facade path.
Next: Phase D.3 test harness migration (migrate test files from facade to Engine, following CLI blueprint).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/ (pytest_cli_refactor.log)
