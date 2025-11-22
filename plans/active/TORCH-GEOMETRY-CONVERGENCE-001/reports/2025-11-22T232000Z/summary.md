### Turn Summary
Audited first U-matrix closure for parameter staleness after Phase C3 confirmed chi²=8.8M BEFORE optimizer.step().
No parameter staleness found — all parameters (log_scale, q_params, U, A*, crystal_overrides) correctly captured and used in closure.
Identified code path divergence hypothesis: zero-point validation (`use_mapping_zero_geometry=True` → direct MOSFLM injection) vs first closure (`use_mapping_zero_geometry=False` → U/B_ideal round-trip) may produce different results even at zero parameters.
Next: instrument A* checksum logging for both code paths and run 2-step diagnostic to prove/disprove divergence hypothesis.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/ (phase_c4_first_closure_audit.md, phase_c4_parameter_staleness_decision.md)
