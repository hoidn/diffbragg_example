Summary: Align Stage A's masked-intensity baseline with the observed data so DB-AT-028/029 stop railroading the global scale delta into the clamp.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: main
Mapped tests: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T210000Z/

Do Now:
- Implement: dbex/refinement/stage_a.py::_build_stage_a_params — when a warm StageAContext exists, always compute `target_mean_masked` / `model_mean_masked`, adjust `log_scale_baseline` by `np.log(target/model)` (or set it when calibration metadata is absent), refresh `config.log_scale_baseline`, and propagate the new baseline into StageAContext/telemetry so zero-iteration Stage A predictions already match the masked target.
- Validate: tests/dbex/test_stage_a_smoke_parity.py::{test_db_at_028_loss_scale_sanity,test_db_at_029_intensity_roi_corr} — rerun the Stage A parity selectors with the calibrated detector-size=small fixture and capture logs/JSON under the new report directory.

How-To Map:
1. export REPORT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T210000Z && mkdir -p "$REPORT_DIR"/scale_probe "$REPORT_DIR"/db_at_028 "$REPORT_DIR"/db_at_029
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py \
     --detector-size small \
     --device cpu \
     --output "$REPORT_DIR"/scale_probe/stage_a_scale_alignment.json \
     | tee "$REPORT_DIR"/scale_probe/probe_run.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   DBAT028_ARTIFACT_DIR="$REPORT_DIR"/db_at_028 \
   DBAT029_ARTIFACT_DIR="$REPORT_DIR"/db_at_029 \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
   | tee "$REPORT_DIR"/pytest_db_at_028_029.log

Pitfalls To Avoid:
- Do not reintroduce the removed `* sqrt_spot_scale` term inside reconstruction; only Stage A's baseline logic should change.
- Keep `config.log_scale_baseline` and `StageAContext.log_scale_baseline` in sync so Stage B/C and reconstruction consume the corrected baseline.
- Preserve the existing guarded fallback for uncalibrated runs (baseline stays `None` until a ratio > 0 is observed).
- Use the same masked tensors (`inputs.target`, `inputs.loss_mask`) that drive the loss so the ratio reflects the real optimization pixels.
- Avoid hard-coding detector size or ROI counts—respect the config flags already in RefinementConfig.
- Capture fresh artifacts even if pytest keeps failing; we need the updated telemetry JSON/logs in the reserved report dir.

If Blocked:
- If `target_mean_masked` or `model_mean_masked` still come back `None`, log the exception stack plus the computed statistics to `$REPORT_DIR/blocker.txt`, leave `log_scale_baseline` untouched, set `next_action=diagnostics` in galph_memory, and pause implementation for supervisor review.
- If DB-AT-028/029 still fail with the same chi² signature after the baseline change, keep the new pytest log + telemetry JSON, note the recorded `log_scale_effective` values in `$REPORT_DIR/db_at_028/db_at_028_metrics.json`, and flag the next loop as needing spec-change triage before touching reconstruction again.

Findings Applied:
- SCALE-009 — Reconstruction must follow Stage A's calibrated scale telemetry; this loop adjusts the Stage A baseline so the telemetry itself encodes the correct masked intensity before reconstruction consumes it.

Pointers:
- docs/spec-db-core.md §Objective Function & Variance Model — canonical definition of masked loss and calibration ladder.
- docs/config_crosswalk.md §Calibration & Unit Conventions — source-of-truth for `spot_scale_override`, sigma precedence, and scaling order.
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md §Phase C.8 — detailed checklist for the baseline alignment fix.

Next Up:
- If the small-detector selectors pass quickly, rerun the full-detector variant (`DBEX_SMOKE_DETECTOR_SIZE=full`) to confirm the baseline change behaves on the canonical dataset before resuming ARCH-REFACTOR-001 Phase D.3.
