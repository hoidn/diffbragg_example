Summary: Fix `build_mapping_stage_a_context` so it uses the smoke dataset’s HKL/calibration assets (not the golden fixtures), then re-run the mapping probe + DB-AT-028/029 to confirm ROI CC recovers or at least reflects the correct inputs.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T075900Z/

Do Now
- Implement: dbex/vis/mapping.py::build_mapping_stage_a_context — remove the hard-coded golden fixture fallback. Prefer `dataload.args.hkl_source_path` when present (defaulting to `dataload.args.mtzFile`), and only load calibration metadata when the caller provides an explicit `calibration_config_path`; otherwise skip calibration so we do not reuse the golden spot_scale_override. Update diagnostics to record the source paths actually used.
- Implement: tests/dbex/test_torch_refine_smoke.py::refgeom_dataload — thread a new optional env var `DBEX_SMOKE_CALIB_PATH` into the DataLoad args (attribute `calibration_config_path`) so mapping helpers can consume the smoke dataset’s calibration payload when it exists. Default to `None` to avoid silently reusing golden configs.
- Validate: (1) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=scaled.mtz python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T075900Z/mapping_cpu_gpu | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T075900Z/mapping_cpu_gpu/probe.log`  
  (2) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=scaled.mtz DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T075900Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T075900Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T075900Z/pytest_db_at_028_029.log`

How-To Map
1) Update `build_mapping_stage_a_context` to (a) respect `dataload.args.hkl_source_path` (set by DBEX_SMOKE_HKL_PATH) and (b) load calibration metadata only when `dataload.args.calibration_config_path` points to a real file. Remove the unconditional `tests/fixtures/golden_data/simple_cubic` fallback so diagnostics reflect the smoke dataset inputs.
2) Extend `tests/dbex/test_torch_refine_smoke.py::refgeom_dataload` to read `DBEX_SMOKE_CALIB_PATH`; when set, store it on the args namespace (attribute `calibration_config_path`). Default to `None` so we do not silently reuse golden calibration.
3) Ensure `build_mapping_stage_a_context` propagates the chosen HKL/calibration path into `MappingStageAContext.diagnostics` (fields `hkl_source`, `hkl_path`, `calibration_path`) so artifacts prove we are no longer pulling from the golden fixture.
4) After implementing, rerun the CPU/GPU mapping probe and DB-AT-028/029 according to the Validate commands; capture JSON/logs under the new artifacts path and summarize whether ROI CC improves or at least now reflects the smoke dataset HKL/calibration.

Pitfalls To Avoid
- Do not reintroduce the golden fixture fallback; if no calibration file exists for the smoke dataset, leave `calibration=None` instead of pulling from `tests/fixtures/...`.
- Preserve existing defaults so other callers (e.g., golden probe scripts) still work when they explicitly pass refined MTZ/calibration paths.
- Keep diagnostics device-neutral; when you rerun the probe, verify both CPU and GPU still agree within numerical noise.
- Always persist DB-AT metrics before assertions so artifacts exist even when tests fail.
- Environment freeze: use only existing deps/assets; no new package installs or downloads.

If Blocked
- If no smoke calibration file is available, document the missing path in `summary.md` and `docs/fix_plan.md` Attempts History, point `calibration_config_path` to `None`, rerun the probe/tests, and note that calibration is intentionally absent. Only mark blocked if `build_mapping_stage_a_context` cannot run without calibration (capture stack trace + env settings in artifacts).

Findings Applied (Mandatory)
- STAGEA-001 — Ensure mapping helpers respect the dataset’s calibration/HKL provenance; log the actual paths in diagnostics.
- GEOMETRY-003 / GEOMETRY-004 — Keep MappingStageAContext inputs unchanged; only the asset provenance changes.
- CONVERGENCE-001 — Verify zero-parameter mapping forward still matches DB-AT-024 semantics after the helper changes.
- PHYSICS-LOSS-001 — Variance-weighted chi² and masked pixel counts remain the reference in probe/test logs.
- POLICY-001 — Environment Freeze: only use locally available deps/scripts; no installs or external data pulls.

Pointers
- dbex/vis/mapping.py:100-220 — current helper with hard-coded golden fixtures; remove/refactor this logic.
- tests/dbex/test_torch_refine_smoke.py:70-140 — DataLoad fixture where we inject HKL/calibration paths.
- docs/spec-db-conformance.md:280-366 — DB-AT-028/029 tolerances.
- docs/TESTING_GUIDE.md:130-190 — Canonical DB-AT-028/029 commands/env.
- plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py — probe reference; rerun after the fix.

Next Up (optional)
- Once mapping helper parity is restored, revisit ROI diagnostics (triptychs) using the corrected helper so any geometric conclusions are trustworthy.

Doc Sync Plan (Conditional)
- None yet; if new ROI diagnostics promote to a selector/regression guard, run `pytest --collect-only` for the affected node and update docs/TESTING_GUIDE.md + docs/development/TEST_SUITE_INDEX.md after the code passes.

Mapped Tests Guardrail
- Ensure `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` reports both selectors (>0). Treat zero collection as a blocker before touching diagnostics.

Hard Gate
- Do not close the loop without: (a) updated diagnostics in the mapping probe JSON proving the HKL/calibration paths now point to the smoke dataset, (b) DB-AT-028/029 metrics/logs under the new artifacts path, and (c) summary.md describing whether ROI CC changed after the helper fix.

Normative Math/Physics
- Reference docs/spec-db-core.md §82-92 for variance/ROI correlation math in the probe; do not paraphrase equations or relax tolerances without spec approval.
