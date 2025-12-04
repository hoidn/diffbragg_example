---
initiative: ARCH-SIM-CONSTRUCTION-001
typed_as: bugfix
action_type: implementation
mode: parity
acceptance:
  selector: DB-AT-028 & DB-AT-029
  signature: 'chi²/pixel initial ≈2.1e5 (≫1e2 spec) with median ROI corr before ≈-0.054 (<0.2) because Stage A reconstruction still rebuilds via the cold simulator path and drops the warmed StageAContext/cached Bragg stack, leaving masked means 30× below telemetry'
baseline:
  commit: 3412b20e0ada53a74b3ee76f02bc3ead7210ce7a
  truth_sources:
    - docs/fix_plan.md#ARCH-SIM-CONSTRUCTION-001
    - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028/baseline_stats.json
    - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json
do_now:
  - step: Plumb StageAArtifacts through the DB-AT fixture
    locus: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result
    expected: After `engine.run(...)`, fetch `stage_a_artifacts = getattr(engine, "_artifacts", {}).get("stage_a")`, pass its `stage_a_ctx` into both `build_final_bragg_from_stage_a_telemetry` calls, and when `bragg_full` is cached reuse it for the `"final"` stack so warm runs reuse the exact Stage A output while the legacy cold reconstruction remains the fallback when artifacts are absent.
  - step: Mirror the defensive artifact lookup in the baseline probe
    locus: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main
    expected: Probe now pulls `stage_a_ctx`/`bragg_full` from `getattr(engine, "_artifacts", {})`, threads the warmed context into both helper invocations, and prefers the cached final Bragg image so telemetry vs reconstruction parity can be measured without re-running cold simulators.
  - step: Re-run the warmed baseline probe under the new report directory
    locus: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
    expected: `stage_a_baseline_probe.json` in `reports/2025-12-14T150000Z/` shows `model_mean_masked` ratios →1.0 when StageAArtifacts exist (and clearly reports when the cold-path fallback was required).
  - step: Re-run DB-AT-028/029 with artifact capture
    locus: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity + test_db_at_029_structure_parity
    expected: Updated `baseline_stats.json` + pytest log demonstrate whether the warmed cache reuse eliminates the 30× magnitude gap (or clearly logs when `_artifacts` were missing so we can escalate engine plumbing).
tests_to_run:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k 'DB_AT_028 or DB_AT_029' | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log
docs_to_update: []
report_back:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json with telemetry vs reconstruction parity metrics (note whether warm cache or fallback path fired)
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028/baseline_stats.json
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029/baseline_stats.json
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log summarizing the gate outcomes
blocked:
  status: no
  reason: ''
---
