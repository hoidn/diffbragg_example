Summary: Capture and wire a detector-size–specific smoke calibration bundle for the refGeom_small Stage A fixture so probes and DB-AT-028/029 stop mixing small-geometry data with the full-detector calibration.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T213500Z/

Do Now:
- Implement: tests/conftest.py::refgeom_dataload — make the calibration/HKL resolver detector-size aware so `DBEX_SMOKE_DETECTOR_SIZE=small` drives `config_torch_smoke_small.json` + `smoke_refined_structure_factors_small.mtz` (with override envs still authoritative) while the full-detector fixture keeps using the canonical files.
- Validate: `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` under the metadata env to archive fresh telemetry showing the new small-calibration bundle; failures expected on chi²/ROI CC but logs must capture the detector-specific paths.

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T213500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p "$REPORT"/{capture_small,mapping_dataset_metrics,db_at_028,db_at_029}`.
2. Generate the detector-specific bundle: `python plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/refGeom_small/refGeom_small.expt --refl sp.proc/refGeom_small/refGeom_small.refl --mask sp.proc/refGeom_small/refGeom_small_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke_small.json --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors_small.mtz --manifest "$REPORT"/capture_small/smoke_calibration_small_manifest.json | tee "$REPORT"/capture_small/capture_small.log`.
3. After editing `.gitignore` + `tests/conftest.py`, update any tooling constants that hardcoded `config_torch_smoke.json` (e.g., `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::define_cases`) so metadata cases pick the detector-specific file when `DBEX_SMOKE_DETECTOR_SIZE=small`.
4. Probe the effect: `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_raw metadata_calibrated cli_raw cli_calibrated --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir "$REPORT"/mapping_dataset_metrics | tee "$REPORT"/mapping_dataset_metrics/probe.log` (leave `DBEX_SMOKE_HKL_PATH` unset so the resolver chooses the new refined MTZ).
5. Export artifacts env for DB-AT selectors: `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`.
6. `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log`.
7. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log`; expect failures on the existing chi²/ROI CC gates but confirm the emitted `mapping_context_fixture.json` files now reference `config_torch_smoke_small.json` + `smoke_refined_structure_factors_small.mtz`.

Pitfalls To Avoid:
- Do not regress the override precedence: `DBEX_SMOKE_HKL_PATH` / `DBEX_SMOKE_CALIB_PATH` must still win over the detector-size defaults.
- Keep the full-detector fixture wired to the canonical calibration files; the new `_small` bundle is ONLY for `DBEX_SMOKE_DETECTOR_SIZE=small`.
- Update tooling scripts that hand-roll dataset paths; otherwise probes and pytest will drift again.
- Capture manifest/log artifacts for the new bundle so reviewers can verify SHA256 and provenance.
- Preserve lazy imports/device neutrality in fixtures; no CUDA-only assumptions.
- Leave environment freeze untouched—no package installs to unblock capture.
- Archive probe/pytest logs even though selectors will keep failing on physics thresholds.
- Record the new calibration assets in docs/data_dependency_manifest.md so future loops know which files belong to which detector size.

If Blocked:
- If the capture script fails on the refGeom_small inputs, stash the stack trace in `$REPORT/capture_small/capture_small.log`, mention the failing command in summary.md, and log the blocker in docs/fix_plan Attempts History before stopping.
- If pytest can no longer collect the smoke selectors after the fixture change, keep the collect log, triage for ≤15 minutes, and if unresolved mark TOOLING-VIS-001 blocked with the signature in fix_plan + summary (do not revert the change).

Findings Applied (Mandatory):
- STAGEA-001 — Stage A/mapping tooling must consume the same calibration + HKL provenance; detector-specific bundles keep the zero-point invariant intact.
- SCALE-004 — Refined structure factors must pair with the calibration metadata; producing a small-detector refined MTZ enforces that requirement.
- SCALE-005 — Calibration provenance must stay auditable; scripts/tests must emit the new calibration path so telemetry tracks which bundle was used.

Pointers:
- docs/data_dependency_manifest.md:34-95 — refGeom smoke fixtures + calibration/HKL precedence rules that need to reflect the detector-specific bundle.
- docs/findings.md:9-55 — STAGEA/SCALE guardrails on calibration/HKL usage.
- plans/active/TOOLING-VIS-001/implementation.md:1-200 — initiative goals and Phase D acceptance gates for DB-AT-027/028/029.
- docs/fix_plan.md:330-360 — latest TOOLING-VIS-001 attempts plus the small-calibration plan.
- tests/dbex/test_stage_a_smoke_parity.py:70-210 — Stage A smoke fixtures whose behavior you’re changing.

Next Up (optional):
- If the detector-specific calibration still leaves ROI CC≈-0.04, follow up with a calibration-component probe (spot scale vs N_cells vs beam flux) before touching Stage A physics.
