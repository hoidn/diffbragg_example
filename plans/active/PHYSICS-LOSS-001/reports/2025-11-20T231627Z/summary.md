### Turn Summary
Implemented variance-weighted chi-squared loss for nanobrag refinement per spec-db-core.md:57-68; Stage A now minimizes Sum((I_model - I_obs)^2 / (I_model.detach() + sigma^2)) with sigma_readout plumbed through CLI (--sigma-rdout), bridge (prepare_refinement_inputs), and LBFGS closures.
Refactored compute_masked_mse_loss in nanobrag_bridge.py to accept optional sigma_readout parameter with variance-weighted path (chi-squared) and MSE fallback; updated DB-AT-010 test fixtures to provide deterministic sigma_readout=3.0 ADU and confirmed gradcheck passes for crystal_cell_a (78.21s).
Next: extend telemetry to emit chi_squared alongside masked_mse in RefinementTelemetry and _write_torch_outputs; run full DB-AT-010 suite (cell_gamma, distance, wavelength) and update TEST_SUITE_INDEX.md.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/ (pytest_db_at_010.log)
