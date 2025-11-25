Summary: Quantify geometry deltas between refGeom and refined experiments so we can explain the Stage A mapping failure before touching production code.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_geometry_zero_points.py::main — introduce a T2 analysis script that loads named experiment cases (default: refgeom.expt, sp.proc/idx-0000_refined.expt, tests/fixtures/golden_data/simple_cubic/refined.expt), extracts unit cells, U/B/A* matrices, detector distance/beam center/axes, and beam vectors via dxtbx, then emits both per-case metrics and pairwise deltas vs the base case into <artifacts>/geometry_deltas/geometry_deltas.json so we can see how far the canonical geometry has drifted.
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_geometry_zero_points.py --cases refgeom idx_refined golden_refined --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/geometry_deltas | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/geometry_deltas/compare_geometry_zero_points.log; (2) same env pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/pytest_db_at_028_029_collect.log (stop if <2 tests collect); (3) same env plus DBAT028_ARTIFACT_DIR/DBAT029_ARTIFACT_DIR pointing at the new artifacts run pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/pytest_db_at_028_029.log and archive refreshed db_at_028/db_at_028_metrics.json + db_at_029/db_at_029_metrics.json even though the selectors still fail.

How-To Map
1) Export DBEX_SMOKE_SIGMA_SOURCE=metadata, DBEX_SMOKE_DETECTOR_SIZE=small, DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json, DBEX_SMOKE_HKL_PATH=scaled.mtz, KMP_DUPLICATE_LIB_OK=TRUE, and NANOBRAGG_DISABLE_COMPILE=1 for every command so the geometry probe and DB-AT selectors share inputs.
2) Write compare_geometry_zero_points.py with argparse (--cases, --out-dir, optional --base-case) that defines default cases (refgeom, idx_refined, golden_refined) pointing at the canonical refGeom assets, sp.proc/idx-0000_refined.expt, and tests/fixtures/golden_data/simple_cubic/refined.expt respectively; allow overrides via env/CLI so future loops can drop in additional cases.
3) For each case, load the experiment via dxtbx, extract unit cell (a,b,c,alpha,beta,gamma), orientation matrix U, B matrix, derived A*=U@B (store flattened 3x3 values), beam vector, detector distance, beam center (fast/slow mm), panel normal/fast/slow axes, and crystal setting angles; record everything as doubles to avoid rounding noise.
4) Compute pairwise deltas vs the base case (default refgeom) for each metric: absolute/relative differences for cell edges/angles, Frobenius norm of U/A* deltas plus implied rotation angle (use scipy/np.linalg.svd or scitbx.matrix to get angle), beam center shifts, detector distance deltas, and panel normal dot-products. Store these in a "deltas" section of geometry_deltas.json alongside a markdown summary for the report directory.
5) Run the script with AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md and tee stdout to geometry_deltas/compare_geometry_zero_points.log. Ensure the JSON and a short summary.md in the same folder explain which geometry differs most and by how much.
6) With the same env, run pytest --collect-only for DB-AT-028/029 (fail fast if fewer than 2 tests collect), then run the full pytest command so artifacts capture the current failure signature tied to this geometry analysis.

Pitfalls To Avoid
- Do not treat the large spot_scale_override (~3e17) as a bug again; golden configs use the same magnitude.
- Keep all geometry math in double precision so tiny rotations (<1e-4 rad) are measurable; avoid casting to float32.
- When computing deltas, compare everything in the same coordinate frame (e.g., use normalized rotation matrices before taking differences).
- Do not mutate the experiment objects or write back changes; this script MUST remain read-only analysis.
- Ensure the script gracefully reports missing cases or assets (e.g., idx_refined may be absent) and still emits partial results.
- Preserve the CONFORMANCE-001 artifact policy: archive logs/JSON even though pytest fails.

If Blocked
- If any experiment file is missing or ExperimentList fails to load, capture the traceback in compare_geometry_zero_points.log, write a short blocker note in summary.md, and stop before running pytest.
- If pytest --collect-only drops below 2 tests, attach the collect log, call out the missing selector, and do not run the full tests until the fixture issue is resolved.

Findings Applied (Mandatory)
- STAGEA-001 — Geometry probe must reuse the canonical Stage A/mapping assets so telemetry stays comparable.
- GEOMETRY-003 — Zero-point analysis has to respect the incremental UB baseline defined there.
- GEOMETRY-004 — Orientation deltas must be expressed in the same incremental UB framework so future fixes map cleanly onto Stage A.
- CONFORMANCE-001 — Even in failure we archive DB-AT artifacts verbatim; reruns must follow docs/spec-db-conformance.md.
- POLICY-001 — Read-only analysis only; no environment mutations or new dependencies.

Pointers
- docs/data_dependency_manifest.md:1 — Canonical list of Stage A/mapping assets and overrides.
- docs/spec-db-conformance.md:280 — DB-AT-028/029 acceptance rules we’re still violating.
- docs/TESTING_GUIDE.md:94 — Metadata sigma/Calib instructions for Stage smoke selectors.
- plans/active/TOOLING-VIS-001/implementation.md §Phase D — Context for the mapping alignment objectives and zero-point requirements.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/summary.md — Latest evidence that HKL/calibration swaps do not change the failure signature.

Next Up (optional)
- If geometry deltas identify a dominant drift (e.g., detector translation or U-matrix rotation), sketch the minimal refGeom update required so Stage A zero-point parity can be revalidated.

Doc Sync Plan (Conditional)
- None — we’re not adding or renaming selectors this loop.

Mapped Tests Guardrail
- Run pytest --collect-only for DB-AT-028/029 with the metadata env before the full run; abort implementation if fewer than 2 tests collect.

Hard Gate
- Do not mark the loop complete until geometry_deltas.json + summary.md exist and DB-AT-028/029 artifacts under plans/active/TOOLING-VIS-001/reports/2025-11-25T103500Z/ reflect the latest failure signature.

Normative Math/Physics
- Reference docs/spec-db-core.md §§82-92 when interpreting any ROI or chi-squared metrics that accompany the geometry analysis; do not restate the math in prose.
