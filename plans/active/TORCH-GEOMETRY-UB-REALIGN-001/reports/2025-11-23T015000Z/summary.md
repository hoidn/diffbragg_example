### Turn Summary
Wired incremental UB parameterization into Stage A LBFGS closure with 10 trainable DOF (q_delta quaternion, cell log-perturbations + angle deltas) constructing A* = U(q_delta) @ B(cell_deltas) in a single direction per spec-db-core.md.
Added use_incremental_ub config flag, initialized baseline crystal state (U₀, B₀) from dxtbx, and implemented closure branching to derive geometry via B1/B2 helpers with MOSFLM a/b/c_star injection (no cell overrides per GRADIENT-001).
Regression guard test_stage_a_expansion PASSED with default cell+misset path unaffected.
Next: validation with use_incremental_ub=True requires config override mechanism (Phase B follow-up) and DB-AT-026 closure integration checks.
Artifacts: plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T015000Z/ (pytest_stage_a_incremental_ub_false.log)
