Summary: Crop the metadata sigma-map to the refGeom_small window and rewire the Stage A smoke fixtures so metadata sigma tiles can be consumed without swapping experiments, then rerun the mapping probe and DB-AT-028/029 under the canonical geometry.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/

Do Now
- Implement: tests/conftest.py::refgeom_dataload — add plan-local sigma-map support for the cropped refGeom_small detector window by (a) authoring `plans/active/TOOLING-VIS-001/bin/crop_sigma_map_to_window.py::main` to slice `sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl` into a 1024×1024 pickle (fast [751,1775), slow [719,1743]) under `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl`, (b) defaulting `smoke_dataset_paths` to that cropped file whenever `smoke_detector_size=="small"` and metadata sigma is requested while preserving the `DBEX_SMOKE_SIGMA_MAP_PATH` override, and (c) updating docs/data_dependency_manifest.md to document the new asset + rotation-delta diagnostics. After rebuilding the fixture, ensure `emit_mapping_context_diagnostics` records the geometry metadata and sigma-map provenance from the new asset.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/pytest_db_at_028_029.log (expect both selectors to run without the sigma-map ValueError).

How-To Map
1) mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/{mapping_cpu_gpu_canonical,db_at_028,db_at_029} and capture all logs (script stdout, mapping probe, pytest collect/full) into this directory.
2) KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/crop_sigma_map_to_window.py --sigma-map sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl --fast-start 751 --slow-start 719 --width 1024 --height 1024 --output sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl --report plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/crop_sigma_map_report.json | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/crop_sigma_map.log, then record sha256 + size of the new pickle in the report.
3) Export the canonical env block used in Do Now so both the mapping probe and pytest share the same geometry, HKL, calibration, and sigma-map assets; keep DBEX_SMOKE_SIGMA_MAP_PATH pointed at the cropped pickle.
4) Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=metadata ... python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/mapping_cpu_gpu_canonical | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/mapping_cpu_gpu_canonical/probe.log`, then confirm `mapping_forward_cpu_gpu.json` shows ROI CC ≥ 0.2 with matching CPU/GPU stats and records the geometry metadata.
5) Run pytest --collect-only with the same env to ensure both DB-AT selectors are discoverable, tee the output to `pytest_db_at_028_029_collect.log`, and stop if the collection count is <2.
6) Run the validating pytest command from Do Now to capture refreshed db_at_028/db_at_029 metrics JSONs; verify the ValueError is gone, mapping telemetry references the cropped sigma-map, and ROI CC/chi² signatures are updated even if thresholds still fail.

Pitfalls To Avoid
- Do not mutate `dbex/data_load.py`; keep all sigma-map cropping logic in the plan-local script and fixture to avoid side effects on production ingestion.
- Preserve dtype/order when slicing the pickle (panel-major, slow×fast); a transposed crop will silently corrupt sigma weights.
- Keep the original metadata pickle untouched—write the cropped file under `sp.proc/refGeom_small/` and document provenance.
- When wiring defaults in `smoke_dataset_paths`, respect `DBEX_SMOKE_SIGMA_MAP_PATH` so other datasets (full detector, future overrides) remain configurable.
- Ensure the new script emits a manifest/report so future loops can verify the crop parameters without re-reading README.md.
- Do not relax the DB-AT tolerances; the goal is to unblock test execution, not lower the bar.
- Keep geometry comparisons in float64; the 0.95° rotation delta disappears in float32 and reintroduces silent drift.
- Avoid deleting existing artifacts in `plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/`; we need the failing log for Attempts History.
- Remember Environment Freeze: use stdlib/numpy only—no pip install during script authoring.
- When editing docs/data_dependency_manifest.md, describe both the cropped and full-detector sigma-map assets so provenance stays clear.

If Blocked
- If `sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl` is missing, document the FileNotFoundError in `plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/summary.md`, update docs/fix_plan.md Attempts History with the error signature, and stop after pytest --collect-only.
- If the cropped pickle still loads with a shape mismatch, log the exact dimensions plus crop parameters, attach the report, and mark the loop blocked (do not downgrade the selectors).

Findings Applied (Mandatory)
- STAGEA-001 — Stage A/mapping artifacts must share identical inputs; sigma-map cropping keeps metadata tiles aligned to the canonical geometry.
- GEOMETRY-003 — Zero-point alignment depends on the refGeom baseline, so overriding geometry and sigma tiles must copy that baseline exactly.
- GEOMETRY-004 — Record the rotation delta and geometry provenance so future UB realignment work can audit drift.
- CONFORMANCE-001 — DB-AT selectors must archive diagnostics/logs even when they fail or error; capture updated metrics JSONs regardless of outcomes.

Pointers
- tests/conftest.py:80-260 — Current geometry/sigma plumbing that now triggers the sigma-map shape mismatch.
- sp.proc/refGeom_small/README.md — Source of the 751/719 crop window for the small detector assets.
- plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/refGeom_small_report.json — JSON record of the crop parameters to reuse in the script.
- dbex/data_load.py:43-120 — Sigma-map loader enforcing the (panel, slow, fast) shape that currently errors on the metadata pickle.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/pytest_db_at_028_029.log — Error signature showing the (2527,2463) vs (1024,1024) mismatch we must resolve before re-running the selectors.

Next Up (optional)
- Once metadata sigma threads cleanly, rerun DB-AT-028/029 at the full detector size to compare ROI CC improvements against the small-detector fix.

Doc Sync Plan (Conditional)
- Update docs/data_dependency_manifest.md immediately after the code/script changes to reflect the new cropped sigma-map asset; no new selectors were added so no registry sync is required.

Mapped Tests Guardrail
- Abort if `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` yields fewer than 2 tests; fix fixture imports or env paths before running the full selectors.

Hard Gate
- Do not call the loop done unless `mapping_cpu_gpu_canonical/mapping_forward_cpu_gpu.json` records ROI CC ≥ 0.2 with matching CPU/GPU stats and the DB-AT-028/029 pytest run completes without the sigma-map ValueError (failures allowed but execution must finish and archive metrics).

Normative Math/Physics
- Follow docs/spec-db-core.md §§32-40 and 82-92 for the sigma-map tensor shape plus variance-weighted chi²/ROI correlation definitions when validating the cropped sigma tiles and mapping probe outputs.
