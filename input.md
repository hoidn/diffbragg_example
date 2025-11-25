Summary: Persist the DiffBragg-refined HKL asset during smoke calibration capture and rewire the Stage A fixtures to consume it so mapping + DB-AT-028/029 finally share calibrated structure factors (hkl_source="refined").
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests:
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py::capture_calibration_metadata and tests/conftest.py::refgeom_dataload — add a `--refined-mtz-out` option that copies the DiffBragg `_temp.mtz` produced during calibration capture into `sp.proc/calibration/smoke_refined_structure_factors.mtz`, record its SHA256 in the manifest, and make the Stage A smoke fixtures plus mapping helpers default their HKL source to this refined file (hkl_source="refined") whenever metadata calibration is requested.
- Validate: (1) `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors.mtz DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/mapping_cpu_gpu_refined` (expect `hkl_source="refined"`, ROI telemetry captured); (2) `DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/db_at_029` with the same env block `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/pytest_db_at_028_029.log` (collect-only first, then full run; failures allowed but runs must finish and fixtures must report hkl_source="refined").
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/

How-To Map
1) `python plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config sp.proc/calibration/config_torch_smoke.json --refined-mtz-out sp.proc/calibration/smoke_refined_structure_factors.mtz --manifest plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/smoke_calibration_manifest.json | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/capture_smoke_calibration.log` (records new SHA256 entries for both config + refined MTZ).
2) `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors.mtz DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1` (keep for steps 2-4).
3) `python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/mapping_cpu_gpu_refined | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/mapping_cpu_gpu_refined/probe.log` and verify JSON shows `hkl_source="refined"`, `sigma_provenance="cli_map"`, and ROI telemetry populated.
4) `DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/db_at_029 pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/pytest_db_at_028_029_collect.log` (guardrail ≥2 tests collect).
5) Rerun the same env/dirs with `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/pytest_db_at_028_029.log`; inspect `db_at_028/mapping_context_fixture.json` & `db_at_029/mapping_context_fixture.json` to ensure they show the refined HKL path.

Pitfalls To Avoid
- Do not leave `_temp.mtz` dangling; copy/rename it to the tracked refined MTZ and remove any stale temp once manifest is updated.
- Keep the calibration config and refined MTZ in sync; if capture fails midway, do not reuse previous files silently.
- When updating the fixture defaults, preserve overrides (`DBEX_SMOKE_HKL_PATH`) and detector-size branching.
- Ensure docs/data_dependency_manifest.md reflects the new asset and overrides in the same commit.
- Mapping probe + DB-AT selectors must run with identical env vars; do not test with mixed HKL/calibration sources.
- Maintain ASCII JSON (no NaN/Inf) when writing manifest entries.
- Avoid touching Stage A production code paths beyond the fixture/helper scope; keep edits limited to tooling + data plumbing.

If Blocked
- If DiffBragg capture cannot produce the refined MTZ (hopper error, missing assets), tee the full stderr/stdout to `plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/capture_smoke_calibration_failed.log`, note the error in docs/fix_plan.md Attempts History, and pause before modifying fixtures.
- If pytest still reports `hkl_source="raw"` after code changes, stop and archive `mapping_forward_cpu_gpu.json` plus fixture JSONs showing the mismatch.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A diagnostics must consume calibration + HKL assets from the same dataset; documenting the refined MTZ satisfies this invariant.
- SCALE-004 — DiffBragg-refined structure factors must accompany calibration metadata; raw `scaled.mtz` + calibration mix collapses ROI CC (docs/findings.md:38).
- CONFORMANCE-001 — DB-AT selectors still need full artifact capture even on assertion failure.

Pointers
- plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py (adds refined MTZ persistence logic).
- tests/conftest.py:148-230 (refgeom_dataload / smoke_dataset_paths HKL defaults).
- docs/data_dependency_manifest.md:1-80 (mapping + Stage A asset provenance, needs refined MTZ entry).
- docs/findings.md:33-42 (SCALE-001/004 rationale for pairing calibration with refined |F|).

Next Up (optional)
- After refined HKL ingestion succeeds, re-evaluate ROI diagnostics/DB-AT tolerances to decide whether further calibration or HKL provenance work is needed.

Doc Sync Plan (Conditional)
- Not required (no new selectors, existing pytest nodes reused).

Mapped Tests Guardrail
- `pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only` must report ≥2 collected tests before running the full suite.

Hard Gate
- Do not mark the loop complete until `mapping_cpu_gpu_refined/mapping_forward_cpu_gpu.json` shows `hkl_source="refined"` and both Stage A fixture JSONs under db_at_028/db_at_029 record the refined HKL path plus calibration path, and the pytest command finishes (failures acceptable).

Normative Math/Physics
- Reference `docs/spec-db-core.md` §§32-92 and `docs/spec-db-workflow.md` Stage A clauses for the variance-weighted chi² and calibration ladder; no alternate math shortcuts.
