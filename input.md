Summary: Replace the bridge’s Euler extraction with the analytic XYZ inversion so the canonical DB-AT-001 tensors align pixel-for-pixel with dxtbx geometry.
Mode: none
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011029Z/

Do Now:
- Focus: NANOBRAG-GOLDEN-001
- Implement: dbex/nanobrag_bridge.py::create_detector_config
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011029Z/

How-To Map:
1. Edit `dbex/nanobrag_bridge.py::create_detector_config`: build rotation matrix `R = np.column_stack([panel.get_fast_axis(), panel.get_slow_axis(), panel.get_normal()])`, compute analytic Euler angles with `phi_y = -np.arcsin(np.clip(R[2,0], -1.0, 1.0))`, `phi_x = np.arctan2(R[2,1], R[2,2])`, `phi_z = np.arctan2(R[1,0], R[0,0])`, convert to degrees, and optional asserts that `angles_to_rotation_matrix` reconstructs `R` within 1e-9; remove the previous `r3_rotation_matrix_as_x_y_z_angles()` call.
2. Extend `tests/dbex/test_nanobrag_bridge_configs.py::test_detector_convention_custom` (or add a sibling test) to load `refGeom.expt` via `ExperimentListFactory`, call `create_detector_config`, build a `TorchDetectorConfig`/`TorchDetector`, and `np.testing.assert_allclose` the returned fast/slow/normal vectors to dxtbx axes with atol=1e-6. Guard the environments with `pytest.importorskip("nanobrag_torch")` to keep CPU-only runs green.
3. Generate a fresh canonical dataset in this checkout (no `_2` paths) into a new timestamp directory beneath `plans/active/NANOBRAG-GOLDEN-001/reports/`: `RUN_TS=$(date -u +%Y-%m-%dT%H%M%SZ)`; `REPORT_DIR=plans/active/NANOBRAG-GOLDEN-001/reports/$RUN_TS`; `mkdir -p "$REPORT_DIR"`; then `PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$REPORT_DIR/golden_dataset" --hkldebug "$REPORT_DIR/torch_hkl_debug.json" --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic --roi-dump "$REPORT_DIR/roi_triptychs"`.
4. Confirm alignment post-change: `python plans/active/NANOBRAG-GOLDEN-001/bin/summarize_roi_offsets.py --index-json "$REPORT_DIR/roi_triptychs/index.json" --write-json "$REPORT_DIR/roi_offset_summary.json"` (expect median_abs_offset ≤ 1 px) and spot-check manifest paths stay inside this workspace.
5. Run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee "$REPORT_DIR/pytest_db_at_001.log"`; archive generator stdout/stderr as `$REPORT_DIR/canonical_capture.log` and attach the offset summary + parity log in the report directory.
6. Update ledger/docs: append Attempts History entry with metrics and cite `$REPORT_DIR`, refresh `docs/fix_plan.md`/`plans/.../implementation.md` status, and note any new lessons in `docs/findings.md` if discovered; leave repo clean.

Pitfalls To Avoid:
- Do not reintroduce CUSTOM detector vectors—keep `DetectorConvention.DIALS` so pivot stays BEAM.
- Clamp the arcsin argument to [-1,1] before inversion to avoid math domain errors from floating noise.
- Ensure generator runs from this repository; manifests pointing at `diffbragg_example_2` violate MANIFEST-001.
- Preserve SCALE-001/002 fixes (no pre-scaling structure factors; keep √scale post sim) and HKL-ORIENT-001 beam-direction handling.
- Always export `KMP_DUPLICATE_LIB_OK=TRUE` for parity run and disable compile if gradcheck fixtures engage.
- Capture artifacts under the new timestamp directory only; avoid overwriting historical reports.
- Keep GPU/CPU neutrality—tests must pass on CPU-only boxes (use `importorskip` for torch GPU features where needed).
- Don’t leave the new test without collect-only evidence; ensure it runs under pytest selectors without skipping silently.
- Maintain Environment Freeze: no conda/pip installs or nanoBragg rebuilds.
- Guard against gimbal lock fallback; if `cos(phi_y)` ≈ 0, log and branch appropriately instead of returning bogus angles.

If Blocked:
- If Euler inversion blows up (e.g., |R[2,0]| > 1 + 1e-9), dump the offending matrix and panel id to `$REPORT_DIR/errors.log`, revert the code tweak in-place, log the blocker in `docs/fix_plan.md`, and halt for supervisor guidance.
- If generator or pytest crashes, tee stderr to `$REPORT_DIR/failure.log`, preserve stack traces, update Attempts History with the failure signature, and stop—do not chase environment fixes solo.

Findings Applied (Mandatory):
- MANIFEST-001 — Keep manifest emission scoped to tensors verified in this workspace; re-run validation after regeneration.
- SCALE-001 — Avoid double-applying structure-factor scaling when refitting the bridge.
- SCALE-002 — Ensure the √scale post-simulation factor remains active and documented in metrics.
- HKL-ORIENT-001 — Maintain sample→source incident beam direction so HKL grids stay populated.

Pointers:
- docs/config_crosswalk.md:15 — Detector mapping requirements and angle conventions.
- docs/nanobrag_api.md:32 — DetectorConfig fields (convention, pivot, masks).
- dbex/nanobrag_bridge.py:232 — Current geometry extraction logic to replace.
- tests/dbex/test_nanobrag_bridge_configs.py:80 — Detector config test harness to extend for axis checks.
- docs/fix_plan.md:15 — Initiative Attempts History and exit criteria snapshot.
- plans/active/NANOBRAG-GOLDEN-001/implementation.md:20 — Phase A checklist for canonical tensor capture.

Next Up (optional):
1. If offsets fall below 1 px, proceed to Phase B1 manifest/metadata rewrite.
2. After parity metrics improve, tighten DB_AT_001 thresholds per spec in Phase C2.
