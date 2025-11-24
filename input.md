Summary: Capture DB-AT-024 mapping telemetry and extend the Stage A refGeom driver so Phase D.A metrics (chi²/ROI CC/intensity) land under the new artifacts directory.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py::main — add an `--out-dir` argument plus JSON metric emission (chi² trace, variance_floor_masked_pixels, chi²-per-pixel, ROI CC vs data for mapping/stage_a_before/stage_a_after, global intensity ratios, zero-point deltas vs mapping) so Phase D.A2 evidence lands deterministically under the artifacts directory; use this output to author D.A3 `stage_a_mapping_diagnosis.md`.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT024_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/db_at_024 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/{db_at_024/,stage_a_refgeom_run/,stage_a_mapping_gap_metrics.json,stage_a_mapping_diagnosis.md}

How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` (all commands reference §2 selectors) and `mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/db_at_024` before running tests.
2. Mapping baseline per `docs/TESTING_GUIDE.md:118`: `DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT024_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/db_at_024 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` — copy the resulting `mapping_metrics.json` to `mapping_metrics_snapshot.json` inside the same folder.
3. Update `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py` (`parse_args`, `_run_canonical_stage_a`, and `main`) so `--out-dir` overrides the timestamp path and the run emits `stage_a_mapping_gap_metrics.json` containing the D.A2 quantities plus the raw chi² trace and masked pixel counts; keep existing PNG/report generation unchanged.
4. Run the updated driver on CPU with deterministic seeding: `python plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py --device cpu --steps 30 --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_refgeom_run` and verify the JSON metrics reference the same mapping data pulled in step 2.
5. Author `plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_mapping_diagnosis.md` summarizing chi²_per_pixel, ROI correlations (mapping vs Stage A before/after), and global intensity ratios versus the DB-AT-027/028/029 tolerances; include links to the JSON files and note any deltas that violate or satisfy the spec bands.
6. If the JSON metrics reveal pathological gaps (e.g., chi²_per_pixel > 1e2 or mean_abs_diff > 2e2), attach the failing excerpts to `mapping_diagnosis.md` and flag next steps (D.B0 zero-point probe or calibration plumbing) in the doc.

Pitfalls To Avoid
- Keep `simulate_forward_once` inputs/masks identical between DB-AT-024 and the Stage A driver; do not regenerate ROIs or change sigma policies mid-run.
- Respect `POLICY-001` — no pip installs or CUDA toggles beyond documented env vars.
- Preserve existing triptych/image output structure so downstream scripts are unaffected.
- Avoid re-sampling ROIs inside the driver; use `MappingStageAContext.inputs.panel_slices` exclusively.
- Ensure JSON floats are serializable (use `float()` casts) and avoid dumping NumPy arrays directly.
- Do not downgrade the DB-AT-024 selector when rerunning; treat failures as blockers and capture the full pytest log.
- Keep `--out-dir` optional and backwards compatible (default timestamped behavior).
- Leave Stage B/C toggles untouched; this loop is Stage A only.
- Execute commands on CPU to avoid CUDA nondeterminism (unless existing scripts already gate GPU usage).
- Reference spec tolerances verbatim in the diagnosis doc; no ad-hoc thresholds.

If Blocked
- If DB-AT-024 fails (e.g., missing sigma metadata), copy the pytest log to the artifacts directory, update `docs/fix_plan.md` Attempts History with the failure signature, and halt before modifying the driver.
- If the driver cannot locate refined assets, note the missing file(s) in `stage_a_mapping_diagnosis.md`, set `[TOOLING-VIS-001]` to `blocked` with the same evidence, and notify supervisor before touching Stage B/C code.

Findings Applied (Mandatory)
- GEOMETRY-003 — Stage A zero point must reuse mapping baseline misset; keep `MappingStageAContext` outputs authoritative while computing metrics.
- GEOMETRY-004 — UB incremental parameterization invariants require `bragg_before` reconstruction via `_build_final_bragg_from_stage_a_telemetry`; do not decompose A* ad-hoc.
- PHYSICS-LOSS-001 — Use the canonical variance-weighted chi² (sigma_floor clamp, detached denominator) when computing chi²_per_pixel.
- CONFORMANCE-001 — Treat DB-AT selectors as authoritative; capture pytest logs + mapping artifacts exactly as documented.
- REFINE-001 — Respect global scale hints from mapping calibration when reporting intensity ratios to avoid false positives from unbounded log_scale.

Pointers
- docs/spec-db-conformance.md:201 — DB-AT-027/028/029 tolerances for zero point, chi²_per_pixel, and ROI correlations.
- docs/spec-db-workflow.md:42 — Stage A mapping zero-point invariant and incremental UB constraints.
- docs/TESTING_GUIDE.md:118 — DB-AT-024 metadata mapping guard environment + artifact policy.
- plans/active/TOOLING-VIS-001/implementation.md:180 — Phase D.A checklist and deliverables.
- docs/fix_plan.md:200 — TOOLING-VIS-001 ledger entry (status, attempts, dependencies).

Next Up (optional)
- Prepare D.B0 zero-point probe instrumentation (engine-based no-op) once D.A metrics are in the reports directory.

Mapped Tests Guardrail
- DB-AT-024 selector collects exactly one test; verify `collect_db_at_024_metadata.log` reports 1 collected before marking the loop complete.

Hard Gate
- Keep DB-AT-024 active; if evidence shows chi² equality already holds, document it rather than loosening the tolerance.

Normative Math/Physics
- See docs/spec-db-conformance.md:201-280 for DB-AT-027/028/029 equations and docs/spec-db-workflow.md:42-58 for the mapping-aligned Stage A invariants that the new metrics must cite verbatim.
