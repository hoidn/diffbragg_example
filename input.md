Summary: Capture a canonical smoke calibration bundle (spot_scale_override + beam/crystal metadata) and point Stage A parity harnesses at it so mapping/Stage-A diagnostics stop falling back to golden fixtures.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py::main — add a T2 CLI that ingests the metadata smoke dataset (idx-0000_sigma_metadata.expt/refGeom.refl/scaled.mtz/747_mask.pkl), reuses the DiffBragg capture pipeline to recover spot_scale_override, beam flux/exposure/beamsize_mm, and N_cells, and emits `sp.proc/calibration/config_torch_smoke.json` plus a manifest (paths + SHA256) recorded under the artifacts directory.
- Implement: tests/dbex/test_torch_refine_smoke.py::refgeom_dataload — if `DBEX_SMOKE_CALIB_PATH` is unset but `sp.proc/calibration/config_torch_smoke.json` exists, set `args.calibration_config_path` to that file so Stage A parity fixtures and mapping probes default to the new calibration while still letting env vars override. Ensure diagnostics log the actual calibration path.
- Validate: (1) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small python plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --manifest plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/smoke_calibration_manifest.json | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/capture_smoke_calibration.log`  
  (2) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k \"DB_AT_028 or DB_AT_029\" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/pytest_db_at_028_029.log`  
  (3) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/mapping_cpu_gpu | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/mapping_cpu_gpu/probe.log`

How-To Map
1) Follow `sp.proc/sigma_metadata_manifest.json` to ensure the metadata sigma assets exist locally; if missing, rerun the documented embed command before attempting calibration capture.  
2) In `capture_smoke_calibration.py`, borrow the calibration extraction logic from `scripts/generate_simple_cubic_golden.py` / `dbex/run_diffbragg.run_diffbragg` so the script writes config metadata with spot_scale_override, beam flux/exposure, beamsize_mm, N_cells, HKL stats, and panel geometry. Persist SHA256 + provenance to `smoke_calibration_manifest.json`.  
3) Update `refgeom_dataload` so `args.calibration_config_path` defaults to `sp.proc/calibration/config_torch_smoke.json` when present; keep env overrides and log the resolved path in the existing diagnostics JSONs.  
4) Re-run the CPU/GPU mapping probe and DB-AT-028/029 under `DBEX_SMOKE_CALIB_PATH` to demonstrate the new calibration produces non-zero Bragg stacks and to capture before/after metrics in the artifacts directory. Summarize ROI CC + chi² signatures in summary.md.

Pitfalls To Avoid
- Do not resurrect the golden config fallback; the calibration must be derived from the metadata smoke dataset and recorded with a manifest.
- Capture SHA256 + command provenance for any new calibration assets (`sp.proc/calibration/config_torch_smoke.json`) per MANIFEST-001 rather than leaving ad-hoc files.
- Ensure `capture_smoke_calibration.py` reuses repo-local dependencies only (DiffBragg + hopper already vendored); no pip installs or CUDA toolchain changes.
- When wiring the default calibration path, guard on file existence so unit tests that purposely omit calibration still behave as before.
- Persist DB-AT artifacts (metrics JSON + diagnostics) before assertions even when tests fail; these runs remain FAIL until Stage A physics improves.

If Blocked
- If the calibration capture fails (e.g., hopper import error, missing sigma assets), record the exact command, stderr, and dataset state in summary.md + `docs/fix_plan.md`, stash the partial manifest/log under the artifacts directory, and mark TOOLING-VIS-001 blocked on the documented error instead of dropping back to the golden config.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A zero-point/mapping parity requires calibrated spot_scale_override + throughput metadata; the new calibration must satisfy this invariant.
- GEOMETRY-003 / GEOMETRY-004 — Preserve mapping-stage geometry/HKL provenance; calibration capture must not mutate the zero-point geometry.
- PHYSICS-LOSS-001 — Mapping probe + DB-AT-028/029 validations rely on variance-weighted chi²/ROI metrics; keep loss_mask semantics intact.
- CONFORMANCE-001 — Acceptance selectors must keep canonical env/commands/artefacts; archive new logs even when failing.
- POLICY-001 — Environment Freeze: use only repo-local tooling and document any targeted patches via manifests rather than touching the runtime.

Pointers
- docs/spec-db-conformance.md:287-349 — DB-AT-028/029 tolerances and telemetry requirements.
- docs/TESTING_GUIDE.md:130-190 — Canonical commands/env for DB-AT-028/029 plus artifact expectations.
- plans/active/TOOLING-VIS-001/implementation.md §Phase D — context for mapping alignment + calibration scope.
- scripts/generate_simple_cubic_golden.py & dbex/run_diffbragg.py — reference logic for extracting spot_scale_override/beam/N_cells and writing config_torch manifests.
- sp.proc/sigma_metadata_manifest.json — authoritative source for current metadata sigma assets and regeneration commands.

Next Up (optional)
- After calibration capture stabilizes mapping baseline, revisit the ROI triptych probe (`probe_mapping_roi_triptychs.py`) with the new calibration to isolate any remaining geometry/structure issues.

Mapped Tests Guardrail
- Verify `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` still reports both selectors before implementation; treat zero collection as a blocker.

Hard Gate
- Do not consider the loop done without (a) the new `config_torch_smoke.json` + manifest in both `sp.proc/calibration/` and the artifacts dir, (b) refreshed mapping probe JSON/logs proving we now have non-zero Bragg stacks and recorded calibration paths, and (c) DB-AT-028/029 artifacts executed under `DBEX_SMOKE_CALIB_PATH=<new file>`.

Normative Math/Physics
- Reference `docs/spec-db-core.md §§82‑92` for variance-weighted chi² and ROI correlation math in the capture script and diagnostics; do not relax tolerances without spec approval.
