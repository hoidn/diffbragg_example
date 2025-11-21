# Input

- Summary: Thread the metadata sigma readout source through DB-AT-024 mapping + CLI diagnostics so provenance and chi-squared telemetry stay consistent across all acceptance gates.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `tests/dbex/test_mapping_consistency.py::{canonical_assets,TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke}` + `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` + `docs/TESTING_GUIDE.md#1.4` + `docs/development/TEST_SUITE_INDEX.md:12` — plumb the existing `smoke_sigma_source` fixture into DB-AT-024 so metadata-backed datasets reuse `sp.proc/idx-0000_sigma_metadata.expt`, inject `sigma_readout` tensors into `prepare_refinement_inputs`, and assert mapping telemetry reports `sigma_readout_provenance="external_lookup"` with clamp stats while CLI diagnostics gain a metadata-backed branch that verifies `/torch_diagnostics` attrs and Stage A telemetry flip between CLI scalar vs metadata; refresh the docs/registry rows with the new DB-AT metadata workflow and artifact expectations.
- Test: (a) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/pytest_db_at_024_metadata.log`; (b) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k torch_diagnostics_metadata | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/pytest_cli_metadata.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/

## How-To Map
1. Inspect DB-AT-024 harness via `rg -n "DB_AT_024" tests/dbex/test_mapping_consistency.py` to locate the `canonical_assets` fixture and confirm where `DataLoad` pulls refGeom assets.
2. Update `tests/dbex/test_mapping_consistency.py::canonical_assets` to accept `smoke_sigma_source`, swap `expt` paths to `sp.proc/idx-0000_sigma_metadata.expt` when metadata is requested (skip if assets missing), and surface the metadata tiles’ provenance on the returned dict.
3. In `TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`, branch on `smoke_sigma_source` to pass either deterministic CLI scalar arrays (3.0 ADU) or the harvested metadata tensor into `prepare_refinement_inputs`, propagate the provenance through the `diagnostics` payload, and assert `diagnostics["sigma_readout_provenance"]` plus `variance_floor_clamp_fraction` behave as expected; ensure `mapping_metrics.json` records the provenance + clamp stats.
4. Parameterize/extend `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` so it exercises both `cli_override` and metadata flows by seeding `mock_dl.sigma_readout_map`/`sigma_readout_map_source="external_lookup"`, verifying `_write_torch_outputs` writes the correct attrs for each branch, and keeping other CLI sigma guard tests intact.
5. Refresh `docs/TESTING_GUIDE.md` §1.4 and `docs/development/TEST_SUITE_INDEX.md` to describe the DB-AT metadata command, env vars (`DBEX_SMOKE_SIGMA_SOURCE`, `DBAT024_ARTIFACT_DIR`), and artifact filenames (`pytest_db_at_024_metadata.log`, `mapping_metrics.json`, `pytest_cli_metadata.log`).
6. Run the mapped selectors with metadata enabled, teeing logs into the new report directory and archiving `mapping_metrics.json`/`.csv` alongside the pytest outputs.

## Pitfalls To Avoid
1. Do not run DB-AT selectors without `DBEX_SMOKE_DETECTOR_SIZE=full`; pytest guard will abort before emitting artifacts.
2. Never regenerate metadata fixtures inside tests—skip with actionable messaging when `sp.proc/idx-0000_sigma_metadata.expt` or `.sigma_tiles.pkl` is missing.
3. Preserve CLI sigma precedence (`--sigma-rdout` > `--sigma-map` > metadata); metadata coverage must not reintroduce silent fallbacks.
4. Keep variance-floor assertions unchanged (PHYSICS-LOSS-002) so metadata runs still require positive clamps and report fractions in telemetry.
5. Ensure DB-AT telemetry comparisons continue to reference the canonical Stage A chi-squared snapshot; don’t mix Stage A/B/C loss units.
6. Avoid mutating `refGeom.expt` in-place when swapping metadata assets—only point fixtures to the metadata copy.
7. Capture `DBAT024_ARTIFACT_DIR` outputs (JSON/CSV) before rerunning the selector to avoid overwriting logs without evidence.
8. Respect Environment Freeze: no pip/conda/cmake changes even if metadata assets look stale; treat missing deps as blockers.

## If Blocked
Record the failing pytest/stdout in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/blocked.log`, note whether metadata assets existed (`ls sp.proc/idx-0000_sigma_metadata*`), include the exact command + env vars, and append the blocker plus remedial steps to `docs/fix_plan.md` Attempts History before pausing the initiative.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — Stage B/C (and now DB-AT) must consume the same variance-weighted denominator/telemetry as Stage A; metadata selection simply changes provenance.
- PHYSICS-LOSS-002 — Sigma-floor clamps stay mandatory; tests must assert clamping telemetry even when metadata supplies larger RMS values.
- PHYSICS-LOSS-003 — Canonical Stage A chi-squared snapshots drive Stage C/DB-AT comparisons; metadata coverage cannot change units or comparison targets.
- PHYSICS-LOSS-004 — Sigma-map loader constraints (shape, positivity) govern the metadata assets; reuse the helper outputs rather than fabricating new arrays.
- PHYSICS-LOSS-005 — External_lookup tiles are the normative metadata source; selectors must assert `sigma_readout_provenance="external_lookup"` whenever metadata mode is active.
- REFINE-007 — Detector microslip acceptance depends on telemetry deltas; documentation updates should remind operators not to relax gate thresholds when switching sigma sources.

## Pointers
- docs/fix_plan.md:15 — PHYSICS-LOSS-001 ledger + 2025-11-21T075449Z planning entry describing Phase I scope.
- plans/active/PHYSICS-LOSS-001/implementation.md:70 — Phase H completed + new Phase I checklist governing DB-AT/CLI metadata coverage.
- docs/TESTING_GUIDE.md:80 — Sigma readout policy + metadata commands to update with DB-AT instructions.
- docs/development/TEST_SUITE_INDEX.md:12 — Stage-smoke/DB-AT registry rows needing the new metadata selector details.
- tests/dbex/test_mapping_consistency.py:1 — DB-AT-024 harness where `smoke_sigma_source` plumbing and telemetry assertions must be extended.
- tests/dbex/test_refine_one_cli.py:772 — CLI diagnostics test verifying `/torch_diagnostics` metadata; add metadata branch assertions here.

## Next Up (optional)
1. Once DB-AT + CLI telemetry coverage ships, finish Phase G (G4/G5) by adding manifest/hash guards for metadata fixtures and a CI validation hook.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/collect_db_at_024_metadata.log`
