### Turn Summary
Scoped the fix to keep Stage A smoke fixtures on the canonical refGeom geometry even when metadata sigma tiles are enabled so the ~1° refined-orientation drift stops poisoning mapping ROI correlations.
Authored a ready-for-implementation Do Now that introduces DBEX_SMOKE_GEOM_PATH/DBEX_SMOKE_SIGMA_MAP_PATH, copies the canonical detector/beam/crystal into DataLoad when rotation deltas exceed tolerance, and records the override in mapping + DB-AT diagnostics before rerunning the mapping probe and DB-AT-028/029.
Next: Ralph implements the canonical-geometry override, captures the mapping_cpu_gpu_canonical probe, and reruns DB-AT-028/029 with the refreshed telemetry.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/
