Summary: Add mask coverage diagnostics/fallback in the reconstruction helper and exercise them via the simulator comparison probe so DB-AT-028/029 evidence stops regressing when trusted masks are enabled.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/{summary.md,mask_coverage.json,simulator_intensity_metrics_masked.json,simulator_intensity_metrics_unmasked.json,pytest_db_at_028_029.log}
Do Now:
  1. Implement: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry`
     - Compute `panel_trusted_mask.mean()` (float) for every panel when a mask is provided and append the per-panel coverage plus panel id to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/mask_coverage.json` (create the file if needed).
     - If any panel coverage falls below 0.50, log the panel id and coverage, skip injecting the mask for that panel (fall back to `None`), and keep the old behaviour for other panels so we do not zero the entire detector. Guard with a tiny epsilon to avoid float noise and keep the DEBUG print block intact.
  2. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py`
     - Add a `--use-reconstruction-helper` flag that rebuilds `RefinementInputs` + `RefinementConfig` and calls `build_final_bragg_from_stage_a_telemetry` so the probe exercises the same mask logic as DB-AT-028/029.
     - Add a `--disable-trusted-mask` flag that temporarily sets `inputs.trusted_mask = None` before calling the helper so we can capture “masked vs unmasked” outputs in one script.
     - When the reconstruction helper is used, emit two JSON files in the artifacts directory (`simulator_intensity_metrics_masked.json`, `..._unmasked.json`) that include raw/scale means, mask coverage statistics emitted by the helper, and the CLI arguments.
  3. Evidence collection:
     - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --use-reconstruction-helper --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/simulator_intensity_metrics_masked.json`
     - Repeat with `--use-reconstruction-helper --disable-trusted-mask --output .../simulator_intensity_metrics_unmasked.json` so we can quantify the guard effect.
  4. Validation:
     - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/pytest_db_at_028_029.log`
How-To Map:
  - Always `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` before running helper scripts/tests so env guards match the repo standard.
  - Use `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --help` after editing to confirm the new flags are wired, then run the masked + unmasked commands above. Keep `NANOBRAGG_DISABLE_COMPILE=1` to stay deterministic.
  - Ensure `mask_coverage.json` is valid JSON (list of dicts or dict keyed by panel id). When appending stats, include timestamp, panel id, coverage fraction, and whether the guard skipped mask injection.
  - After pytest finishes, grep the DEBUG block in the log to confirm the guard logged coverage data for both masked and fallback panels.
Pitfalls To Avoid:
  - Do not mutate warm-cache paths – only wrap the cold-path detector construction, otherwise Stage A regressions will occur.
  - Percent coverage thresholds must remain ≥0.50 per spec; do not “clip” coverage by forcing 1.0.
  - Keep the existing DEBUG prints and scaling math unchanged so prior evidence remains comparable.
  - Guard code must be device/dtype agnostic (no implicit CPU tensors) and avoid writing to stdout outside the existing DEBUG block.
  - When running pytest, honor the DBAT artifact directory env vars so the selector collects instead of skipping.
If Blocked:
  - If `inputs.trusted_mask` is `None`, record the situation (repr of `inputs`) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/blocked.md`, update `docs/fix_plan.md` + `galph_memory.md`, and stop before modifying code further.
  - If both masked and unmasked probe runs yield identical metrics (coverage guard never triggers), capture the JSON + log evidence and be ready to shift the hypothesis (likely calibration instead of masking).
Findings Applied (Mandatory):
  - REFINE-016 — Stage C and reconstruction helpers must apply the same trusted-mask gate as Stage A so chi² comparisons remain meaningful.
Pointers:
  - docs/spec-db-core.md §Data Contracts — trusted mask polarity and `(background >= 0) ∧ trusted_mask` loss mask definition.
  - docs/fix_plan.md §ARCH-SIM-CONSTRUCTION-001 Attempts History (lines ~133-168) — context for the mask regression and new evidence plan.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md — Phase C.6 checklist describing the trusted-mask parity objective and validation requirements.
Next Up:
  1. If mask coverage diagnostics show healthy coverage, attempt the real parity fix (thread mask tensors through reconstruction and rerun DB-AT-028/029).
  2. If the guard fires on every panel, inspect `prepare_refinement_inputs` and DataLoad to see why the trusted mask is sparse before re-attempting the fix.
