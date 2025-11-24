# TOOLING-VIS-001 — Phase D.A Evidence Plan (2025-11-24T213251Z)

## Objective
Capture ground-truth mapping telemetry and canonical Stage A LBFGS outputs so we can quantify the current Stage A vs mapping gap (chi², ROI CCs, global intensity). This satisfies checklist D.A0–D.A3 ahead of the DB-AT-027 zero-point probe.

## Scope
1. Refresh DB-AT-024 metadata mapping guard evidence under this initiative's reports directory.
2. Extend `generate_stage_a_refgeom_roi_triptychs_adam.py` with deterministic `--out-dir` support plus JSON metric emission (chi² trace, variance_floor_masked_pixels, ROI CCs vs data/mapping, global intensity ratios).
3. Run the updated driver against the canonical simple_cubic fixture, write its outputs to the shared artifacts directory, and synthesize `stage_a_mapping_diagnosis.md` that cites spec tolerances (`docs/spec-db-conformance.md:201-280`, `docs/spec-db-workflow.md:42-58`).

## Validation Inputs
- **Mapping baseline:** `pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` with `DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full DBAT024_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/db_at_024` (per `docs/TESTING_GUIDE.md:118`).
- **Stage A evidence:** Updated driver invoked as `python plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py --device cpu --steps 30 --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_refgeom_run`.

## Deliverables
- `db_at_024/mapping_metrics_snapshot.json` (chi², clamp fraction, median ROI CC, scale ratios).
- `stage_a_refgeom_run/stage_a_mapping_gap_metrics.json` (chi² per pixel, ROI CC vs data for mapping/stage_a_before/stage_a_after, global intensity ratios, zero-point deltas vs mapping).
- `stage_a_mapping_diagnosis.md` summarizing the observed delta, citing spec tolerances, and noting whether D.A2 values meet/violate expectations.

## Next Steps
Once D.A artifacts are in place, proceed to D.B0 (zero-point probe) using the same driver outputs and begin plumbing calibration payloads into `run_nanobrag_refinement` (D.C0–D.C2).
