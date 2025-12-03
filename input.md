Summary: Extend the simulator comparison probe so we have per-path intensity + calibration metrics for Stage A, reconstruction, and simulate_forward_once, then rerun DB-AT-028/029 with the new logging so we can isolate which scale term is still missing.
Mode: none
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: main
Mapped tests: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/

Do Now:
- Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py::main — add CLI flags for `--detector-size` and `--device`, run Stage A warm cache, reconstruction cold path, and `simulate_forward_once` against the canonical smoke dataset, and record for each path the calibration inputs (`spot_scale_override`, `log_scale_baseline`, `beam_flux`, `beam_exposure`, `beamsize_mm`, `adu_per_photon`), raw mean/max, sqrt-spot-scale-adjusted mean, final `scale_factor`, and cross-path ratios. Emit both `simulator_intensity_metrics.json` and a Markdown summary under the 2025-12-09T210000Z report dir.
- Capture: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --device cpu --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/simulator_intensity_metrics.json
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/pytest_db_at_028_029.log

How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --device cpu --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/simulator_intensity_metrics.json
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/pytest_db_at_028_029.log

Pitfalls To Avoid:
- Do not edit or reinstall nanobrag_torch itself; we are only authoring evidence scripts in the repo per Environment Freeze rules.
- Keep the probe script in plans/active (T2 tool) and commit the JSON + Markdown artifacts under the timestamped report directory.
- Use the smoke dataset (`DBEX_SMOKE_DETECTOR_SIZE=small`) so runs stay deterministic and within CPU limits.
- Preserve existing script functionality (Stage A vs reconstruction comparison) while adding simulate_forward_once and the new telemetry fields.
- When rerunning DB-AT-028/029 keep the CLI overrides exactly as listed so we can compare logs apples-to-apples with prior loops.

If Blocked:
- If the smoke dataset or calibration assets are missing, log the missing file paths in plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/blocked.md along with the command output, then update docs/fix_plan.md + galph_memory.md with the block reason so we can escalate.
- If pytest fails before reaching the Stage A selector for non-physics reasons (import error, fixture missing), capture the full traceback in the report dir and stop; do not attempt to downgrade tests or patch dependencies.

Findings Applied:
- SCALE-002 — Stage A must reapply √spot_scale post-run; we need the probe to show whether reconstruction is missing this factor.
- SCALE-009 — Reconstruction helpers must mirror Stage A scaling and calibration threading; the new metrics should confirm which term is still misaligned.

Pointers:
- docs/spec-db-core.md:106 — Objective Function & Variance Model definition for Bragg + background scaling.
- docs/spec-db-workflow.md:19 — Calibration Policy (ADU vs photons, spot_scale precedence) that governs expected scale factors.
- docs/config_crosswalk.md:1 — Detector/beam/crystal mapping contract and calibration threading references for beam flux/exposure.
- docs/fix_plan.md:133 — ARCH-SIM-CONSTRUCTION-001 ledger entry with latest lifecycle state and exit criteria.
