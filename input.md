Summary: Expose refined-structure-factor telemetry in the nanobrag CLI and guard it with tests.
Mode: none
Focus: MAP-SCALE-003 — CLI refined structure factor telemetry
Branch: integration
Mapped tests:
- pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 -q
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
Artifacts: plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/
Do Now:
- MAP-SCALE-003: Implement: dbex/refine_one.py::run_nanobrag_backend + dbex/refine_one.py::_write_torch_outputs — thread refined MTZ telemetry into torch diagnostics and keep raw fallback backwards-compatible. Validate: pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 -q; pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke (env: KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1, DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z).
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1 -q | tee plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/pytest_cli_refined_mtz.log
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/cli_refined_telemetry.h5 -m 747_mask.pkl -z scaled.mtz --torch-config tests/fixtures/golden_data/simple_cubic/config_torch.json --refined-mtz tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz
4. python - <<'PY' > plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/telemetry_probe.txt
from pathlib import Path
import h5py
h5_path = Path("plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/cli_refined_telemetry.h5")
with h5py.File(h5_path, "r") as h:
    diag = h["torch_diagnostics"].attrs
    print({key: diag[key] for key in sorted(diag.keys())})
PY
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke | tee plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/collect_db_at_024.log
6. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/pytest_db_at_024.log
Pitfalls To Avoid:
- Keep `_write_torch_outputs` backward-compatible (only append attributes); avoid changing dataset layouts.
- Do not import new third-party packages or modify environment (Environment Freeze).
- Ensure telemetry values are JSON/HDF5-friendly (native Python scalars / strings).
- Mock refined MTZ loading in tests to avoid filesystem coupling; keep CLI test hermetic.
- Maintain CPU execution (`torch.device('cpu')`) so tests remain deterministic.
- Preserve existing log messages and thresholds to avoid DB_AT_024 regressions.
- Capture logs under the new report directory; no stray files elsewhere.
If Blocked: Log the issue in plans/active/MAP-SCALE-003/reports/<timestamp>/blocked.md, update docs/fix_plan.md Attempts History with the blocker summary, and note the block + return conditions in galph_memory.md before switching focus.
Findings Applied:
- SCALE-003 — Enforce refined |F| usage by surfacing telemetry and tests guard fallback.
- SCALE-004 — Ensure telemetry reflects refined geometry/MTZ pairing to prevent mismatched assets.
- SCALE-006 — Maintain CLI calibration plumbing while extending diagnostics.
- TESTING-002 — Use CLI mocks/fixtures to isolate backend behavior.
- TESTING-003 — Capture collect-only output before marking selectors Active.
Pointers:
- dbex/refine_one.py:201 — refined MTZ loading branch
- dbex/refine_one.py:340 — `_write_torch_outputs` diagnostics emission
- tests/dbex/test_refine_one_cli.py:200 — CLI regression scaffolding
- docs/findings.md:17 — SCALE-003 guardrail
- docs/findings.md:29 — SCALE-004 refined geometry requirement
- docs/TESTING_GUIDE.md:71 — DB_AT_024 selector details
Next Up (optional):
1) Extend telemetry to capture refined geometry provenance (expt/refl paths) if gaps remain.
2) Add negative-path test covering missing/invalid `--refined-mtz` warnings.
Doc Sync Plan:
- After telemetry test passes, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md to mention the new CLI telemetry attributes and refreshed artifact path (plans/active/MAP-SCALE-003/reports/2025-11-05T150000Z/). Include references to the pytest and collect-only logs captured this loop.
