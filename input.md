Summary: Align the Stage A baseline probe with the DB-AT-028/029 smoke fixture so the telemetry evidence uses the same HKL/calibration inputs before we gather more parity data.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/

Do Now:
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::get_refgeom_dataload` so it resolves calibration + HKL paths exactly like `tests/conftest.py` (honour `DBEX_SMOKE_CALIB_PATH` / `DBEX_SMOKE_HKL_PATH`, default to the detector-size-specific refined MTZ when calibration metadata exists, fall back to `scaled.mtz` and the `I(+),SIGI(+),I(-),SIGI(-)` columns only when no calibration payload is present). Thread the resolved `mtz_file`/`mtz_col` into the `DataLoad` Namespace instead of the current hard-coded `scaled.mtz`.
- Implement: In the baseline probe output (`probe_metadata` block), persist the resolved `mtz_file`, `mtz_col`, and `calibration_config_path`, and print a short console line summarizing the chosen HKL/cali paths so future parity reviews can confirm the probe matched the DB-AT fixture inputs.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/stage_a_baseline_probe.json`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/pytest_db_at_028_029.log`

How-To Map:
1. Mirror the detector-size aware HKL logic from `tests/conftest.py`: if `DBEX_SMOKE_HKL_PATH` is set, use it (choose `F(+),SIGF(+),F(-),SIGF(-)` when “refined” appears, otherwise use the raw `I(+),SIGI(+),I(-),SIGI(-)` columns); else when a calibration config exists pick `sp.proc/calibration/smoke_refined_structure_factors_small.mtz` for the small detector (or the full-detector variant), falling back to `scaled.mtz` only when neither calibration nor refined MTZ is present.
2. Keep the existing calibration-path resolution, but feed the resolved `mtz_file`/`mtz_col` into the `Namespace` you pass to `DataLoad`. Add small helper prints so we can see the chosen files in CI logs, and include the same values in `probe_metadata` for the JSON artifact.
3. After editing the script, rerun the probe command with the usual smoke env vars so `stage_a_baseline_probe.json` under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/` captures the aligned telemetry + metadata.
4. Rerun the DB-AT-028/029 selector with the new artifact directories so `db_at_028/db_at_028_metrics.json`, `baseline_stats.json`, and the pytest log all reference the updated report path.

Pitfalls To Avoid:
- Do not regress the existing mask/telemetry instrumentation—new metadata must be additive.
- Keep env overrides authoritative (if `DBEX_SMOKE_*` paths are provided, do not silently override them with defaults).
- Remember the refined MTZ uses `F(+),SIGF(+),F(-),SIGF(-)` while the raw scaled MTZ needs the `I(+),SIGI(+),I(-),SIGI(-)` columns; double-check column names before calling `open_mtz`.
- Preserve cross-device safety: all logging/conversions should stay on CPU/NumPy so CUDA jobs do not OOM.
- Re-use the existing report timestamp (`2025-12-15T010000Z`) for both the probe and pytest artifacts to keep the evidence bundle coherent.

If Blocked:
- If the refined MTZ is missing, log the fallback in the probe summary (`mtz_file`, `mtz_col`) and capture the failure in the report directory rather than guessing; ping Galph with the log excerpt.
- If DataLoad raises because the MTZ column string is wrong, stop immediately, capture the traceback under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/`, and notify me—do not silently revert to the old hard-coded path.

Findings Applied:
- SCALE-009 — Reconstruction helpers and diagnostics must stay aligned with Stage A scaling inputs; mismatched HKL data invalidates the telemetry evidence.
- SCALE-008 — Stage A’s masked intensity baseline drives reconstruction scale, so parity probes must consume the same calibration/HKL payloads as the acceptance fixtures.

Pointers:
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
- tests/conftest.py:60-210 (smoke calibration/HKL resolution logic)
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md (§C.9 checklist)
- docs/fix_plan.md §ARCH-SIM-CONSTRUCTION-001 (2025-12-14 entries)
