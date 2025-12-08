# DB-AT-023 — Calibration Policy Guard (ADU vs Photons)

## Phase A — Baseline validation & probes
- [x] A1: Reality-check canonical assets (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`) and capture inventory log under reports. (Complete: i=153, 2025-12-08T022101Z — cross-referenced i=143 validation, all 4 assets VALID)
- [x] A2: Reproduce calibration context by instantiating `DataLoad` with canonical args; record background-subtracted ROI sample metrics (mean, std, ROI sums) to anchor acceptance thresholds. (Complete: i=153, 2025-12-08T022101Z — 92 ROIs, mean=62.66 ADU, no sigma_readout_map)
- [x] A3: Cross-reference normative sources (`docs/spec-db-workflow.md §4`, `docs/architecture.md §13`, `docs/config_crosswalk.md`) and summarize calibration expectations (photon conversion vs ADU + global scale) inside report summary. (Complete: i=153, 2025-12-08T022101Z — calibration_policy_summary.md)

## Phase B — Implementation & testing
- [ ] B1: Extend `dbex.refine_one.create_parser` and downstream plumbing to accept optional `--adu-per-photon` (float > 0), threading the value into `DataLoad`/bridge calls.
- [ ] B2: Update `dbex.nanobrag_bridge.prepare_refinement_inputs` (and `RefinementInputs`) to apply photon conversion when `adu_per_photon` is provided, preserve ADU otherwise, and surface `target_representation` plus `global_scale_hint` metadata.
- [ ] B3: Author `tests/dbex/test_calibration_policy.py` (DB_AT_023) with fixtures covering photon conversion, ADU path (scale hint present), and guardrail enforcement for invalid/non-positive `adu_per_photon`; ensure tests reference canonical assets when available and use synthetic inputs otherwise.
- [ ] B4: Run mapped pytest commands:
  - `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_calibration_policy.py -k DB_AT_023`
  - `pytest --collect-only tests -k DB_AT_023`

## Phase C — Documentation & artifact sync
- [ ] C1: Persist artifacts under `plans/active/DB-AT-023/reports/<timestamp>/` (pytest logs, collect logs, calibration_metrics.json capturing photon vs ADU comparisons).
- [ ] C2: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to promote DB_AT_023 selector to Active with environment flags and artifact references; ensure `docs/spec-db-conformance.md` calibration section reflects new guard.
- [ ] C3: Append durable calibration lessons to `docs/findings.md` if new guardrails emerge (e.g., minimum viable `adu_per_photon`, representation drift checks) and log Attempts History entry in `docs/fix_plan.md`.
