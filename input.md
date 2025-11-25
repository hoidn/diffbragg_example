Summary: Capture masked/unmasked scale diagnostics in mapping_context artifacts and rerun the metadata-smoke mapping probe plus DB-AT-028/029 to isolate the calibration mismatch.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests:
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/

Do Now
- Implement: dbex/vis/mapping.py::emit_mapping_context_diagnostics — extend the JSON diagnostics to record masked/unmasked target/Bragg means, both scale ratios, and the `global_scale_hint` so we can prove whether calibration metadata is driving the ROI anti-correlation. Wire the helper to keep existing fields stable and re-use numpy for all reductions (no new deps).
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_GEOM_PATH=sp.proc/refGeom_small/refGeom_small.expt DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_scaled metadata_refined --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/mapping_dataset_metrics | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/mapping_dataset_metrics/probe.log, (2) same env DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/pytest_db_at_028_029.log, (3) capture `pytest --collect-only` output to plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/pytest_db_at_028_029_collect.log. Expect mapping JSON to show refined vs scaled deltas and pytest to finish even if assertions fail.

How-To Map
1) export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md and the metadata env block from Do Now before any probe/test; keep them identical between commands so telemetry comparisons stay valid.
2) mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/{mapping_dataset_metrics,db_at_028,db_at_029} and note every stdout/stderr stream via tee into this tree (probe.log, pytest logs, collect-only log).
3) After modifying emit_mapping_context_diagnostics, run `python -m compileall dbex/vis/mapping.py` (fast sanity) before executing probes to ensure syntax is clean.
4) `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_scaled metadata_refined --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/mapping_dataset_metrics --device cuda:0 --default-sigma 3.0 | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/mapping_dataset_metrics/probe.log`; confirm the resulting JSON has the new masked/unmasked means/scale ratios for both cases.
5) `pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/pytest_db_at_028_029_collect.log` and stop if <2 tests collect.
6) `DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/pytest_db_at_028_029.log`; copy the refreshed metrics JSONs plus mapping_context_fixture.json files into the artifacts directory.

Pitfalls To Avoid
- Do not touch run_nanobrag_refinement or other production paths; diagnostics live purely in emit_mapping_context_diagnostics.
- Keep numpy reductions in float64 to avoid losing precision on the 3e17 spot_scale values.
- Preserve existing JSON keys so downstream scripts parsing mapping_context_fixture.json do not break.
- Never run pytest without DBEX_SMOKE_SIGMA_SOURCE=metadata; otherwise we regress to the cli_override path and miss the blocking signature.
- The dataset probe must run on the same GPU/driver as pytest; avoid mixing CPU/GPU because ROI CC changes slightly.
- Do not delete or overwrite prior artifacts; append new ones under the timestamped directory only.
- Ensure env vars don’t leak absolute paths into repo-relative JSON fields unless already required (use str(Path(...).resolve()) only where existing code expects it).
- Respect Environment Freeze: emit diagnostics with stdlib/numpy only.
- Make sure the metadata_refined case actually uses the refined MTZ/config paths; double-check the CLI output before trusting JSON.
- Keep DBAT028/029 logs even when they fail so Attempts History captures the signature per CONFORMANCE-001.

If Blocked
- If compare_mapping_dataset_metrics errors (e.g., missing MTZ), capture the traceback in plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/mapping_dataset_metrics/probe.log, update docs/fix_plan.md Attempts History with the error signature, and stop before touching pytest.
- If pytest --collect-only yields <2 tests with the metadata env, document the collection output, mark TOOLING-VIS-001 blocked due to fixture/env drift, and skip the full run.

Findings Applied (Mandatory)
- STAGEA-001 — Mapping and Stage A diagnostics must share HKL/calibration provenance; new metrics prove alignment.
- GEOMETRY-003 — Zero-point alignment depends on the canonical refGeom assets, so env overrides must keep geometry consistent during probe/test.
- SCALE-004 — Calibration metadata (spot_scale_override, flux) must be recorded anywhere simulate_forward_once is used.
- CONFORMANCE-001 — DB-AT selectors must persist diagnostics/logs regardless of pass/fail; tee outputs into the artifacts tree before assertions.

Pointers
- docs/fix_plan.md:211-360 — Current TOOLING-VIS-001 Attempts History and the calibration mismatch Next Actions we’re addressing.
- docs/TESTING_GUIDE.md:136-172 — DB-AT-028/029 selector contract and env requirements.
- docs/spec-db-core.md:37-115 — Variance-weighted chi² and sigma handling referenced by the new diagnostics fields.
- docs/data_dependency_manifest.md:30-120 — Mapping helper data provenance and required telemetry fields (HKL/sigma/calibration).

Next Up (optional)
- If scaled vs refined metrics diverge significantly, schedule the follow-up loop to patch the MTZ selection logic or Stage A calibration application accordingly.

Doc Sync Plan (Conditional)
- No new tests; if mapped selectors change names this loop (not expected) follow docs/TESTING_GUIDE.md §2 update rules.

Mapped Tests Guardrail
- Every run must include `pytest -q tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" --collect-only`; abort the loop if it reports <2 tests.

Hard Gate
- Do not mark the loop complete unless `mapping_dataset_metrics.json` contains both metadata_scaled and metadata_refined entries with the new diagnostics fields populated and `pytest_db_at_028_029.log` shows both selectors executed to completion (failures allowed but no errors).

Normative Math/Physics
- Follow docs/spec-db-core.md §§32-40 & 82-92 for sigma shapes and variance-weighted χ² definitions when interpreting the masked/unmasked means and scale ratios; no bespoke formulas.
