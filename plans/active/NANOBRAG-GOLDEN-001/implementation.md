# NANOBRAG-GOLDEN-001 — Canonical DB-AT-001 Golden Dataset

## Phase A — Canonical tensor capture
> Status note (2025-10-29): DIFFBRAGG-001 resolved; rebuilt `simtbx_diffBragg_ext.so` (md5 1506a48bee414ffcec041083b1496a44). A2 capture can proceed once nanobrag_torch workflow is ready.

- [x] **A1 — Environment + dependency validation**: Evidence captured in `reports/2025-11-04T012616Z/canonical_capture.log` (`which python`, `nanobrag_torch` import, dataset paths) per `docs/spec-db-core.md:20-41`.
- [x] **A2 — DiffBragg baseline export**: DiffBragg tensors/configs persisted under `reports/2025-11-04T012616Z/golden_dataset/legacy/` with command log (`docs/forward_equivalence.md:21-37`).
- [x] **A3 — nanoBragg2 forward capture**: Canonical torch tensors + configs written to `reports/2025-11-04T012616Z/golden_dataset/torch/`, ROI dumps stored alongside (`docs/nanobrag_api.md:21-83`).
- [x] **A4 — Torch geometry pivot alignment**: `dbex/nanobrag_bridge.create_detector_config` emits DIALS XYZ angles; `roi_offset_summary.json` shows median_abs_offset=0.0 px (`reports/2025-11-04T012616Z/`).

## Phase B — Manifest + verification
- [x] **B1 — Manifest & metadata update**: Canonical `manifest.json`/`metadata.json` under `tests/fixtures/golden_data/simple_cubic/` include SHA256 + provenance (generated 2025-11-04T012816Z).
- [x] **B2 — Fixture + checksum tests**: `tests/dbex/test_db_at_001_parity.py::TestManifestIntegrity` + loader checksum guards validate canonical layout (`docs/TESTING_GUIDE.md:74-85`).
- [x] **B3 — Regeneration tooling**: `scripts/generate_simple_cubic_golden.py` documents canonical workflow and produced `reports/2025-11-04T012616Z/golden_dataset/` (`plans/nanobrag_integration_plan.md:32-88`).

## Phase C — Parity harness integration
- [x] **C1 — Harness dataset swap**: Parity harness consumes canonical tensors from `tests/fixtures/golden_data/simple_cubic/` (torch vs DiffBragg baseline, no synthetic noise).
- [x] **C2 — Threshold enforcement**: `TestDB_AT_001_Parity::test_db_at_001_parity_smoke` enforces correlation ≥0.2 and localization ≥0.9 with artifact logging + conditional xfail.
- [x] **C3 — Documentation sync**: Update `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, and `docs/index.md` with canonical dataset + new artifact paths (complete 2025-11-04T020930Z).

## Phase D — Closure
- [x] **D1 — Artifact archival**: Capture fresh parity log + metrics under `plans/active/NANOBRAG-GOLDEN-001/reports/<next_timestamp>/parity_harness/` referencing canonical tensors (captured 2025-11-04T020930Z).
- [x] **D2 — Knowledge base update**: Add durable lessons (e.g., detector Euler inversion guard) to `docs/findings.md` if not already recorded.
- [x] **D3 — Ledger wrap-up**: Update `docs/fix_plan.md` Attempts History + status once canonical parity rerun/log sync completes. (Completed 2025-11-04T030000Z with checksum guard entry and status flip.)
