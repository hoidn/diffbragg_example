Summary: Nudge Stage A's log_scale baseline to match masked target intensity so DB-AT-028/029 stop clamping at +3 and reconstruction inherits the correct scale.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: main
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028, tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/

Do Now:
- Implement: dbex/refinement/stage_a.py::StageA.run — whenever the warm cache exists, tensorize `inputs.target`/`inputs.loss_mask`, run the zero-iteration simulators, compute masked target/model means on the correct device, and add `log(target/model)` to `log_scale_baseline` (or set it outright when calibration metadata is absent). Update `StageAContext.log_scale_baseline`, `config.log_scale_baseline`, `param_values['log_scale_baseline_source']`, and telemetry so reconstruction and later stages read the corrected baseline.
- Update: dbex/refinement/stage_a.py::StageA.run — ensure the adjusted baseline propagates through `_build_stage_a_context`, `stage_a_ctx`, and the returned telemetry so cold-path reconstruction rebuilds `bragg_before/bragg_after` with the aligned scale (no Stage B/C changes this loop).
- Validate: capture a fresh scale-alignment probe plus DB-AT-028/029 runs with artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/`; the probe should show `log_scale_delta_clamped≈0` and the tests must hit `chi²/pixel ≤ 1e2` and median ROI corr ≥ 0.2.

How-To Map:
1. `mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/{scale_probe,db_at_028,db_at_029}`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py \
     --detector-size small \
     --calibration-config sp.proc/calibration/config_torch_smoke_small.json \
     --device cpu \
     --out-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/scale_probe`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
   | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T010000Z/pytest_db_at_028_029.log`

Pitfalls To Avoid:
- Do not touch Stage B/C or reconstruction scaling this loop; the fix lives entirely inside Stage A baseline math.
- Keep all tensor math device/dtype neutral (use Stage A’s `device`/`dtype` and fall back to NumPy if tensorization fails).
- Only add the masked-intensity adjustment when both means are positive; guard against zero, NaN, or inf inputs.
- Preserve existing telemetry keys and `StageAContext` fields so downstream consumers and scripts keep working.
- Do not relax `log_scale_max_delta` or other clamps; fixing the baseline is the goal, not widening bounds.
- Leave environment/toolchain untouched per Environment Freeze; if a dependency is missing, stop and log the block.
- Ensure artifact dirs exist before running scripts/tests so logs land in the expected report tree.
- Keep ROI/panel sampling logic unchanged; the adjustment should work for both ROI and panel modes.

If Blocked:
- If masked means cannot be computed (e.g., warm cache disabled or tensor conversion fails), log the exact exception, capture the partial telemetry in the probe JSON, and update `docs/fix_plan.md` + Attempts History with the evidence before re-queuing the work.
- If DB-AT-028/029 still clamp `log_scale_delta` after the baseline change, keep the failing telemetry JSON + pytest log under the new report dir and ping Galph so we can decide whether to escalate (spec-change vs wider baseline instrumentation).

Findings Applied:
- docs/findings.md:41 (SCALE-008) — Stage A must honor a mapping-provided or measured baseline so we avoid double-applying `spot_scale_override`.
- docs/findings.md:42 (SCALE-009) — Reconstruction already trusts Stage A telemetry; keep that path untouched and focus on delivering a correct baseline upstream.

Pointers:
- docs/fix_plan.md:133 — Initiative overview and Attempts History for ARCH-SIM-CONSTRUCTION-001.
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:313 — Phase C.7 summary and the Phase C.8 checklist you are executing now.
- docs/spec-db-workflow.md:100 — Stage A pipeline contract (nearest-neighbor simulator + variance-weighted loss expectations).

Next Up (optional):
1. If DB-AT-028/029 pass with the new baseline, revisit `log_scale_max_delta` vs telemetry to decide whether we can tighten or document the clamp behavior before re-enabling Stage B/C validations.
