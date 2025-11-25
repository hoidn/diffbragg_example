Summary: Use the captured smoke calibration bundle to rerun the mapping probe and DB-AT-028/029 so we can prove Stage A is finally reading the right calibration path and record it in every artifact.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/

Do Now
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — persist the resolved calibration metadata (calibration_path, spot_scale_override) from mapping_context.diagnostics into both the mapping_context_fixture JSON and the db_at_028/db_at_029 metrics before assertions so we can prove the selectors used sp.proc/calibration/config_torch_smoke.json.
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::compute_cpu_gpu_mapping_metrics — include calibration_path + spot_scale_override (per device) in the JSON/summary output so the CPU/GPU probe always reports which config_torch file it consumed.
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --manifest plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/smoke_calibration_manifest.json | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/capture_smoke_calibration.log; (2) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/mapping_cpu_gpu | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/mapping_cpu_gpu/probe.log; (3) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/pytest_db_at_028_029.log (collect-only first if the selectors were touched).

How-To Map
1) Re-run the capture script from repo root (command above) so the manifest references this checkout; verify the sha256 embedded in the manifest matches `sha256sum sp.proc/calibration/config_torch_smoke.json` and leave both files under sp.proc/calibration/ plus the artifacts directory.
2) Before running probes/tests, export `DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json` (repo-relative) so refgeom_dataload and the CPU/GPU probe both pick up the new config. Keep other smoke env vars (sigma source, detector size, CUDA guards) identical to the history runs for apples-to-apples comparison.
3) Update stage_a_smoke_result to grab `mapping_context.diagnostics["calibration_path"]` and copy it into the fixture JSON + db_at metrics; do not mutate the diagnostics dict after storing the string. While touching the fixture, assert the field is not None so failures surface early.
4) Extend compute_cpu_gpu_mapping_metrics to include both the calibration path and spot_scale_override for CPU and GPU; keep the schema backward compatible by adding new keys rather than renaming existing ones.
5) Run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the canonical env to confirm both selectors still collect before executing the full tests.
6) Execute the CPU/GPU probe and pytest commands from Do Now, ensuring `DBAT028_ARTIFACT_DIR` and `DBAT029_ARTIFACT_DIR` point into the new artifact directory so JSON/log files capture the calibration_path fields even if assertions fail.
7) Record ROI CC, scale ratios, chi²/pixel, and the calibration path used in summary.md; if spot_scale_override remains ~3e17, call it out explicitly so we know the metadata capture reproduces the large scale.

Pitfalls To Avoid
- Do not fall back to the golden config or run probes/tests without `DBEX_SMOKE_CALIB_PATH`; the goal is to validate the new smoke calibration.
- Keep dataset/HKL/sigma sources identical between the capture script, probe, and pytest run; mismatched inputs invalidate comparisons.
- Archive mapping diagnostics and db_at metrics before pytest assertions so artifacts exist even on failure.
- When logging calibration_path, use explicit strings (Path.resolve())—do not log Python objects or None placeholders.
- Leave the existing ROI metric fields untouched; new calibration metadata must be additive so downstream scripts do not break.
- Do not “fix” the huge spot_scale_override in code unless you have evidence; just make it observable and document the result for now.
- Avoid rerunning capture/probe in parallel with pytest; reuse the same env so cached detectors/HKL grids do not diverge mid-loop.
- Preserve the Environment Freeze: use repo-local hopper/diffBragg modules only and capture any errors instead of pip-installing fixes.
- Ensure `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` exist before pytest so metrics land under artifacts/2025-11-25T074043Z.
- Respect the deterministic flags (KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1) exactly as documented in docs/TESTING_GUIDE.md.

If Blocked
- If the capture script fails (e.g., hopper import error, missing sigma assets), save the full traceback to capture_smoke_calibration.log, note the failure in summary.md, and update docs/fix_plan.md Attempts History with the error signature + dataset state instead of dropping back to the golden config.
- If pytest refuses to collect DB-AT-028/029 even after collect-only, stop immediately, record the collect-only output in the artifacts directory, and mark TOOLING-VIS-001 blocked pending selector repair.

Findings Applied (Mandatory)
- STAGEA-001 — Mapping and Stage A must share identical calibration payloads; log calibration_path + spot_scale_override to prove compliance.
- GEOMETRY-003 / GEOMETRY-004 — Mapping context uses the incremental UB baseline; do not mutate geometry when rerunning probes.
- PHYSICS-LOSS-001 — Use the canonical variance-weighted chi²/ROI metrics when interpreting probe and pytest results.
- CONFORMANCE-001 — DB-AT selectors must archive artifacts even when they fail; keep DBAT028/029 logs + JSON in the artifacts path.
- POLICY-001 — Environment Freeze: rely solely on repo-local DiffBragg/simtbx tooling and document any missing dependency as a blocker.

Pointers
- docs/spec-db-conformance.md:280-349 — Acceptance gates for DB-AT-028/029 (chi² per pixel, ROI CC bands, artifact requirements).
- docs/data_dependency_manifest.md:14-45 — Source-of-truth for DBEX_SMOKE_* env vars and calibration routing; confirms refgeom_dataload defaults.
- docs/TESTING_GUIDE.md:130-190 — Canonical commands/env vars for Stage A smoke selectors; matches the envs listed above.
- plans/active/TOOLING-VIS-001/implementation.md §Phase D.D — Context and objectives for mapping/Stage A alignment, including calibration plumbing scope.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/ (manifest + capture log) — Use as a reference when verifying sha256 + metadata in the new artifacts.

Next Up (optional)
- If ROI CC remains negative even with the captured calibration, pivot to inspecting capture_smoke_calibration.py output vs DiffBragg telemetry (spot_scale units) before adjusting Stage A physics.

Doc Sync Plan (Conditional)
- Not needed unless new tests are added; if selectors or probe scripts change names, refresh docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after the code passes.

Mapped Tests Guardrail
- Confirm `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` returns two collected nodes before running the full tests; document the output under the artifacts directory if collection fails.

Hard Gate
- Do not claim the loop complete until the mapping probe JSON and both db_at_028/db_at_029 metrics include the calibration_path field populated with sp.proc/calibration/config_torch_smoke.json and the pytest log reflects execution under `DBEX_SMOKE_CALIB_PATH`.

Normative Math/Physics
- Reference docs/spec-db-core.md §§82-92 for the variance-weighted chi² and ROI correlation formulas when analyzing the probe + pytest outputs; do not rewrite the math inline.
