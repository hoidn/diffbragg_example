---
initiative: ARCH-SIM-CONSTRUCTION-001
typed_as: bugfix
action_type: implementation
mode: parity
acceptance:
  selector: DB-AT-028 & DB-AT-029
  signature: 'chi²/pixel initial ≈2.1e5 (>1e2) with median ROI corr before ≈-0.054 (<0.2) because reconstruction rebuilds Stage A Bragg stacks via cold simulators that are 9–30× smaller than telemetry'
baseline:
  commit: afdadc7f770b478bae61d7073f906aecd1dc3e8d
  truth_sources:
    - docs/fix_plan.md#ARCH-SIM-CONSTRUCTION-001
    - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/baseline_stats.json
    - tests/dbex/test_stage_a_smoke_parity.py
do_now:
  - step: Thread StageAArtifacts through the DB-AT fixture
    locus: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result
    expected: Warm cache `stage_a_ctx` and cached `bragg_full` flow into both `build_final_bragg_from_stage_a_telemetry` calls so reconstruction reuses the Stage A simulator instead of falling back to the cold factory path.
  - step: Mirror the artifact lookup in the baseline probe
    locus: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main
    expected: The probe now replays Stage A telemetry with the warmed context/cached stack, proving simulator parity before running the DB-AT selectors.
  - step: Re-run the baseline probe with the warmed wiring
    locus: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
    expected: New `stage_a_baseline_probe.json` under `reports/2025-12-14T150000Z/` shows reconstructed masked means matching telemetry (ratio → 1.0) once warm caches are consumed.
  - step: Re-run DB-AT-028/029 with artifact capture
    locus: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity + test_db_at_029_structure_parity
    expected: Updated `baseline_stats.json`/pytest log confirm whether chi²/pixel and ROI correlation improve after warm cache wiring.
tests_to_run:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k 'DB_AT_028 or DB_AT_029' | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log
docs_to_update: []
report_back:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json with telemetry vs reconstruction parity metrics
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028/baseline_stats.json and db_at_029/baseline_stats.json plus pytest_db_at_028_029.log summarizing the chi²/ROI outcomes
blocked:
  status: no
  reason: ''
---
