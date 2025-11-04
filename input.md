**Summary**: Realign nanobrag detector geometry so torch peaks land on DiffBragg pixels for DB_AT_001 parity.
**Mode**: none
**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
**Branch**: integration
**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/

**Do Now (hard validity contract)**  
- Implement: dbex/nanobrag_bridge.py::create_detector_config — emit DIALS-convention XYZ rotation angles (no CUSTOM vectors) so DetectorConfig stays in BEAM pivot and preserves the refGeom beam center.  
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke  
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/

**Priorities & Rationale**
- Geometry parity (docs/config_crosswalk.md:22-37) demands canonical tensors share `[panel, slow, fast]` alignment; eliminating the 6 px offset is prerequisite for Exit Criteria 1.  
- docs/nanobrag_api.md:32-45 documents pivot behavior; staying in BEAM mode ensures beam-center provenance required by specs/spec-db-conformance.md:23-26.  
- specs/forward_equivalence.md:21-37 requires tight ROI metrics before manifest/test enforcement; geometry drift currently blocks these thresholds.

**How-To Map**
- `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`
- `PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/torch_hkl_debug.json --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic --roi-dump plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/roi_triptychs`
- `python - <<'PY'\nimport json\nimport numpy as np\nfrom pathlib import Path\nreport = Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z')\ntriptych_index = report/'roi_triptychs/index.json'\nif triptych_index.exists():\n    data = json.loads(triptych_index.read_text())\n    offsets = [abs(sample['dy']) + abs(sample['dx']) for sample in data.get('samples', [])]\n    stats = {\n        'n_samples': len(offsets),\n        'median_abs_offset': float(np.median(np.abs(offsets))) if offsets else 0.0,\n        'max_abs_offset': float(np.max(np.abs(offsets))) if offsets else 0.0,\n    }\nelse:\n    base = Path('tests/fixtures/golden_data/simple_cubic')\n    diff = np.load(base/'bragg_diffbragg.npy')[0]\n    torch = np.load(base/'bragg_torch.npy')[0]\n    idx_diff = np.array(np.unravel_index(diff.argmax(), diff.shape))\n    idx_torch = np.array(np.unravel_index(torch.argmax(), torch.shape))\n    shift = (idx_torch - idx_diff).tolist()\n    stats = {\n        'n_samples': 1,\n        'median_abs_offset': float(np.linalg.norm(shift, ord=1)),\n        'max_abs_offset': float(np.linalg.norm(shift, ord=1)),\n        'offset_vector': shift,\n    }\n(report/'roi_offsets.json').write_text(json.dumps(stats, indent=2))\nPY`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/pytest_db_at_001.log`

**Pitfalls To Avoid**
- Do not reintroduce `DetectorConvention.CUSTOM`; it forces SAMPLE pivot and recreates the 6 px drift.  
- Keep beam-center mm values swapped (slow→s, fast→f) per docs/nanobrag_api.md:28 to avoid axis inversion.  
- Preserve SCALE-002 post-simulation scaling; do not tweak intensity normalization.  
- Ensure ROI `.npz` payloads are written inside this checkout before updating manifests (MANIFEST-001).  
- Respect Environment Freeze: no package installs or edits outside repo; treat missing imports as blockers.  
- Retain trusted mask polarity (True=include) when regenerating metrics.  
- Do not drop existing findings or change xfail reason in parity test.

**If Blocked**
- If `nanobrag_torch` import fails, capture the stack trace tail, note blocker in docs/fix_plan.md Attempts History, and halt without edits.  
- If canonical generator exits non-zero, preserve `canonical_capture.log`, record failure signature in `plans/.../reports/2025-11-04T011500Z/` and flag focus as blocked in galph_memory.md.  
- Should pytest selector collect 0 tests, downgrade mapped selector status in docs/TESTING_GUIDE.md and record the gap before exiting.

**Findings Applied (Mandatory)**
- MANIFEST-001 — verify regenerated tensors reside in this workspace before manifest emission.  
- SCALE-002 — retain √scale post-simulation factor when comparing torch vs DiffBragg outputs.  
- HKL-ORIENT-001 — keep beam vector sample→source (`-s0/||s0||`) to avoid HKL miss rate regressions.

**Pointers**
- docs/config_crosswalk.md:22  
- docs/nanobrag_api.md:32  
- docs/TESTING_GUIDE.md:86  
- docs/forward_equivalence.md:21

**Next Up (optional)**
- Tighten DB_AT_001 parity thresholds after geometry alignment if localization ≥90% is achieved.
