### Turn Summary
Implemented mapping alignment so both stage_a_smoke_result fixture and CLI probe consume the exact same mapping_context.inputs (target, loss_mask, panel_slices) from the metadata-sigma smoke dataset, resolving input misalignment (CLI used refined.expt, pytest used sp.proc metadata expt).
Fixed the parity probe to replicate tests/conftest.py smoke_dataset_paths logic; when DBEX_SMOKE_SIGMA_SOURCE=metadata, it now uses sp.proc/idx-0000_sigma_metadata.expt + refGeom.refl + 747_mask.pkl.
Next: re-run the CLI probe with aligned smoke dataset paths to confirm mapping ROI CC/scale match (expect both ~-0.04 or both ~0.62), then investigate Stage A negative correlations per Phase D plan.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T045456Z/ (parity_probe/, db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json, pytest_db_at_028_029.log, pytest_db_at_028_029_collect.log)
