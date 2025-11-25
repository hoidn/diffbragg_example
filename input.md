Summary: Thread the smoke calibration asset through the shared refGeom fixture so Stage A mapping diagnostics finally record the correct calibration_path/spot_scale values before re-running the metadata smoke selectors.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests:
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/

Do Now
- Implement: tests/conftest.py::refgeom_dataload — propagate `calibration_config_path` (defaulting to `sp.proc/calibration/config_torch_smoke.json` when present, otherwise honoring `DBEX_SMOKE_CALIB_PATH`) onto `dataload.args` so `build_mapping_stage_a_context` and Stage A fixtures can load the captured smoke calibration without falling back to golden assets. Preserve the geometry override + sigma-map wiring that already lives in this fixture.
- Validate: (1) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/pytest_db_at_028_029_collect.log` (fail if <2 tests collect); (2) same env plus `DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/pytest_db_at_028_029.log` (assertions may fail but run must complete); (3) `python plans/active/TOOLING-VIS-001/bin/check_mapping_fixture_calibration.py --artifacts plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z --expected-calib sp.proc/calibration/config_torch_smoke.json` to assert both mapping_context_fixture.json files now report the smoke calibration path and a non-unit spot_scale_override.

How-To Map
1) export AUTHORITATIVE_CMDS_DOC and the full metadata env block above before touching pytest so the fixture sees the overrides; keep the same shell for all commands.
2) Run `python -m compileall tests/conftest.py` to catch syntax errors after editing the fixture.
3) `mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/{db_at_028,db_at_029}` to stage artifact directories.
4) Execute the collect-only command from Do Now step (1) and store the log via tee at `.../pytest_db_at_028_029_collect.log`.
5) Execute the full pytest command from Do Now step (2) with tee to `.../pytest_db_at_028_029.log`; this writes refreshed metrics JSONs + mapping_context_fixture.json under the db_at_* artifact dirs.
6) `python plans/active/TOOLING-VIS-001/bin/check_mapping_fixture_calibration.py --artifacts plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z --expected-calib sp.proc/calibration/config_torch_smoke.json | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/check_calibration_path.log` to fail fast if calibration_path remains null or spot_scale_override=1.0.

Pitfalls To Avoid
- Do not touch production Stage A code paths (dbex/nanobrag_refinement.py, simtbx) in this loop—only the pytest fixture.
- Keep the metadata env vars identical between collect-only and pytest runs; missing one drops back to cli_override sigma.
- Preserve existing geometry override telemetry (`geometry_metadata`) when editing refgeom_dataload; other selectors consume it.
- Never fall back to golden refined assets inside refgeom_dataload; the point is to use the smoke calibration captured under sp.proc/.
- Do not remove the sigma-map validation logic (shape checks) when adding calibration wiring.
- Avoid introducing new third-party deps—the fixture must stay stdlib/dxtbx only per Environment Freeze.
- Ensure mapping_context_fixture.json continues to log target/bragg stats added last loop; no key churn.
- Abort immediately if pytest reports <2 collected tests or if mapping fixture still shows calibration_path null; treat as blockers.
- Keep GPU/CPU device usage consistent across probe + pytest; this run requires CUDA for parity.

If Blocked
- If pytest cannot find the metadata sigma tiles or calibration config, capture the exact FileNotFoundError in the artifacts directory, annotate `docs/fix_plan.md` Attempts History with the path that failed, and stop before editing more code. Mark TOOLING-VIS-001 blocked pending asset recovery.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A fixtures must reuse the mapping calibration payload; this edit ensures the smoke config actually flows through refgeom_dataload.
- GEOMETRY-003 — Keep the canonical geometry overrides intact while adding calibration wiring so the mapping zero point stays aligned.
- SCALE-004 — DiffBragg calibration metadata (spot_scale_override, beam flux/exposure) must be threaded into simulate_forward_once; the new fixture plumbing fulfills this requirement.
- CONFORMANCE-001 — DB-AT selectors must archive diagnostics/logs even on failure; the How-To map keeps tee’d logs + mapping_context fixtures.

Pointers
- docs/fix_plan.md:261-344 — TOOLING-VIS-001 Attempts History + calibration mismatch notes.
- docs/TESTING_GUIDE.md:136-172 — DB-AT-028/029 selector contract, env vars, and artifact expectations.
- docs/data_dependency_manifest.md:30-125 — refgeom_dataload + mapping helper data-dependency rules (HKL, calibration, sigma paths).

Next Up (optional)
- Once calibration wiring lands, pivot to either HKL/scale provenance probes or Stage A loss-scale tuning depending on the updated telemetry.

Doc Sync Plan (Conditional)
- Not applicable (no new selectors this loop).

Mapped Tests Guardrail
- Re-run `pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only` after code changes; abort if fewer than two tests collect.

Hard Gate
- Do not call the loop done unless both `mapping_context_fixture.json` files in the artifacts tree report the smoke calibration path (non-null) and spot_scale_override != 1.0, and the pytest command completes (failures allowed but no crashes).

Normative Math/Physics
- Reference docs/spec-db-core.md §§32-92 for variance-weighted loss + sigma ladder details when interpreting the telemetry; no bespoke math.
