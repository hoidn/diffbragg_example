Summary: Compare mapping metrics for metadata+scaled vs metadata+refined HKL/calibration to pinpoint why DB-AT-028/029 remain negative before prescribing fixes.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::main — add a T2 probe that loads multiple mapping contexts (metadata+scaled.mtz with smoke calibration vs metadata+tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz with golden calibration), reuses build_mapping_stage_a_context so HKL/calibration flow matches the Stage A fixture, computes ROI CC, masked/unmasked scale ratios, bragg stats, and writes a diff JSON under the new artifacts directory so we can quantify the HKL/calibration effect driving the ROI CC gap.
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/mapping_dataset_metrics --cases metadata_scaled metadata_refined | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/mapping_dataset_metrics/probe.log; (2) same env plus DBAT028_ARTIFACT_DIR/DBAT029_ARTIFACT_DIR exports run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/pytest_db_at_028_029_collect.log; (3) execute the full pytest command with tee to plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/pytest_db_at_028_029.log and persist refreshed db_at_028/db_at_028_metrics.json + db_at_029/db_at_029_metrics.json even though the selectors still fail.

How-To Map
1) Export DBEX_SMOKE_SIGMA_SOURCE=metadata, DBEX_SMOKE_DETECTOR_SIZE=small, DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json, DBEX_SMOKE_HKL_PATH=scaled.mtz, KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1 before running any probes/tests so Stage A fixture and the new dataset probe share inputs.
2) Implement compare_mapping_dataset_metrics.py so it accepts a list of preset case names (metadata_scaled maps to expt=sp.proc/idx-0000_sigma_metadata.expt, refl=refGeom.refl, mask=747_mask.pkl, hkls=scaled.mtz, calibration=sp.proc/calibration/config_torch_smoke.json; metadata_refined swaps hkls for tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz and calibration for tests/fixtures/golden_data/simple_cubic/config_torch.json) and future cases can be added with the same pattern.
3) Reuse build_mapping_stage_a_context internally for each case (no ad-hoc forward code), emit per-case metrics (roi_cc_median, scale_ratio_masked/unmasked, bragg_mean/std/max, global_scale_hint, sigma_floor_value, spot_scale_override, calibration_path, hkl_source/path/count) plus a diff section comparing the first case to each additional case.
4) Run the probe once with --cases metadata_scaled metadata_refined, capture stdout + JSON to plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/mapping_dataset_metrics/ so the ledger can cite the exact ROI CC and scale deltas.
5) With the same env, run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" and pipe to the collect log; stop immediately if collection drops below 2 tests.
6) Run the full pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" command, tee the log, and ensure refreshed db_at_028/db_at_028_metrics.json and db_at_029/db_at_029_metrics.json land under the new artifacts directory even though the assertions fail.

Pitfalls To Avoid
- Do not let the dataset probe silently fall back to golden geometry for the metadata_scaled case; it must share the exact expt/refl/mask/MTZ/calibration the Stage A fixture uses to make the comparison meaningful.
- Keep build_mapping_stage_a_context as the only code path building mapping contexts; avoid bespoke simulate_forward_once calls that might bypass the telemetry fixes landed earlier.
- When adding the refined case, point hkls at tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz and calibration at tests/fixtures/golden_data/simple_cubic/config_torch.json explicitly—no relative wandering or git-ignored copies.
- Archive JSON/log outputs BEFORE asserting anything so partial runs still leave evidence per CONFORMANCE-001; the pytest selectors must write metrics even on failure.
- Do not tweak the DB-AT-028/029 tolerances; the point of this loop is data gathering, not weakening the gate.
- Ensure the new probe normalizes masked vs unmasked scale ratios consistently with the Stage A fixture (loss_mask vs full detector) so diffs are interpretable.

If Blocked
- If the probe cannot load either dataset (missing files, DataLoad errors), capture the stack trace in mapping_dataset_metrics/probe.log, drop a short blocker note into summary.md + docs/fix_plan.md, and stop before touching tests.
- If pytest --collect-only fails, record the stdout/stderr in the collect log, list the missing selectors in summary.md, and do not proceed to the full run.

Findings Applied (Mandatory)
- STAGEA-001 — Mapping calibration data must match the probe/test inputs; this script compares combinations without reintroducing the golden fallback silently.
- GEOMETRY-003 / GEOMETRY-004 — Mapping zero-point alignment relies on the same HKL/calibration metadata the Stage A engine consumes; reuse those helpers.
- PHYSICS-LOSS-001 — ROI CC and χ² interpretations must use the variance-weighted, masked metrics documented there; the probe’s outputs should follow that contract.
- CONFORMANCE-001 — DB-AT selectors must archive logs/metrics even while failing; keep the artifact policy intact.
- POLICY-001 — Stay inside the pre-provisioned environment; no new dependencies or dataset downloads.

Pointers
- docs/spec-db-conformance.md:280-366 — Canonical DB-AT-028/029 acceptance criteria and artifact expectations.
- docs/data_dependency_manifest.md:14-70 — Mapping helper inputs (HKL/calibration overrides) that the new probe must respect.
- docs/TESTING_GUIDE.md:136-176 — Command/env matrix for DB-AT-027/028/029 smokes.
- plans/active/TOOLING-VIS-001/implementation.md §Phase D.D — Context on Stage A mapping parity objectives.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/mapping_cpu_gpu/mapping_forward_cpu_gpu.json — Latest metadata+scaled failure signature to match when verifying probe outputs.

Next Up (optional)
- If the probe proves metadata+refined HKL restores ROI CC while metadata+scaled remains pathological, decide whether to reintroduce the refined HKL override for DB-AT-028/029 or generate a metadata-specific refined MTZ bundle as a dedicated follow-up initiative.

Doc Sync Plan (Conditional)
- None — no selectors are being added or renamed this loop; re-run the collect-only guard after code passes if you touch tests in a future loop.

Mapped Tests Guardrail
- Run pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" with the metadata env before the full run; stop and log a blocker if fewer than 2 tests collect.

Hard Gate
- Do not call the loop complete until mapping_dataset_metrics.json contains entries for both metadata_scaled and metadata_refined with ROI CC and scale ratios, and the new pytest artifacts for DB-AT-028/029 live under plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/.

Normative Math/Physics
- Reference docs/spec-db-core.md §§82-92 for the variance-weighted χ² and ROI correlation formulas when interpreting the dataset probe and pytest metrics—do not restate or approximate the math in code comments.
