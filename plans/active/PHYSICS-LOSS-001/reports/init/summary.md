### Turn Summary
Completed initialization audit for PHYSICS-LOSS-001 documenting that Phase A (bridge data plumbing) is functionally complete in nanobrag_bridge.py with sigma_readout field, broadcast logic, and ADU→photon conversion.
Gap identified: CLI lacks `--sigma-r` flag and refine_one.py does not pass sigma_readout parameter, defaulting to zeros (Poisson-only mode).
Next: Either add CLI integration or proceed to Phase B (variance-weighted loss implementation) depending on supervisor direction; Phase B requires updating compute_masked_mse_loss and run_nanobrag_refinement closures.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/init/ (audit.md)
