Summary: Reshape the smoke calibration capture output to the DiffBragg config_torch schema so Stage A actually loads the metadata, then rerun the mapping probe and DB-AT-028/029 with DBEX_SMOKE_CALIB_PATH pointing at the regenerated config.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py::capture_calibration_metadata — emit a DiffBragg-style config_torch payload (nested crystal.scale_override / crystal.N_cells and beam.flux / beam.exposure / beam.beamsize_mm) plus matching manifest entries so dbex.nanobrag_bridge.load_calibration_metadata stops raising KeyError and build_mapping_stage_a_context receives the real calibration dict.
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --manifest plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/smoke_calibration_manifest.json | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/capture_smoke_calibration.log; (2) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/mapping_cpu_gpu | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/mapping_cpu_gpu/probe.log; (3) Same env vars + DBAT028_ARTIFACT_DIR/DBAT029_ARTIFACT_DIR export run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/pytest_db_at_028_029_collect.log`; (4) Execute the full pytest command with tee to `pytest_db_at_028_029.log` and persist refreshed db_at_028/db_at_028_metrics.json + db_at_029/db_at_029_metrics.json in the new artifacts directory.

How-To Map
1) Before editing, compare `sp.proc/calibration/config_torch_smoke.json` against `tests/fixtures/golden_data/simple_cubic/config_torch.json` and `dbex/nanobrag_bridge.py:1602-1675` to list the exact keys load_calibration_metadata requires; use that checklist while reshaping the capture payload.
2) Update `capture_smoke_calibration.py` so `calibration_config` mirrors the DiffBragg structure (top-level metadata/device, nested `beam` and `crystal` sections, existing manifest hashes) without dropping the provenance block or the SHA256 verification; keep helper `to_native` conversions intact.
3) After running the capture CLI, record the SHA256 printed in `smoke_calibration_manifest.json` inside summary.md and verify the manifest grows the `manifest_sha256` field.
4) Run the CPU/GPU mapping probe with `DBEX_SMOKE_CALIB_PATH` set; inspect `mapping_forward_cpu_gpu.json` to confirm both metrics now show `spot_scale_override≈3.1e+17`, non-zero bragg stats, and `calibration_path` resolves to the regenerated config.
5) Run `pytest --collect-only` and then the full `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the canonical env (metadata sigma, small detector, CUDA guards, DBAT artifact dirs pointing into the new reports folder); archive both the collect-only and execution logs plus refreshed db_at_028/db_at_028_metrics.json and db_at_029/db_at_029_metrics.json.
6) Summarize whether the selectors still fail; explicitly call out the new mapping probe ROI CC / chi² numbers and the recorded `spot_scale_override` in `summary.md` so we know the calibration now actually loads.

Pitfalls To Avoid
- Do not invent a new schema for config_torch; mirror the nested keys (`beam.*`, `crystal.*`) exactly or load_calibration_metadata will continue to ignore it.
- Keep the manifest SHA256 logic identical so the provenance ledger stays reproducible.
- Ensure the regenerated config lives at `sp.proc/calibration/config_torch_smoke.json` (repo-relative) before running probes/tests—stale configs elsewhere won’t be picked up by DBEX_SMOKE_CALIB_PATH.
- Preserve the existing CLI defaults (sigma=metadata, detector_size=small, deterministic CUDA flags) when rerunning probes/tests so results compare apples-to-apples with prior artifacts.
- Archive mapping probe JSON/logs and db_at metrics before assertions: even failing selectors must leave evidence under the artifacts directory per CONFORMANCE-001.
- Don’t massage the huge spot_scale_override value; the goal is to record it accurately and prove it flows through telemetry, not to clamp/scale it.
- Avoid touching production `dbex` modules in this loop; only the plan-local capture script should change.
- When verifying JSON output, watch for NaN ROI CC values—if bragg stacks are still zero, capture the probe log and stop instead of proceeding to more diagnostics.

If Blocked
- If hopper/simtbx refuses to run (import error, GPU failure, etc.), capture the full traceback in `capture_smoke_calibration.log`, drop a short blocker note into summary.md + docs/fix_plan.md Attempts History, and stop rather than reverting to the golden config.
- If load_calibration_metadata still sees KeyError after restructuring, persist the failing JSON + exception text under the artifacts path and mark TOOLING-VIS-001 blocked on schema alignment.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A diagnostics must reuse mapping calibration; fixing the schema ensures calibration_path proves compliance.
- GEOMETRY-003 / GEOMETRY-004 — Mapping context defines the zero-point geometry; new calibration data must not change those invariants.
- PHYSICS-LOSS-001 — Mapping probe/DB-AT-028/029 analysis hinges on the variance-weighted chi² + loss mask semantics documented there.
- SCALE-002 — spot_scale_override is applied as sqrt(scale_override); keeping the canonical schema preserves that derivation.
- POLICY-001 — Environment Freeze remains in effect; use only bundled simtbx/diffBragg bits and record any missing dependency as a blocker.

Pointers
- docs/spec-db-conformance.md:280-349 — Acceptance gates for DB-AT-028/029 (chi²-per-pixel, ROI CC bands, artifact policy).
- docs/data_dependency_manifest.md:14-45 — Required env vars and telemetry fields for mapping helpers (DBEX_SMOKE_HKL_PATH / DBEX_SMOKE_CALIB_PATH).
- dbex/nanobrag_bridge.py:1602-1675 — load_calibration_metadata schema expectations that the capture script must satisfy.
- plans/active/TOOLING-VIS-001/implementation.md §Phase D.C/D.D — Context on mapping-calibration plumbing and why DBEX_SMOKE_CALIB_PATH is required before further physics debugging.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/mapping_cpu_gpu/mapping_forward_cpu_gpu.json — Reference failure signature showing calibration_path recorded but spot_scale_override stuck at 1.0.

Next Up (optional)
- Once calibration loads and metrics stop being NaN, proceed with the Phase D.D zero-point probe to compare `_build_final_bragg_from_stage_a_telemetry` vs mapping and isolate the remaining chi² gap.

Doc Sync Plan (Conditional)
- None — no new selectors are being added or renamed in this loop; only existing probes/tests rerun.

Mapped Tests Guardrail
- Run `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the canonical env before executing the tests; archive the collect output under the artifacts path and stop if collection fails.

Hard Gate
- Do not call the loop done until the new `mapping_forward_cpu_gpu.json` shows `spot_scale_override≈3.1e+17` and `calibration_path` resolving to `sp.proc/calibration/config_torch_smoke.json`, and both db_at_028/db_at_029 metrics JSONs include the same calibration_path/spot_scale fields captured from the rerun.

Normative Math/Physics
- Reference docs/spec-db-core.md §§82-92 for the variance-weighted chi² and ROI correlation formulas when interpreting probes/tests; do not restate the math inline.
