Summary: Restore Stage A/reconstruction simulator parity by threading the `apply_calibration_n_cells` gate into `build_final_bragg_from_stage_a_telemetry` and revalidating DB-AT-028/029.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: main
Mapped tests: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/{simulator_intensity_metrics.json,summary.md,pytest_db_at_028_029.log,db_at_028/,db_at_029/}

Do Now:
- Implement `apply_calibration_n_cells` parity inside `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` by extracting `N_cells` from `config.calibration_metadata`, honoring `config.apply_calibration_n_cells`, and passing those values into `create_crystal_config(...)` so both warm and cold reconstruction paths reuse the same domain-count gating as Stage A/mapping.
- Preserve the existing mask-coverage guard and DEBUG block, but extend the printout (or add a short log) so it records whether `N_cells` was applied or suppressed; keep device/dtype neutrality and do not reintroduce the explicit `* sqrt_spot_scale` multiplication (SCALE-009 still handled via `scale_factor`).
- Re-run the simulator comparison probe to confirm Stage A warm cache, reconstruction helper, and `simulate_forward_once` now produce matching raw/scaled means, saving outputs under the new report directory.
- Execute `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with DBAT artifact env vars pointed at the same report directory so we capture logs/metrics proving chi² and ROI correlation gates return to spec.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --device cpu --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/simulator_intensity_metrics.json`
   - Expect `stage_a_vs_reconstruction` ≈ 1.0 and note the logged `n_cells_applied` flag in stdout/summary.md.
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/pytest_db_at_028_029.log`
   - Leave the mask coverage JSON that reconstruction writes in the same report directory so we have before/after coverage evidence.

Pitfalls To Avoid:
- Do not reintroduce the old `* sqrt_spot_scale` multiplication; SCALE-009 expects the sqrt factor to be encoded via `scale_factor = exp(log_scale_baseline + Δ)`.
- Honor `config.apply_calibration_n_cells` exactly as Stage A context/mapping does: skip `N_cells` when the gate is False, and make sure the cold path does NOT silently enable N_cells for small-detector fixtures.
- Keep device/dtype handling intact (CrystalConfig overrides must stay tensor-friendly); avoid moving masks or HKL grids to CPU in the cold path or Stage A warm cache.
- Environment Freeze is still in effect—no package rebuilds/pip installs. Only touch repo-local Python files.
- Ensure the DB-AT selectors use `DBEX_SMOKE_SIGMA_SOURCE=cli_override`; other sigma sources violate the test contract.

If Blocked:
- If raw/scaled means still diverge after the gating patch, capture the updated `compare_simulator_outputs.py` JSON + stdout plus the reconstruction DEBUG block and commit them under the same report directory, then stop and raise the mismatch (include chi²/median ROI values) rather than iterating further.
- If the DB-AT selectors abort for reasons unrelated to reconstruction (e.g., missing fixtures), log the failing command + stderr into the report directory and notify Galph so we can reassess the plan instead of guessing.

Findings Applied (Mandatory):
- SCALE-008 — Stage A and mapping must share the `apply_calibration_n_cells` gate so simulator domain counts stay consistent.
- SCALE-009 — Spot-scale factors are applied via `sqrt_spot_scale` / `log_scale_baseline` and must not be double-counted.

Pointers:
- dbex/refinement/reconstruction.py:132-220 — current Stage A reconstruction helper lacking the N_cells gate.
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:260-310 — Phase C.5/C.6 notes and the new probe/test plan for this loop.
- docs/fix_plan.md:133-205 — ARCH-SIM-CONSTRUCTION-001 ledger entry, lifecycle status, and recent findings.
