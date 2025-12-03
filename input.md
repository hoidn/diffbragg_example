Summary: Instrument the Stage A reconstruction path so we can quantify the masked-intensity gap versus telemetry before changing any physics or DB-AT gates.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/

Do Now:
- Implement: dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry — after building `bragg_full`, compute masked/unmasked means using `inputs.loss_mask`/`inputs.target`, compare them against `telemetry.target_mean_masked` and `telemetry.model_mean_masked` (dict fallback when telemetry is serialized), log the ratios, and append a JSON record (e.g. `baseline_stats.json`) under the artifact directory selected by `DBAT028_ARTIFACT_DIR` or `DBAT029_ARTIFACT_DIR` (fallback to the report path) similar to the existing mask-coverage log.
- Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main — read `telemetry.target_mean_masked`, `telemetry.model_mean_masked`, `telemetry.scale_factor`, and masked chi² directly from the `RefinementTelemetry` object instead of the `log_scale_effective` dict, and emit the updated values (plus the reconstructed masked means/chi²) in both the JSON payload and the stdout table so we can diff telemetry vs reconstruction without digging through DB-AT logs.
- Validate: tests/dbex/test_stage_a_smoke_parity.py::{test_db_at_028_loss_scale_sanity,test_db_at_029_structure_parity} — run the targeted selector with `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` pointing at this loop’s report directory so the new `baseline_stats.json`, probe output, and pytest logs land under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/`.

How-To Map:
1. Rebuild the Stage A baseline probe: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --device cpu --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/stage_a_baseline_probe.json` — this should now report the telemetry masked means instead of NaN and note the reconstructed-vs-telemetry ratios.
2. Run the DB-AT selector with artifact envs so pytest, mask coverage, and the new baseline stats drop into the report dir:
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/pytest_db_at_028_029.log`.
3. After the run, confirm `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T235500Z/baseline_stats.json` contains at least one record with telemetry vs reconstruction masked means (ratio ~2.7× today) so we have quantitative evidence for the next decision.

Pitfalls To Avoid:
- Do not touch physics or acceptance thresholds yet; we only want instrumentation plus evidence.
- Keep the Environment Freeze intact (no package installs or upstream edits); the probe + reconstruction changes live in-repo under approved paths.
- Leave Stage A loss math untouched—only add logging/JSON emission; no speculative scale tweaks.
- Maintain device/dtype neutrality (the new stats must work on CPU and CUDA) and respect `inputs.loss_mask` polarity (True = trusted per spec-db-core).
- Artifact writers must be tolerant when env vars are absent; never crash if `DBAT028_ARTIFACT_DIR` isn’t set.
- Continue honoring SCALE-009: make sure any new diagnostics happen after the existing `scale_factor` math so we don’t accidentally double-apply `sqrt(spot_scale_override)`.
- Keep the probe on the canonical refGeom smoke assets defined in docs/data_dependency_manifest.md; don’t hard-code alternate datasets.
- Avoid spamming stdout with unbounded logs—stick to concise debug prints plus the JSON append.
- Remember that `telemetry_a` may be a dict (archived artifacts); guard lookups accordingly.
- If pytest fails for reasons unrelated to the instrumentation, capture the failure signature and halt per repeat-failure guard instead of editing more code.

If Blocked:
- If `build_final_bragg_from_stage_a_telemetry` cannot see `inputs.loss_mask`/`inputs.target`, log the missing data in the summary, capture whatever partial stats you can, and stop—don’t guess at new masks.
- If pytest still fails before writing the new JSON (e.g., the selector crashes earlier), file the partial artifacts, note the failure signature plus any console logs, and wait for supervisor direction; do not tweak Stage A scale math without a plan change.

Findings Applied:
- SCALE-009 (docs/findings.md:42) — Reconstruction helpers must honor Stage A’s sqrt(spot_scale) convention; the diagnostics we’re adding explicitly verify that post-run.
- SCALE-008 (docs/findings.md:41) — Stage A baseline adjustments depend on masked-intensity telemetry; ensuring the probe and reconstruction read those fields keeps us compliant with the masked-baseline policy.

Pointers:
- docs/fix_plan.md:133 — ARCH-SIM-CONSTRUCTION-001 entry with latest status/history.
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:326 — Phase C.9 checklist detailing this telemetry instrumentation follow-up.
- dbex/refinement/reconstruction.py:1-420 — `build_final_bragg_from_stage_a_telemetry` implementation that needs the masked-mean JSON emission.
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1-360 — Probe script to update for correct telemetry readings.
- tests/dbex/test_stage_a_smoke_parity.py:140-360 — Stage A smoke fixture that will consume the new diagnostics.

Next Up (optional):
- If the new baseline stats confirm the 2.7× mismatch is entirely in telem vs reconstruction, open a spec/harness initiative (or Phase C.10) to decide whether DB-AT gates need revision or the reconstruction helper needs a scale fix.
