Summary: Align nanobrag CLI with MAP-SCALE-001 calibration guardrail so zero-iteration runs use DiffBragg metadata.
Mode: none
Focus: MAP-SCALE-002 — Nanobrag CLI calibration parity
Branch: integration
Mapped tests: pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
Artifacts: plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z/{summary.md,collect_db_at_024.log,pytest_cli.log,pytest_db_at_024.log,mapping_metrics.json}

Do Now (hard validity contract)
- Implement: dbex/refine_one.py::run_nanobrag_backend — load DiffBragg `config_torch.json` metadata (spot_scale_override, beam flux/exposure, beamsize, `N_cells`) via `load_calibration_metadata`, forward overrides to `create_beam_config`/`create_crystal_config` with gated `apply_n_cells`, and support optional refined MTZ input; extend `create_parser` for new CLI flags and refresh `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator` to assert calibration plumbing.
- Validate: pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator --maxfail=1 -q
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator --maxfail=1 -q | tee plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z/pytest_cli.log
3. DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z/collect_db_at_024.log
4. DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z/pytest_db_at_024.log

Pitfalls To Avoid
- Do not regress diffbragg backend behavior while touching `refine_one` parser dispatch.
- Preserve legacy defaults: CLI must still run when calibration flags omitted (warn, no crash).
- Keep calibration loaders within workspace (no downloads; Environment Freeze applies).
- Ensure `create_crystal_config` only enables `apply_n_cells` when metadata present; guard diagnostics accordingly.
- Maintain ADU/photon branch neutrality—respect `--adu-per-photon` handling already in `run_nanobrag_backend`.
- Update mocks in CLI tests instead of importing real torch modules (keep tests fast/offline).
- Record new SCALE-006 guard compliance in summary instead of modifying production metadata files.

If Blocked
- Capture the failing command output in `plans/active/MAP-SCALE-002/reports/2025-11-05T000500Z/blockers.md`, note missing assets or import errors, mark MAP-SCALE-002 as blocked in `docs/fix_plan.md`, and alert Galph via galph_memory next loop.

Findings Applied (Mandatory)
- SCALE-003 — Use DiffBragg spot scale and refined |F| during zero-iteration parity; CLI must load same metadata.
- SCALE-004 — Calibration metadata flows through `load_calibration_metadata`; reuse helper instead of ad-hoc JSON parsing.
- SCALE-005 — Enable sample clipping only when `beam_config` and `N_cells` travel together; cover via CLI changes.
- SCALE-006 — Nanobrag CLI must forward DiffBragg `config_torch.json` metadata before invoking Simulator.
- TESTING-003 — Update pytest docs/log references when selectors change statuses.

Pointers
- dbex/refine_one.py:162 — Current nanobrag CLI backend lacking calibration plumbing.
- tests/dbex/test_refine_one_cli.py:67 — Existing CLI backend dispatch and simulator test to extend.
- docs/spec-db-workflow.md:30 — Calibration and scaling expectations for zero-iteration parity.
- docs/config_crosswalk.md:20 — Beam/crystal parameter mapping needed when forwarding overrides.
- docs/findings.md:18 — SCALE-005/SCALE-006 guardrails governing sample clipping + calibration.

Next Up (optional)
1. Document new CLI flags in `docs/TESTING_GUIDE.md` §2 once implementation lands.
2. Evaluate CLI smoke harness to compare CLI outputs against DB_AT_024 metrics post-calibration.
