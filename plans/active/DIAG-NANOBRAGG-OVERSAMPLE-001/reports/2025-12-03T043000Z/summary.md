### Turn Summary
Successfully identified root cause of ARCH-SIM-CONSTRUCTION-001 reconstruction magnitude discrepancy as DetectorConfig.oversample field mutation (Case A).
Added debug instrumentation to nanobrag_torch, installed in editable mode, captured 1,166 debug lines showing oversample=3 on first invocation then oversample=-1 on all 208 subsequent runs.
Next step: Phase B — fix DetectorConfig preservation via deep-copy, frozen dataclass, or mutation site removal (estimated LOW complexity, likely 1-line fix).
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/ (pytest_db_at_028_debug.log, root_cause_analysis.md, nanobrag_debug_instrumentation.patch)
