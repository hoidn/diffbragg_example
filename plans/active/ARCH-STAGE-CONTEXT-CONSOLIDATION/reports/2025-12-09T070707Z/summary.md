### Turn Summary
Refactored `_build_stage_b_params` signature from 16 positional parameters to single typed `StageBInputContext` parameter per ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.2.
Function body unpacks all 16 fields at the start for backwards compatibility; call site in `run()` constructs the dataclass before calling.
Next: Phase C.4 (update any remaining Stage B call sites) or Phase D (eliminate telemetry dict mutations).
Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/ (pytest_context.log, pytest_smoke_collect.log, import_check.log)
