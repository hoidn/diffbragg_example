---
initiative: ARCH-SIM-CONSTRUCTION-001
typed_as: bugfix
action_type: implementation
mode: parity
acceptance:
  selector: DB-AT-028 & DB-AT-029
  signature: 'chi²/pixel initial ≈2.1e5 (≫1e2 spec) with median ROI corr before ≈-0.054 (<0.2) because the Stage A smoke fixture and baseline probe still rebuild via the cold simulator path whenever StageAArtifacts is missing, so the warmed StageAContext/cached bragg_full never reach reconstruction and masked means stay 9–30× below Stage A telemetry.'
baseline:
  commit: 995da1b9e4381ca561ad4e07564089c3305308a7
  truth_sources:
    - docs/fix_plan.md#ARCH-SIM-CONSTRUCTION-001
    - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json
    - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028/baseline_stats.json
do_now:
  - step: Wire StageAArtifacts through the DB-AT Stage A fixture with fallbacks
    locus: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result
    expected: After `engine.run(...)`, defensively fetch `stage_a_artifacts = getattr(engine, "_artifacts", {}).get("stage_a")`, reuse its `stage_a_ctx` for both `build_final_bragg_from_stage_a_telemetry` calls, and feed the cached `bragg_full` into `bragg_after` when it exists while falling back to the cold helper path when artifacts are absent so DB-AT-028/029 always see the warmed Stage A baseline without crashing.
  - step: Mirror artifact reuse in the Stage A baseline probe
    locus: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main
    expected: The probe now performs the same guarded lookup (`getattr(..., "_artifacts", {})`), threads `stage_a_ctx` into the helper for both `param_state="initial"` and `"final"`, reuses the cached `bragg_full` when available, and clearly logs when it had to fall back, so telemetry vs reconstruction comparisons finally observe warm-cache parity.
  - step: Re-run the warmed baseline probe under the 2025-12-14T150000Z report root
    locus: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
    expected: With StageAArtifacts wired in, `stage_a_baseline_probe.json` shows `model_mean_masked` ratios ≈1.0 and documents whether the warm cache or cold fallback fired, proving the reconstruction path now matches Stage A telemetry prior to re-checking the gates.
  - step: Re-run DB-AT-028/029 with artifact capture after the fix
    locus: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity + test_db_at_029_structure_parity
    expected: The refreshed `baseline_stats.json` and pytest log produced under `reports/2025-12-14T150000Z/` show whether reusing StageAArtifacts eliminates the 30× magnitude gap (or explicitly records that `_artifacts["stage_a"]` was missing so we can escalate the engine plumbing next loop).
tests_to_run:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k 'DB_AT_028 or DB_AT_029' | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log
docs_to_update: []
report_back:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json with warm-cache vs cold-path indicators and masked-mean ratios
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028/baseline_stats.json
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029/baseline_stats.json
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log summarizing selector outcomes
blocked:
  status: no
  reason: ''
---
