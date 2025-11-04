Summary: Equip DB_AT_024 with DiffBragg-refined structure factors so the mapping selector meets its correlation/localization thresholds without an xfail.
Mode: none
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/

Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once — accept an explicit refined HKL payload (indices + amplitudes) so tests can feed DiffBragg `Fopt`; add a helper to read refined MTZ structure factors, teach DB_AT_024 to load `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz`, drop the provisional xfail, and update `scripts/generate_simple_cubic_golden.py` to persist/copy the refined MTZ (manifest + fixtures) for future runs.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
- Artifacts: Capture refreshed `mapping_metrics.json`, `mapping_metrics.csv`, pytest log(s), collect-only log, regenerated manifest, and refined MTZ under plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/refined_capture --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/golden_capture.log
3. export KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z
4. pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/pytest_db_at_024.log
5. pytest --collect-only tests -k DB_AT_024 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/collect_db_at_024.log

Pitfalls To Avoid:
- Do not rescale structure factors inside the helper; SCALE-001 forbids multiplying by √spot_scale.
- Keep √spot_scale post-simulation (SCALE-002) and ensure the override stays optional for fixtures without calibration.
- Fail fast if refined MTZ is missing; log minimal error and exit per Environment Freeze policy.
- Maintain ROI mask semantics and trusted mask polarity when switching amplitude sources.
- Ensure new helper returns CPU numpy arrays; avoid torch tensors to keep device/dtype neutrality.
- Update manifest.json deterministically (sorted keys) so git diffs stay minimal.
- Preserve DB_AT_024 artifact contract (metrics JSON + CSV) and include new metadata fields if added.
- Avoid touching plans/active assets directly in production code; only reference fixtures under tests/.
- Keep runtime bounded to one simulator pass; no added loops or gradcheck hooks.
- Do not delete `_temp.mtz` cleanup logic outside the intentional refined MTZ export path.

If Blocked:
- Missing refined MTZ: record the path that failed in plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/blockers.md and note the blocker in docs/fix_plan.md Attempts History.
- nanobrag_torch import failure: capture the ImportError text verbatim in blockers.md and halt; do not install packages.
- Thresholds still unmet after swap: persist updated metrics, restore provisional xfail with new values, and document gap + next steps in blockers.md before stopping work.

Findings Applied (Mandatory):
- CONFORMANCE-001 — Keep DB_AT_024 selector visible with authoritative command + artifacts (docs/findings.md:8).
- SCALE-001 — Structure factors must remain unscaled before simulation (docs/findings.md:15).
- SCALE-002 — Apply √spot_scale post-sim only (docs/findings.md:16).
- SCALE-003 — Require DiffBragg calibration metadata and refined |F| together (docs/findings.md:17).
- SCALE-004 — Calibration alone overshoots; tie in refined Fopt to resolve (docs/findings.md:27).
- TESTING-003 — Provide fresh pytest + collect-only logs for the Active selector (docs/findings.md:18).

Pointers:
- docs/spec-db-workflow.md:20 — Calibration policy and Stage A scale expectations.
- docs/spec-db-conformance.md:43 — DB_AT_024 correlation/localization thresholds.
- docs/architecture.md:88 — ADR-02 (ADU vs photon scale contract).
- docs/findings.md:15 — SCALE-001 unscaled structure factor rule.
- docs/findings.md:27 — SCALE-004 calibration + Fopt requirement.
- plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z/summary.md — Golden vs zero-iteration intensity analysis.
- plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/summary.md — Current refined-structure-factor plan and validation command.
- plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T012616Z/golden_dataset/torch/config_torch.json — Source of DiffBragg calibration metadata.
- tests/dbex/test_mapping_consistency.py:92 — Current zero-iteration baseline under calibration (pre-refined MTZ).

Next Up (optional): MAP-SCALE-002 — Automate ingest of DiffBragg Fopt for runtime pipelines once DB_AT_024 passes locally.

Doc Sync Plan (conditional): none — existing selector persists; update docs after successful run per Do Now.
