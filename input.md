Summary: Derive DIALS detector rotations in the torch bridge and regenerate the canonical DB-AT-001 dataset to eliminate peak offsets.
Mode: none
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/

Do Now:
- Focus: NANOBRAG-GOLDEN-001
- Implement: dbex/nanobrag_bridge.py::create_detector_config
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/

How-To Map:
1. Update `dbex/nanobrag_bridge.py::create_detector_config` to extract per-panel fast/slow/normal axes, form a rotation matrix with `scitbx.matrix.sqr`, convert to XYZ radians via `r3_rotation_matrix_as_x_y_z_angles`, then store the degree values in `DetectorConfig.detector_rotx_deg`, `.detector_roty_deg`, `.detector_rotz_deg`; keep beam center swap + square-pixel guard.
2. Ensure multi-panel safety: if more than one panel appears, iterate per panel and raise a clear error when axes fail `is_r3_rotation_matrix`.
3. Refresh docs so `docs/nanobrag_api.md` and `docs/config_crosswalk.md` describe DIALS rotations instead of CUSTOM basis vectors (note BEAM pivot preservation).
4. Regenerate canonical tensors with DIALS rotations:
   ```bash
   PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE \
   python scripts/generate_simple_cubic_golden.py \
     --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/golden_dataset \
     --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/torch_hkl_debug.json \
     --emit-manifest \
     --fixtures tests/fixtures/golden_data/simple_cubic \
     --roi-dump plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/roi_triptychs
   ```
5. Summarize offsets to confirm success (expect median_abs_offset ≤1 px, torch_max ≈ diffbragg_max):
   ```bash
   python plans/active/NANOBRAG-GOLDEN-001/bin/summarize_roi_offsets.py \
     --index-json plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/roi_triptychs/index.json \
     --write-json plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/roi_offset_summary.json
   ```
6. Run parity selector and tee logs to artifacts:
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/pytest_db_at_001.log
   ```
7. Archive generator stdout (`canonical_capture.log`) and updated metrics/manifest under the same report directory.

Pitfalls To Avoid:
- Do not revert SCALE-001/002 fixes; keep post-sim √scale applied once.
- Preserve BEAM pivot semantics—no `DetectorConvention.CUSTOM` basis vectors.
- Ensure rotation matrix validation before converting to Euler angles; guard against numerical drift.
- Keep `[panel, slow, fast]` ordering intact when touching generator outputs.
- Stay within Environment Freeze; no package installs or rebuilds this loop.
- Retain manifest paths within this workspace per MANIFEST-001 guard.
- Capture ROI + parity artifacts using the new timestamped directory only.
- Keep pytest selector xfail expectation intact; document if status changes.
- Maintain device neutrality (avoid hard-coded CUDA-only paths during generator run).
- Avoid writing ad-hoc scripts outside `plans/active/.../bin`; reuse inline probes in summary only.

If Blocked:
- If `nanobrag_torch` import fails or generator errors, capture the traceback snippet in `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/errors.log`, mark `docs/fix_plan.md` Attempts History with the error signature, set input Mode=Docs on next loop, and halt implementation until resolved.
- If computed rotations still yield >1 px median offsets, stop after logging metrics, attach ROI overlays, and record the regression in Attempts History before proceeding.

Findings Applied (Mandatory):
- MANIFEST-001 — Keep manifest emission bound to local tensor paths; validate SHA entries post-regeneration.
- SCALE-001 — Do not rescale structure factors again during generation; only torch outputs receive the √scale factor.
- SCALE-002 — Ensure post-simulation global scale remains active and is reported in panel_metrics.json.
- HKL-ORIENT-001 — Maintain correct incident beam direction (sample→source) when mapping DetectorConfig to avoid HKL drift.

Pointers:
- docs/config_crosswalk.md:15 — Detector mapping inputs/outputs and required guards.
- docs/nanobrag_api.md:32 — DetectorConfig expectations and convention notes.
- docs/forward_equivalence.md:46 — DB-AT-001 artifact checklist for parity runs.
- docs/TESTING_GUIDE.md:74 — Selector flags and environment requirements for DB_AT_001.
- docs/spec-db-tracing.md:15 — ROI instrumentation requirements for first-divergence analysis.
- docs/fix_plan.md:15 — Initiative metadata and Attempts History for NANOBRAG-GOLDEN-001.

Next Up (optional):
1. Begin B1 manifest/metadata rewrite once geometry parity is validated.
2. Draft parity threshold tightening plan (C2) based on updated localization metrics.
