Summary: Attach calibrated beam metadata without inflating intensity by wiring beam_config into simulate_forward_once and gating N_cells so DB_AT_024 can regain traction toward threshold.
Mode: Parity
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z/
Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once (attach calibration beam_config to the torch crystal and guard N_cells usage until sample clipping semantics match the generator).
- Pytest: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z/pytest_db_at_024.log
- Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z/
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z
3. Update `dbex/nanobrag_bridge.py::create_crystal_config` to accept an `apply_n_cells` flag and return both the config and a boolean so `simulate_forward_once` can skip `N_cells` unless calibration proves it safe.
4. In `simulate_forward_once`, build `beam_config` from calibration, pass it into `TorchCrystal(..., beam_config=beam_config, device=device)` and to the `Simulator`, and only forward `N_cells` when `apply_n_cells` is True; add a diagnostics field logging whether the override was applied.
5. Adjust `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` to persist the new diagnostics flag inside `summary_metrics["calibration"]` so regressions reapply `N_cells` are visible in artifacts.
6. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z/pytest_db_at_024.log
7. jq -r '.corr_median, .localization_success_rate, .calibration.n_cells_applied' plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z/mapping_metrics.json > plans/active/MAP-SCALE-001/reports/2025-11-04T210000Z/mapping_metrics_summary.txt
Pitfalls To Avoid:
- Do not reintroduce raw `N_cells` overrides without the beam-config sample clipping; it explodes intensity (SCALE-005).
- Keep √spot_scale application exactly once after simulation per SCALE-002.
- Preserve device neutrality by routing `device` through TorchCrystal and Simulator constructors.
- Leave beam flux/exposure parsing tolerant—missing values must surface descriptive errors, not silent defaults.
- Maintain diagnostic emission structure so existing JSON readers keep working; extend rather than replace keys.
- Run pytest with NANOBRAGG_DISABLE_COMPILE=1 to avoid Dynamo regressions noted in runtime checklist.
- Capture logs/artifacts under the new timestamp directory; missing files will fail parity ledger expectations.
- Respect Environment Freeze—no package installs or cuda tweaks while adjusting bridge code.
If Blocked:
- Store failing `mapping_metrics.json` and pytest log in the artifact directory, summarize the observed corr/localization plus calibration fields in docs/fix_plan.md Attempts History, and ping Galph with the error reason (include whether diagnostics reported n_cells_applied=True).
Findings Applied (Mandatory):
- SCALE-001 — Keep structure factors unscaled pre-sim; ensure new plumbing does not scale amplitudes.
- SCALE-002 — Apply √spot_scale exactly once post-simulation even after attaching beam_config.
- SCALE-003 — Continue sourcing refined Fopt and calibration metadata together; tests still rely on refined fixtures.
- SCALE-004 — Maintain refined geometry + calibration pairing in DB_AT_024 (geometry fallback remains unsupported for thresholds).
- SCALE-005 — Ignore `N_cells` until sample clipping semantics are validated; expose diagnostics to make the guard auditable.
- TESTING-003 — Verify the mapped selector collects >0 tests and archive the pytest log referenced in docs.
Pointers:
- docs/spec-db-conformance.md:43-46 — DB_AT_024 acceptance thresholds to satisfy after calibration fix.
- docs/nanobrag_api.md:18-67 — Beam and crystal config fields required by nanobrag_torch.
- docs/architecture.md:82-109 — Bridge responsibilities for calibration metadata flow.
- plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/summary.md — Regression details after naive N_cells wiring.
- plans/active/MAP-SCALE-001/reports/2025-11-04T203000Z/summary.md — Calibration sweep proving N_cells as failure source.
Next Up (optional):
- Re-run the calibration sweep script under the new build to confirm corr_vs_canonical improves once beam_config is attached.
