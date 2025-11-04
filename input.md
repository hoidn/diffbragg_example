Summary: Persist DiffBragg-refined geometry in the golden fixtures and DB_AT_024 harness so the mapping guard meets its correlation/localization thresholds.
Mode: Parity
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/
Do Now:
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden (persist refined experiment/reflection assets + update manifest metadata) and tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::canonical_assets (load refined geometry, retain fallback).
- Pytest: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
- Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/refined_capture --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/golden_capture.log
2. Verify refined assets landed: ls tests/fixtures/golden_data/simple_cubic/{refined_structure_factors.mtz,refined.expt,refined.refl} > plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/fixture_inventory.txt
3. Update scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden per summary (copy refined .expt/.refl, update manifest metadata to cite refined sources, keep MANIFEST-001 guards), then adjust tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::canonical_assets to prefer refined geometry with fallback to legacy assets.
4. Run AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/pytest_db_at_024.log
5. Capture fresh metrics snapshot: jq -r '"corr_median=" + (.corr_median|tostring) + "\nlocalization_success_rate=" + (.localization_success_rate|tostring)' plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/mapping_metrics.json > plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/metrics_snapshot.txt
6. Sanity-check selector discovery: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only -k DB_AT_024 > plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/collect_db_at_024.log
7. Update docs/TESTING_GUIDE.md:71 and docs/development/TEST_SUITE_INDEX.md:27 with new passing metrics + artifact paths; note refined geometry requirement per SCALE-004.
8. Note outcomes + log references in docs/fix_plan.md Attempts History and plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/summary.md before handoff back to Galph.
Pitfalls To Avoid:
- Do not delete or overwrite legacy refGeom assets; provide fallback path for older workflows.
- Keep MANIFEST-001 guard intact—validate refined files exist before manifest/copy steps.
- Preserve SCALE-001/002 behavior: never pre-scale structure factors; apply sqrt(spot_scale_override) post-sim only.
- Respect Environment Freeze: no package installs or external downloads.
- Ensure DBAT024_ARTIFACT_DIR points at this loop’s report dir so metrics land under plans/active/MAP-SCALE-001.
- Maintain device neutrality in loader changes (no `.cuda()` assumptions).
- Capture pytest logs via tee; missing logs break artifact expectations.
- Update docs in sync with evidence; stale metrics in TESTING_GUIDE/INDEX violate TESTING-003.
- Keep refined assets out of gitignore—confirm they appear in fixtures and manifests.
If Blocked:
- Stop, capture failing metrics/logs under plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/, append blocker note to blockers.md, and record the issue plus selector output in docs/fix_plan.md Attempts History. Ping Galph with failure signature.
Findings Applied (Mandatory):
- SCALE-001 — Leave structure-factor amplitudes unscaled until after simulation; refined loader must honor this.
- SCALE-002 — Apply sqrt(spot_scale_override) post-sim only; confirm calibration metadata still flows.
- SCALE-004 — Refined Fopt require matching DiffBragg-refined geometry; plan persists both assets.
- TESTING-003 — Keep selector docs + artifact paths current after metrics change.
- CONFIG-001 — Loss masks/trusted masks must remain boolean when persisted or loaded.
Pointers:
- docs/spec-db-conformance.md:46 — DB_AT_024 acceptance thresholds to enforce.
- docs/TESTING_GUIDE.md:71 — Current DB_AT_024 entry (needs metric refresh + refined geometry note).
- docs/development/TEST_SUITE_INDEX.md:27 — Suite registry row to update post-pass.
- scripts/generate_simple_cubic_golden.py:736 — Refined MTZ persistence block to extend for .expt/.refl.
- tests/dbex/test_mapping_consistency.py:64 — canonical_assets fixture to swap to refined geometry.
Next Up (optional):
- MAP-SCALE-001 B-side: if time remains, draft notes for MAP-SCALE-002 on automating refined asset ingestion for additional datasets.
