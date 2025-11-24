# TOOLING-VIS-001 Phase D.B Planning — Stage A Engine Zero-Point Probe

**Generated:** 2025-11-24T215340Z
**Scope:** Translate the Phase D.A evidence into an actionable Phase D.B runbook. Cement DB-AT-027 tolerances inside a reusable engine-based probe and a pytest selector so calibration fixes can be validated with a single command.

## Phase D.A Recap (Evidence from 2025-11-24T213251Z)
- Mapping baseline (`test_db_at_024_mapping_smoke`) captured with metadata sigma: `chi2 = 9.898e5`, `chi2_per_pixel = 75.64`, `median_cc = 0.491`, `spot_scale_override = 3.18e17`.
- Stage A driver telemetry (LBFGS, 30 steps) shows catastrophic divergence:
  - `scale_ratio_before = 7.11e-05` (spec band [1e-2, 1e2]), `scale_ratio_after = 1.92`.
  - `mean_abs_diff_mapping = 77.43 ADU` (spec ≤ 1e-3), `max_abs_diff_mapping = 3.84e4 ADU` (spec ≤ 200).
  - `chi2_per_pixel_initial = 1.09e5`, `chi2_per_pixel_final = 2.35e4` (spec ≤ 100 per DB-AT-028).
  - `median_cc_stage_a_before = median_cc_stage_a_after = 0.128` (spec ≥ 0.2 per DB-AT-029).
- Diagnosis: Stage A zero-point reconstruction is missing mapping calibration (spot_scale_override, flux/exposure) and possibly the baseline UB state. Need an engine-based reproducer to guard this before plumbing the fix.

## Phase D.B Objectives
1. **Engine probe:** Provide a canonical helper that calls `run_nanobrag_refinement` with Stage A only, `max_iter=0`, and `use_engine_delegation=True`, then reconstructs the Bragg stack via `_build_final_bragg_from_stage_a_telemetry`.
2. **Spec metrics:** Compute `mean_abs_diff`, `max_abs_diff`, `chi2_stagea_at_mapping`, and ROI CCs against the mapping baseline using the canonical variance-weighted loss (`docs/spec-db-conformance.md:201-239`).
3. **DB-AT-027 selector:** Add `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` (xfail until calibration plumbing lands). Selector must cite spec clauses and assert the hard tolerances so the test flips to XPASS once Stage A honors the invariant.

## Proposed Implementation Steps (next loop)
1. **dbex/tools/stage_a_adam.py** — Add `run_engine_zero_point_probe()`:
   - Build `MappingStageAContext` (reuse `build_mapping_stage_a_context`).
   - Instantiate `RefinementConfig` (Stage A only, `max_iter=0`, sigma provenance carried through).
   - Run Stage A once (`run_nanobrag_refinement`) to obtain telemetry; clone telemetry dict, replace each `param_deltas[*]['final']` with `['initial']`, then feed `_build_final_bragg_from_stage_a_telemetry` to reconstruct `bragg_stagea_zero`.
   - Compute variance-weighted chi² on the mapping stack via `_compute_variance_weighted_loss` with `inputs.loss_mask` and `context.sigma_floor_value` (spec-db-core.md §86-90).
   - Emit metrics dict (mean/max abs diff, chi² values, CC samples) and return both the metrics and raw arrays so tests/scripts can persist them.
2. **Plan-local script** — Create `plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py` (T2 helper): CLI flag for `--out-dir`, writes `stage_a_engine_zero_point.json` with the metrics from Step 1 plus provenance (data paths, sigma policy, tolerances). Script will feed Phase D.C and D.D loops.
3. **Pytest selector** — New module `tests/dbex/test_stage_a_mapping_equiv.py` with `@pytest.mark.xfail(strict=True, reason="TOOLING-VIS-001 Stage A zero-point miscalibration (spot_scale missing)")`. The test should:
   - Call `run_engine_zero_point_probe()`.
   - Assert `mean_abs_diff <= 1e-3`, `max_abs_diff <= 200`, and `abs(chi2_rel_diff) <= 1e-3` referencing `docs/spec-db-conformance.md`.
   - Log diff metrics when failing so Phase D.C can compare before/after.
4. **Docs/test registry sync** — Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` to register DB-AT-027 once the test exists. Archive `pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py -k DB_AT_027` output in this loop’s artifacts.

## Risks / Open Questions
- **Runtime:** Stage A zero-iteration run still invokes panel forward pass; expect ≤45s on CPU. Acceptable for a Tier 1 selector.
- **Telemetry shape:** `_build_final_bragg_from_stage_a_telemetry` currently assumes final param deltas; confirm zero-iter telemetry still populates `param_deltas[*]['initial']` and `['final']`. If not, capture guards inside the helper (fallback to mapping to avoid crashes).
- **Sigma provenance:** Ensure `RefinementConfig.sigma_readout_provenance` is forwarded from `MappingStageAContext.inputs`; otherwise, Stage A might clamp to CLI defaults and skew chi².

## Deliverables for Next Loop
- `plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py`
- `tests/dbex/test_stage_a_mapping_equiv.py`
- Updated `dbex/tools/stage_a_adam.py` helper + docs/test registry entries.
- Artifacts under `plans/active/TOOLING-VIS-001/reports/2025-11-24T215340Z/`:
  - `zero_point_probe_plan.md` (this file)
  - `summary.md` (turn summary per supervisor instructions)
  - `pytest_db_at_027_collect.log` (after code passes)
  - `stage_a_engine_zero_point.json` produced by the new script on the canonical fixture.
