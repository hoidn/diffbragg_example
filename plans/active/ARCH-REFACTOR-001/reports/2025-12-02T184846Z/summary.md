### Turn Summary
Completed Stage B consolidation by extracting HKL utilities to hkl_utils.py and inlining LBFGS/parity helpers into StageB class methods.
Both acceptance gates passed (guard 0.78s, shell smoke 22.69s) with no behavioral regression; baseline parity guard and collector-only telemetry path remain intact.
Next: Phase C.6 — delete stage_b_impl.py once all imports are migrated and verified.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/ (pytest_stage_b_guard.log, pytest_stage_b_shell.log)
