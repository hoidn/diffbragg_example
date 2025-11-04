Summary: Port DiffBragg calibration metadata into the zero-iteration helper so DB_AT_024 can assert its intensity thresholds without relying on provisional xfail.
Mode: none
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/

Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once — accept DiffBragg calibration metadata (√spot_scale_override plus beam flux/exposure) loaded from the canonical `config_torch.json`, plumb it through a lightweight loader so zero-iteration simulations emit calibrated intensities, and update `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` to consume the same calibration fixture (copy `config_torch.json` into `tests/fixtures/golden_data/simple_cubic/`) and tighten assertions toward the ≥0.2 correlation / ≥0.90 localization thresholds.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
- Artifacts: Capture calibrated `mapping_metrics.json`, pytest log, and any new calibration JSON emitted by the helper under plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z
3. pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
4. pytest --collect-only tests -k DB_AT_024 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/collect_db_at_024.log

Pitfalls To Avoid:
- Do not derive scale factors from target data; calibration must come from DiffBragg metadata (config_torch.json).
- Keep SCALE-001 semantics (no pre-scaling of |F|); apply √spot_scale_override only post-simulation.
- Ensure new beam flux/exposure fields stay device/dtype neutral and JSON-serializable floats.
- Preserve current artifact policy (only write when DBAT024_ARTIFACT_DIR set; include new calibration JSON if created).
- Maintain DB_AT_024 selector discoverability; if thresholds remain unmet, update xfail reason with calibrated metrics.
- Retain trusted mask polarity and ROI slicing; no shortcuts that bypass loss mask.
- Avoid hard-coding repo-local absolute paths; resolve calibration fixtures relative to repo root/tests directory.
- Keep runtime under control (single simulator pass; no extra loops or global recomputations).
- Respect Environment Freeze (no package installs, no torch upgrades).
- Leave canonical golden tensors untouched; copy config artifacts into tests/fixtures rather than editing plans/active directly.

If Blocked:
- If calibration metadata is missing, log the missing file path in plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/blockers.md and flag the focus as blocked in docs/fix_plan.md Attempts History.
- If nanobrag_torch import fails, record the ImportError signature verbatim and stop; do not attempt installs.
- If pytest selector still xfails after calibration plumbing, capture updated metrics, document in blockers.md, and halt implementation for follow-up.

Findings Applied (Mandatory):
- SCALE-001 — Keep structure factors unscaled and apply calibration post-simulation only.
- SCALE-002 — Reapply DiffBragg √spot_scale_override as the global intensity factor.
- SCALE-003 — Source both √spot_scale_override and refined calibration metadata from DiffBragg outputs instead of heuristics.
- CONFORMANCE-001 — Maintain DB_AT_024 selector visibility with actionable diagnostics.
- TESTING-003 — Ensure pytest collection logs accompany the Active selector after updates.

Pointers:
- docs/spec-db-workflow.md:30 — Stage A global scale expectations for ADU mode.
- docs/architecture.md:88 — ADR-02 (ADU vs photon policy and learnable scale).
- docs/spec-db-conformance.md:43 — DB_AT_024 acceptance thresholds and artifact requirements.
- plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T012616Z/golden_dataset/torch/config_torch.json — DiffBragg calibration metadata (√spot_scale_override, flux, exposure).
- plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z/summary.md — Golden vs zero-iteration comparison results informing calibration plan.
- docs/TESTING_GUIDE.md:70 — Runtime flags and artifact policy for DB_AT_024.

Next Up (optional):
1. Once calibration lands, audit structure-factor sourcing to confirm MTZ amplitudes match DiffBragg refined `Fopt` before tightening thresholds further.

Doc Sync Plan (conditional): none — no new tests added.
