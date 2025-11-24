### Turn Summary
Implemented Phase B.1 variance HDF5 extension in both Legacy and Torch backends computing V=max(I_model+sigma_readout^2, sigma_floor^2) per spec-db-core.md §86-90 and Phase B.2-lite static triptych PNG export with --export-triptychs flag calling dbex.vis.plot_triptych.
All validations PASS: compilation OK, HDF5 structure correct with variance/roi%d datasets plus sigma_readout/sigma_floor scalars, export logic functional.
Next: Phase B.3 planning for auto-generate summary report in refine_one.py exit or Phase C for interactive viewer refactor.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/ (validation_hdf5.log, validation_export.log, decision.json)
