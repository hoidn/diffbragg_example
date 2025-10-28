Summary: Plan Phase B bridge work so Detector/Beam/Crystal configs hydrate nanobrag_torch from dxtbx metadata.
Mode: TDD
Focus: TORCH-BRIDGE-001 — Bridge DataLoad to nanobrag_torch
Branch: integration
Mapped tests: python -m pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py
Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/{do-now-notes.md,pytest.log,config_snapshots.json}
Do Now:
1. TORCH-BRIDGE-001.B1 — Use plans/active/TORCH-BRIDGE-001/implementation.md Phase B checklist to author detector-config unit tests (beam center swap, sample→source vector, mask 0/1 float) and implement helper returning per-panel DetectorConfig objects; tests: python -m pytest -v tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping
2. TORCH-BRIDGE-001.B2 — Extend the same plan checklist to cover Beam/CrystalConfig hydration (wavelength, polarization fallback, MOSFLM A* injection, stills phi defaults) with fixtures and implementation; tests: python -m pytest -v tests/dbex/test_nanobrag_bridge_configs.py::TestBeamCrystalConfigMapping
3. TORCH-BRIDGE-001.B1-B2 — Update plans/active/TORCH-BRIDGE-001/implementation.md and docs/fix_plan.md Attempts History with outcomes and stash pytest + helper notes under the artifact path; tests: none — process+docs
Priorities & Rationale:
- docs/spec-db-core.md:35-41 requires DetectorConfig distance/beam-center/sample→source mapping with square-pixel guard.
- docs/config_crosswalk.md:15-66 spells out Detector/Beam/Crystal field mappings that Phase B must satisfy.
- docs/dxtbx_api.md:5-50 details the source methods (panel.get_* and beam/crystal accessors) the helper must consume.
- docs/nanobrag_api.md:23-58 documents DetectorConfig/BeamConfig/CrystalConfig expectations (beam_center_s, MOSFLM A*, polarization defaults).
- plans/nanobrag_integration_plan.md:33-78 keeps Phase 1 scope aligned with broader integration sequencing.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE before running pytest (torch import requirement).
- mkdir -p plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z && tee pytest.log via python -m pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py | tee plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/pytest.log
- Write planning notes + config snapshots to plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/do-now-notes.md (include spec cites, command, runtime).
- After implementation, update plans/active/TORCH-BRIDGE-001/implementation.md to mark B1/B2 done and link artifact files.
- Keep helper/tests under dbex.nanobrag_bridge / tests/dbex to respect repository layout.
Pitfalls To Avoid:
- Forgetting to swap dxtbx (fast, slow) → (beam_center_f, beam_center_s) per spec.
- Omitting sample→source normalization for DetectorConfig.custom_beam_vector.
- Converting trusted mask to float without preserving shape ordering or polarity.
- Dropping square-pixel guard already enforced in Phase A (reuse shared check instead of duplicating silently).
- Hardcoding polarization defaults inconsistent with docs/nanobrag_api.md:53-57 fallback rules.
- Forgetting to keep unit cell angles in degrees when populating CrystalConfig.
- Letting helper mutate source Experiment objects (should build configs immutably).
- Running pytest without KMP_DUPLICATE_LIB_OK leading to MKL duplicate lib abort.
- Failing to persist pytest.log + notes under the artifact directory for ledger traceability.
If Blocked:
- Record the blocker in docs/fix_plan.md Attempts History (Metrics: pending, Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/block.txt) and flip status to blocked; capture repro notes in artifact dir; alert maintainer via galph_memory entry.
Findings Applied (Mandatory):
- GEOMETRY-001 — DetectorConfig guard + sample→source mapping must align with geometry spec to avoid downstream parity regressions.
- CONFORMANCE-001 — Ensure pytest exports KMP_DUPLICATE_LIB_OK=TRUE for torch-adjacent tests per conformance ledger.
