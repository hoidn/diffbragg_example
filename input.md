Summary: Persist the smoke refined MTZ asset and rerun the mapping probe plus DB-AT-028/029 under the refined HKL path so Stage A telemetry finally references the same HKL/calibration bundle.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T110430Z/
Do Now:
- Implement: .gitignore::<root> — add explicit `!sp.proc/calibration/config_torch_smoke.json` and `!sp.proc/calibration/smoke_refined_structure_factors.mtz` negations so the calibration bundle (config + refined MTZ) is tracked without `git add -f` hacks.
- Generate refined HKL asset by re-running `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py` with `--refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors.mtz`, emit the manifest to the new artifacts dir, and copy/log the SHA256 in that manifest.
- Validate: rerun `plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --mtz-path sp.proc/calibration/smoke_refined_structure_factors.mtz` plus `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` under the refined HKL environment, archiving mapping + DB-AT artifacts under the timestamped reports directory.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T110430Z`.
2. Update `.gitignore` at repo root so it explicitly un-ignores `sp.proc/calibration/config_torch_smoke.json` and `sp.proc/calibration/smoke_refined_structure_factors.mtz`; verify `git status` shows no other unintended changes.
3. `mkdir -p "$REPORT"` and its subdirs (`mapping_cpu_gpu_refined`, `db_at_028`, `db_at_029`).
4. `python plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors.mtz --manifest "$REPORT"/smoke_calibration_manifest.json` (env inherits AUTHORITATIVE_CMDS_DOC). This regenerates both config and MTZ; the manifest in $REPORT should include SHA256 entries for each.
5. `git add sp.proc/calibration/config_torch_smoke.json sp.proc/calibration/smoke_refined_structure_factors.mtz` (now permitted because of the .gitignore change) so the new MTZ is persisted in history.
6. Export the Stage A canonical env: `export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors.mtz DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBAT028_ARTIFACT_DIR=$REPORT/db_at_028 DBAT029_ARTIFACT_DIR=$REPORT/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
7. `python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --sigma 3.0 --mtz-path sp.proc/calibration/smoke_refined_structure_factors.mtz --out-dir "$REPORT"/mapping_cpu_gpu_refined` (same env as step 6) to capture the refined HKL mapping metrics.
8. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log` to rerun both selectors with refined HKL; keep the `pytest ... --collect-only` log only if collection fails unexpectedly.
9. Summarize results + metrics deltas in `$REPORT/summary.md` and update docs/fix_plan.md Attempts History if DB-AT selectors still fail (include failure signatures).
Pitfalls To Avoid:
- Do not skip the .gitignore change—otherwise `smoke_refined_structure_factors.mtz` will be silently dropped on future clones.
- Ensure the capture script overwrites both config + MTZ in the repo so HKL/calibration stay in lockstep (per SCALE-004).
- Keep `DBEX_SMOKE_HKL_PATH` pointing at the refined MTZ when running the probe/tests; defaulting to scaled.mtz will reintroduce the known ROI CC≈-0.04 signature.
- Mapping probe uses metadata sigma; verify `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl` exists before starting.
- Remember that manifest + pytest artifacts live under `$REPORT`; only the calibration assets belong in git.
- Avoid parallel pytest invocations—DB-AT-028/029 share env overrides and artifact dirs.
If Blocked:
- If `capture_smoke_calibration.py` fails (e.g., missing CUDA/Hopper dependency), capture the full traceback to `$REPORT/capture_smoke_calibration_err.log`, revert touched files, mark `[TOOLING-VIS-001]` blocked in docs/fix_plan.md with the error signature, and ping Galph.
- If the refined MTZ cannot be written because `_temp.mtz` was not generated, log the console output + manifest stub under `$REPORT/` and stop; do **not** hand-edit MTZ headers.
- If either DB-AT selector crashes instead of failing its assertions, keep the raw log + metrics JSONs, then halt after updating docs/fix_plan.md Attempts History with the stack trace.
Findings Applied (Mandatory):
- STAGEA-001 — Preserve Stage A/mapping calibration provenance by sharing the same config_torch + HKL assets.
- SCALE-004 — Always pair refined structure factors with calibration metadata to avoid ROI anti-correlation.
- GEOMETRY-003 — Use the canonical refGeom zero point; do not swap experiments when sourcing sigma tiles.
- CONFORMANCE-001 — Archive DB-AT artifacts even on failure (ROIs, metrics, pytest logs all under $REPORT).
- POLICY-001 — Environment is frozen; rely solely on repo-provided DiffBragg/nanobrag tooling.
Pointers:
- docs/fix_plan.md:211-345 (TOOLING-VIS-001 Attempts History + current blocker description).
- docs/data_dependency_manifest.md:80-125 (calibration + refined MTZ asset contract and smoke fixture defaults).
- docs/spec-db-workflow.md:20-62 (Stage A smoke + mapping zero-point requirements).
- docs/spec-db-core.md:84-90 (variance-weighted chi² + ROI correlation gates used by DB-AT-028/029).
- plans/active/TOOLING-VIS-001/implementation.md:200-310 (Phase D objectives + diagnostics context).
Next Up (optional):
- If ROI CC recovers with refined HKL, rerun `plans/active/TOOLING-VIS-001/bin/probe_mapping_dataset_metrics.py` comparing scaled vs refined contexts so we can quantify the improvement before touching Stage A.
