Summary: Add an engine-based Stage A zero-point probe plus DB-AT-027 (xfail) selector so calibration gaps are documented before plumbing fixes.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/

Do Now
- Implement: dbex/tools/stage_a_adam.py::run_engine_zero_point_probe + tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity — add an engine-delegation zero-point helper that reuses MappingStageAContext (Stage A only, max_iter=0, calibration payload preserved), reconstructs `bragg_stagea_zero` via `_build_final_bragg_from_stage_a_telemetry`, computes mean/max |Δ| + chi² stats, exposes them via a plan-local CLI (`plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py`), and wires a strict xfail pytest selector that asserts the DB-AT-027 tolerances so we know exactly when calibration plumbing lands. Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md to register the selector once code passes.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/{stage_a_engine_zero_point.json,pytest_db_at_027.log,pytest_db_at_027_collect.log,summary.md}

How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/stage_a_engine_probe` before running anything so evidence lands deterministically.
2. Implement the helper inside `dbex/tools/stage_a_adam.py` (next to `run_zero_point_check`): reuse `build_mapping_stage_a_context`, construct `RefinementConfig(device="cpu", max_iter=0, enable_stage_b=False, enable_stage_c=False, sigma_readout_provenance=inputs.sigma_readout_provenance)`, call `run_nanobrag_refinement(..., use_engine_delegation=True)`, deep-copy telemetry to force each `param_deltas[*]['final'] = ['initial']`, and feed `_build_final_bragg_from_stage_a_telemetry` to get `bragg_stagea_zero`. Use `_compute_variance_weighted_loss` with `context.inputs` + `context.sigma_floor_value` to compute Stage A chi² on the mapping stack and return a dict with `mean_abs_diff`, `max_abs_diff`, `chi2_stagea`, `chi2_mapping`, `chi2_rel_diff`, `variance_floor_masked_pixels`, and ROI CC samples.
3. Author `plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py` (T2 script) that accepts `--out-dir`, calls the helper, and writes `stage_a_engine_zero_point.json` plus a short stdout summary. Default should remain timestamped `stage_a_engine_probe/<timestamp>` when `--out-dir` is omitted.
4. Create `tests/dbex/test_stage_a_mapping_equiv.py` with `@pytest.mark.xfail(strict=True, reason="TOOLING-VIS-001 Stage A zero-point miscalibration (spot_scale_override missing)")` and a test function that calls the helper, logs the metrics, and asserts `mean_abs_diff <= 1e-3`, `max_abs_diff <= 200`, and `abs(chi2_rel_diff) <= 1e-3` (cite `docs/spec-db-conformance.md:201-239`). Fail fast with informative messages so XPASS immediately highlights success once calibration plumbing lands.
5. Run the helper via CLI to capture evidence: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/stage_a_engine_probe`. Archive the resulting JSON in the artifacts directory.
6. Execute the pytest selector from the Do Now and tee output to `pytest_db_at_027.log` under the artifacts directory. After the test passes/xfails, run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/pytest_db_at_027_collect.log` and update the testing docs per the Doc Sync Plan.

Pitfalls To Avoid
- Do NOT loosen DB-AT-027 tolerances; failures must remain xfail until calibration plumbing (Phase D.C) succeeds.
- Preserve the mapping calibration payload entirely (spot_scale_override, flux, exposure, N_cells, sigma_floor); copying data manually will silently change the spec contract.
- Ensure `max_iter=0` truly skips LBFGS updates so telemetry initial/final match; add guards if the optimizer rewrites params when no iterations occur.
- Stage A helper must stay CPU-only to avoid CUDA nondeterminism unless the Testing Guide explicitly calls for GPU.
- Keep plan-local script T2-compliant (argparse header, docstring) and avoid referencing repo-relative paths that break when run from other directories.
- Record every env var used in the CLI logs so Phase D.C comparisons are reproducible.
- When updating docs/TESTING_GUIDE.md and TEST_SUITE_INDEX.md, describe the selector status as `xfail (known calibration gap)` rather than `active` if it still fails.
- Treat any import errors as blockers per Environment Freeze; document them in docs/fix_plan.md instead of installing packages.
- Do not reuse the Adam debug helper inside pytest; the selector must exercise the real engine path.
- Keep ROI CC calculations masked; unmasked comparisons will mix background noise and hide failures.

If Blocked
- If `run_nanobrag_refinement` fails before emitting telemetry (e.g., missing assets), capture the stack trace in `stage_a_engine_zero_point.json`, mark `[TOOLING-VIS-001]` blocked in docs/fix_plan.md with the error signature, and stop before touching tests/docs.
- If the xfail selector refuses to collect (e.g., plugin errors), log the collect-only output, update docs/fix_plan.md Attempts History, and request supervisor guidance before modifying thresholds.

Findings Applied (Mandatory)
- GEOMETRY-003 — Mapping baseline misset invariants require reusing MappingStageAContext for the zero-point helper.
- GEOMETRY-004 — Incremental UB zero-point guarantees mean we must reconstruct Bragg stacks via `_build_final_bragg_from_stage_a_telemetry` instead of ad-hoc path.
- PHYSICS-LOSS-001 — Variance-weighted chi² must use the canonical sigma_floor clamp when comparing Stage A vs mapping telemetry.
- CONFORMANCE-001 — DB-AT selectors (027) define the contract; pytest logs + collect output must be archived per Testing Guide §2.
- STAGEA-001 — Documented Stage A zero-point miscalibration motivates the new helper and xfail test; keep evidence tied to this finding.

Pointers
- docs/spec-db-conformance.md:200-280 — DB-AT-027/028/029 tolerances for mean/max |Δ|, chi²_per_pixel, ROI CC.
- docs/spec-db-workflow.md:42-58 — Mapping zero-point invariant and calibration payload details.
- docs/TESTING_GUIDE.md §2 — Selector registration policy + env knobs for DB-AT probes.
- plans/active/TOOLING-VIS-001/implementation.md:180-247 — Phase D checklist context for D.A/D.B/D.C.
- plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_mapping_diagnosis.md — Evidence motivating the zero-point helper.

Next Up (optional)
- Phase D.C: plumb calibration payload + log-scale warm starts into Stage A engine once DB-AT-027 instrumentation is in place.

Doc Sync Plan (Conditional)
- After implementation passes, run `pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027` (log to artifacts), then add the selector to docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with status `xfail (known Stage A zero-point gap)`.

Mapped Tests Guardrail
- `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` must collect (xfail accepted). Treat a zero-collection event as a block and stop to update docs/fix_plan.md if it happens.

Hard Gate
- DB-AT-027 remains active and cannot be downgraded; the helper/test should fail/xfail until calibration plumbing brings `mean_abs_diff <= 1e-3`, `max_abs_diff <= 200`, `|chi2_rel_diff| <= 1e-3`.

Normative Math/Physics
- Reference `docs/spec-db-conformance.md:201-239` verbatim for the zero-point equations and use the canonical variance-weighted chi² from `docs/spec-db-core.md:86-90`; no ad-hoc reinterpretations.
