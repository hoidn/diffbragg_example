Summary: Capture Stage A vs DB-AT mask provenance so we can explain why masked means still differ even after the StageAArtifacts warm path landed.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/

Do Now:
- Implement: `dbex/refinement/stage_a.py::_build_stage_a_params` — when Stage A computes `target_mean_masked` / `model_mean_masked`, also capture mask provenance (`loss_mask_pixel_count`, per-panel counts, and a sha1 checksum of the boolean mask). Persist this metadata on the Stage A telemetry (e.g., via `param_values["mask_metadata"]` so it lands on `telemetry.mask_metadata`), since we need it in reconstruction/baseline stats.
- Implement: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` — extend the existing `baseline_stats` payload so each record includes both the telemetry mask metadata and the reconstruction mask metadata (`inputs.loss_mask` count + checksum). Add a short warning when the telemetry checksum differs from the reconstruction checksum so the DB-AT artifacts show mask parity explicitly.
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` — load the new telemetry metadata, emit it in the JSON summary, and print a comparison table (telemetry vs reconstruction vs DB-AT mask) so we can see if the probe uses the same mask definition as the selector.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/stage_a_baseline_probe.json`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/pytest_db_at_028_029.log`

How-To Map:
1. Stage A telemetry: import `hashlib` near the top of `stage_a.py` if needed, compute `mask_checksum = hashlib.sha1(np.ascontiguousarray(inputs.loss_mask, dtype=np.uint8)).hexdigest()`, and store it along with `loss_mask_true_pixels` and `panel_true_pixels=[int(np.count_nonzero(inputs.loss_mask[pid])) ...]`. Attach this dict to both `param_values` and the returned telemetry so downstream code can read `telemetry.mask_metadata`.
2. Reconstruction instrumentation: when writing each `baseline_stats` entry, include a `mask_metadata` block with both the telemetry metadata and a reconstruction view (`loss_mask_true_pixels`, checksum derived from `inputs.loss_mask`, and the mask coverage data you already collect). Log a warning (and include a boolean flag in the JSON) when the checksums differ so DB-AT artifacts will spell out any mismatched masks.
3. Baseline probe: load `telemetry.mask_metadata` and the reconstruction metadata, dump both into the JSON file, and add a console table that clearly lists telemetry vs reconstruction pixel counts and checksums. Emit an explicit PASS/FAIL line when the checksums agree.
4. Run the baseline probe command so the new metadata lands under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/`.
5. Re-run the DB-AT selectors with the new `DBAT028/9_ARTIFACT_DIR` root so the refreshed `baseline_stats.json` and pytest log reflect the instrumentation. This will tell us whether the Stage A masked mean mismatch is caused by different masks (checksum mismatch) or a true scaling bug.

Pitfalls To Avoid:
- Keep checksum computations device/dtype agnostic (always operate on CPU numpy/torch copies) so CUDA runs don’t segfault.
- Do not rename or remove existing baseline stats fields; the new metadata should be additive so old analysis scripts still parse the JSON.
- Make sure the env vars in the validation commands point at the new `2025-12-14T200000Z` artifact directory; the previous loop reused the older timestamp and overwrote evidence.
- Avoid touching `_stage_contexts`; the StageAArtifacts warm path you just landed remains authoritative.
- Respect Environment Freeze—no package installs or edits outside the repo tree.

If Blocked:
- If telemetry lacks `mask_metadata` after your changes, dump the `telemetry.__dict__` in the baseline probe log and stop; capture the traceback in the new report directory and ping Galph instead of guessing.
- If the checksum computation explodes on GPU tensors, fall back to `np.asarray(inputs.loss_mask, dtype=np.uint8)` and note the fallback in the report; do not delete the instrumentation.

Findings Applied:
- SCALE-009 — Reconstruction helpers must stay aligned with Stage A scaling/mask conventions; mask provenance is required to enforce that contract.
- SCALE-008 — Stage A’s masked intensity baseline (and its telemetry) drives reconstruction scaling, so any mask mismatch must be documented before we tweak physics.

Pointers:
- dbex/refinement/stage_a.py
- dbex/refinement/reconstruction.py
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py
- docs/fix_plan.md §ARCH-SIM-CONSTRUCTION-001
