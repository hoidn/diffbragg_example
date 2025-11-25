### Turn Summary
Diagnosed that the new DBEX_SMOKE_GEOM_PATH plumbing now crashes the Stage A smokes because the metadata sigma-map pickle is still full-detector sized (2527×2463) while refGeom_small expects 1024×1024 tiles.
Planned the follow-up loop to crop the sigma-map to the refGeom_small window, default the smoke fixtures to that asset (with env overrides intact), and refresh the data-dependency manifest before rerunning the mapping probe plus DB-AT-028/029.
Next: author the crop helper + fixture/docs changes, generate the cropped pickle, and rerun compare_mapping_forward_cpu_gpu.py and the DB-AT selectors under the canonical env so we can see whether ROI CC recovers.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/
