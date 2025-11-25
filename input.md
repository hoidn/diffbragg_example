Summary: Reuse the canonical refGeom geometry (even when metadata sigma tiles are requested) so Stage A mapping and DB-AT-028/029 stop inheriting the ~1° refined-orientation drift that drives ROI anti-correlation.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/

Do Now
- Implement: tests/conftest.py::refgeom_dataload — decouple sigma sourcing from geometry by introducing `DBEX_SMOKE_GEOM_PATH` (defaults to the refGeom/refGeom_small experiments) and `DBEX_SMOKE_SIGMA_MAP_PATH` so metadata sigma tiles feed `DataLoad.args.sigma_map` instead of swapping in `sp.proc/idx-0000_refined.expt`; copy the canonical detector/beam/crystal onto the DataLoad when the loaded experiment’s U-matrix disagrees (>5e-4 rad) and record the resolved geometry path + rotation delta in the mapping/stage_a diagnostics.
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/mapping_cpu_gpu_canonical | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/mapping_cpu_gpu_canonical/probe.log; (2) same env pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/pytest_db_at_028_029_collect.log (stop if <2 tests); (3) same env plus DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T113500Z/pytest_db_at_028_029.log and archive refreshed metrics JSONs showing mapping ROI CC ≥0.2.

How-To Map
1) Export the env block shown above (GEOM path points at refGeom_small when using the small detector; use refGeom.expt if you switch to full) so both the mapping probe and pytest see the same canonical geometry, sigma tiles, HKL file, and calibration bundle.
2) Update `smoke_dataset_paths` to stop mutating `expt_path` when `smoke_sigma_source=="metadata"`; instead resolve the sigma-map path (env override or default `sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl`), validate it exists, and stash it on the dataclass so `refgeom_dataload` can pass it through `args.sigma_map`.
3) In `refgeom_dataload`, load the canonical experiment from `DBEX_SMOKE_GEOM_PATH` after instantiating `DataLoad`, compute the rotation angle between `dataload.Expt.crystal.get_U()` and the canonical U (use the helper from `compare_geometry_zero_points.py`), and when the angle exceeds 5e-4 rad (or any detector origin differs), overwrite `dataload.Expt`, `dataload.detector`, `dataload.beam`, and `dataload.crystal` with deep copies from the canonical experiment; keep the original DataLoad data/background arrays as-is.
4) Persist the resolved `geometry_path` and measured `rotation_delta_deg` into both the mapping context diagnostics (`emit_mapping_context_diagnostics`) and the DB-AT-028/029 metrics JSONs right next to the existing `dataset_paths` block so regressions are obvious.
5) Re-run `compare_mapping_forward_cpu_gpu.py --out-dir .../mapping_cpu_gpu_canonical` and confirm ROI CC/scale ratios now match between CPU/GPU and show positive correlation; stash the JSON + log under the new artifacts directory.
6) Re-run pytest collect + full DB-AT-028/029 under the canonical env so refreshed metrics/telemetry demonstrate whether the geometry fix restored chi²/ROI behavior; stop early if select count <2 and report the gap in summary.md.

Pitfalls To Avoid
- Do not mutate production `dbex.*` modules outside the smoke fixture plumbing; this fix belongs entirely in the test/helpers layer.
- Keep geometry comparisons in double precision; casting to float32 will hide the 0.95° drift we’re chasing.
- Preserve the existing metadata skip behavior: if the sigma-map pickle is missing, skip the selectors with a clear message instead of falling back silently to refined geometry.
- Thread canonical paths through diagnostics verbatim; do not resolve symlinks or strip prefixes, otherwise Attempts History cannot match future logs.
- Make sure the mapping probe uses the same `DBEX_SMOKE_GEOM_PATH` and sigma-map overrides as pytest; mixed settings will reintroduce false mismatches.
- Never delete or overwrite `sp.proc/idx-0000_sigma_metadata.expt`; the manifest documents it for reproducibility even if we no longer consume it directly.
- Respect Environment Freeze: no pip installs or conda tweaks while editing fixtures.
- Keep ROI-mask logic untouched; only geometry/sigma sourcing should change this loop.
- Do not downgrade the DB-AT gates; we need chi² ≤1e2 and ROI CC ≥0.2 once geometry is corrected.
- Remember to capture the new diagnostics into artifacts even if commands still fail.

If Blocked
- If the sigma-map pickle is missing, capture the `FileNotFoundError` in summary.md, update docs/fix_plan.md Attempts History with the missing asset note, and stop after pytest --collect-only (selectors should skip cleanly).
- If the canonical geometry override still reports <5e-4° delta, document the measurements in mapping_cpu_gpu_canonical/mapping_forward_cpu_gpu.json and hold off on code changes until we gather more evidence.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A/mapping artifacts must share identical inputs; canonical geometry override enforces this.
- GEOMETRY-003 — Zero-point alignment uses the incremental UB baseline, so overrides must copy the baseline crystal exactly.
- GEOMETRY-004 — Orientation deltas have to be measured/recorded so future UB realignment work can reason about them.
- CONFORMANCE-001 — DB-AT selectors still archive metrics/logs even when they fail during this fix.

Pointers
- docs/data_dependency_manifest.md:1 — Lists the Stage A smoke dataset inputs we’re updating (sigma map vs geometry separation).
- tests/conftest.py:72 — smoke_dataset_paths/refgeom_dataload helpers that swap experiments today.
- plans/active/TOOLING-VIS-001/bin/compare_geometry_zero_points.py:1 — Reference rotation-angle math reused for the guard.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/summary.md — Geometry delta evidence motivating this fix.
- docs/TESTING_GUIDE.md:94 — Canonical env vars for DB-AT-028/029 (sigma/calibration ladder expectations).

Next Up (optional)
- If geometry override succeeds, resurrect `compare_mapping_dataset_metrics.py` to compare refGeom vs refined MTZ combos under the fixed geometry to pinpoint remaining scale issues.

Doc Sync Plan (Conditional)
- None — no new selectors; update docs/data_dependency_manifest.md inline with the code changes above.

Mapped Tests Guardrail
- Abort immediately if pytest --collect-only for DB-AT-028/029 returns fewer than 2 tests; fix the fixture/file paths before rerunning the full selectors.

Hard Gate
- Do not call the loop done unless mapping_cpu_gpu_canonical/mapping_forward_cpu_gpu.json shows ROI CC ≥0.2 and the DB-AT-028/029 metrics JSONs capture the geometry override metadata (paths + rotation delta) alongside the improved chi²/CC measurements.

Normative Math/Physics
- Reference docs/spec-db-core.md §§82‑92 for the variance-weighted chi² and ROI correlation definitions when interpreting the refreshed diagnostics; do not restate the formulas in prose.
