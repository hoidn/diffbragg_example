Summary: Fix mapping sigma-source routing so metadata tiles flow through `_select_sigma_readout` and the Stage A smoke selectors record the correct provenance before assessing ROI telemetry again.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests:
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/

Do Now
- Implement: dbex/vis/mapping.py::_select_sigma_readout and dbex/vis/mapping.py::emit_mapping_context_diagnostics — treat `sigma_readout_map_source="cli_map"` the same as `"external_lookup"`, keep the metadata sigma tensor instead of falling back to a scalar, and tag diagnostics with an explicit cli_map provenance string so mapping_context_fixture.json proves when metadata tiles are consumed.
- Validate: (1) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/mapping_cpu_gpu_metadata` to capture refreshed ROI stats + sigma provenance; (2) same env plus `DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/pytest_db_at_028_029.log` (expected failures OK but run must complete and persist mapping_context fixtures).
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/

How-To Map
1) `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1` (keep this shell for the rest of the loop).
2) `mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/{mapping_cpu_gpu_metadata,db_at_028,db_at_029}` so probe + pytest logs have a home.
3) `python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/mapping_cpu_gpu_metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/mapping_cpu_gpu_metadata/probe.log` and confirm the JSON shows `sigma_provenance="cli_map (args.sigma_map)"`.
4) `DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/db_at_029 pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/pytest_db_at_028_029_collect.log` and verify ≥2 tests collect before continuing.
5) Re-run the same env block with `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T150500Z/pytest_db_at_028_029.log`; inspect `db_at_028/mapping_context_fixture.json` and `db_at_029/mapping_context_fixture.json` to ensure they show the metadata sigma provenance + path.
6) If any command crashes, stop and capture the exact stderr/stdout in the artifacts directory; do not retry with modified env variables until the root cause is documented.

Pitfalls To Avoid
- Do not change Stage A core code paths—confine edits to dbex/vis/mapping.py helper logic.
- Never broaden the sigma fallback beyond the documented ladder; only accept the explicit map tiers per spec.
- Do not drop existing diagnostic keys (target/bragg stats, calibration_path, geometry metadata) when adjusting emit_mapping_context_diagnostics.
- Avoid assuming CUDA-only behavior; mapping probe must still work on CPU if CUDA is unavailable, so keep the helper device-neutral.
- Ensure the cli_map provenance string is deterministic—tests parse it verbatim.
- Keep env vars identical between collect-only and full pytest runs so fixtures don’t silently switch back to cli_override sigma.
- Don’t skip artifact creation; every command should tee logs into the new reports directory.
- Abort if <2 tests collect or if mapping_context fixtures still show the scalar provenance—treat as blockers, not soft failures.

If Blocked
- If metadata sigma assets are missing or `_select_sigma_readout` still returns the scalar after your change, capture the stack trace/log under the artifacts directory, note the missing path in docs/fix_plan.md Attempts History, and pause. Do not fall back to cli_override to get a passing run.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A diagnostics must consume the same calibration/sigma assets as mapping; keeping cli_map tiles intact satisfies this invariant.
- GEOMETRY-003 — Maintain the canonical refGeom inputs and zero-point alignment while touching the mapping helper so we don’t reintroduce orientation drift.
- PHYSICS-LOSS-004 — Sigma map ingestion must follow the documented format/positivity requirements; respecting the `sigma_map` ladder keeps us compliant.
- CONFORMANCE-001 — DB-AT selectors require full artifact capture even when assertions fail, so tee every command into the reports directory.

Pointers
- dbex/vis/mapping.py:70-220 — `_select_sigma_readout` and `build_mapping_stage_a_context` sigma-plumbing logic.
- docs/data_dependency_manifest.md:30-125 — Canonical provenance rules for refgeom_dataload, HKL, calibration, and sigma assets.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/db_at_028/mapping_context_fixture.json:1 — Evidence that sigma_provenance still reads "cli_override" even with cli_map tiles.

Next Up (optional)
- If metadata sigma routing works, re-assess ROI CC vs chi² deltas to decide whether to prioritize calibration scaling or HKL provenance next loop.

Doc Sync Plan (Conditional)
- Not required (no new selectors or renamed tests).

Mapped Tests Guardrail
- Run `pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only` and abort if fewer than two tests collect.

Hard Gate
- Do not call the loop complete unless both mapping_context_fixture.json files in the artifacts tree show `sigma_provenance` referencing the metadata cli_map input and contain the smoke calibration path, and the pytest command finishes (failures allowed but no crashes/hangs).

Normative Math/Physics
- Follow `docs/spec-db-core.md` §§32-92 (sigma ladder + variance-weighted chi²) and `docs/spec-db-workflow.md` Stage A mapping clauses when reasoning about these diagnostics—no ad-hoc math.
