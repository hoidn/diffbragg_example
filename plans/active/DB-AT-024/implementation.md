# DB-AT-024 — Mapping Consistency Guard

## Phase A — Baseline validation & probes
- [ ] A1: Confirm canonical assets present (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`, golden tensors) and log inventory under reports.
- [ ] A2: Reproduce zero-iteration baseline by loading `DataLoad` with canonical inputs; capture reference metrics for `data - background` (per-panel mean/max, ROI count, loss-mask coverage) to anchor acceptance thresholds.
- [ ] A3: Summarize normative expectations from `docs/spec-db-conformance.md` (workflow integration), `docs/forward_equivalence.md` (correlation/localization math), and `docs/spec-db-tracing.md` (diagnostic artifacts) inside report summary to guide implementation.

## Phase B — Implementation & testing
- [ ] B1: Extract a reusable zero-iteration helper (e.g., `simulate_forward_once`) from `dbex.refine_one.run_nanobrag_backend` that returns `(bragg, target_adu, target_photons, loss_mask, panel_slices, diagnostics)` without touching HDF5; ensure helper reuses `prepare_refinement_inputs` and honors ADU/photon metadata.
- [ ] B2: Author `tests/dbex/test_mapping_consistency.py` (selector DB_AT_024) that samples canonical ROIs, computes ROI correlation and central-half-box localization against `data - background`, persists metrics JSON/CSV under `$DBAT024_ARTIFACT_DIR`, and emits actionable assertions for threshold breaches.
- [ ] B3: Integrate helper with existing parity utilities (`tests/fixtures/parity_loader.py`) to avoid metric drift; ensure tests cover both success path (canonical assets) and skip/xfail behavior when assets missing.
- [ ] B4: Run mapped pytest commands:
  - `DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/<timestamp> KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_mapping_consistency.py -k DB_AT_024`
  - `pytest --collect-only tests -k DB_AT_024`

## Phase C — Documentation & artifact sync
- [ ] C1: Archive pytest logs, collect-only output, and metrics artifacts (JSON/CSV, optional overlays) under `plans/active/DB-AT-024/reports/<timestamp>/`.
- [ ] C2: Promote DB_AT_024 rows in `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, and `docs/spec-db-conformance.md` to Active with environment flags, thresholds, and artifact references.
- [ ] C3: Record Attempts History entry in `docs/fix_plan.md`, append new lessons (if any) to `docs/findings.md`, and verify `docs/index.md`/`docs/prompt_sources_map.json` reference the selector.
