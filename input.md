# Input

- Summary: Extend Stage B/C smokes plus docs so metadata sigma fixtures run without CLI overrides and still satisfy the Stage B/C telemetry gates.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full --smoke-sigma-source=metadata`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full --smoke-sigma-source=metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` + `tests/conftest.py::smoke_dataset_paths` + `docs/TESTING_GUIDE.md#1.4`/`docs/development/TEST_SUITE_INDEX.md:12` — mark Stage B/C selectors with `@pytest.mark.allow_metadata_sigma`, plumb the `--smoke-sigma-source` knob through their configs so metadata-backed datasets emit `sigma_readout_provenance="external_lookup"`, assert telemetry + clamp stats for both sigma sources, and refresh the docs/registry rows so Stage smoke instructions explain how to run metadata coverage end-to-end.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip} --smoke-detector-size=full --smoke-sigma-source=metadata | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/pytest_stage_bc_metadata.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/

## How-To Map
1. Inspect current skips via `rg -n "allow_metadata_sigma" tests/dbex/test_torch_refine_smoke.py` so the added markers land on Stage B/C selectors without touching other tests.
2. Update `tests/conftest.py::smoke_dataset_paths` and `tests/dbex/test_torch_refine_smoke.py::refinement_inputs` so metadata runs reuse the generated `sp.proc/idx-0000_sigma_metadata.expt` and assert `sigma_readout_map` exists before proceeding (continue to skip with actionable messaging when the asset is missing).
3. Modify `tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` to accept `smoke_sigma_source`, set `RefinementConfig.sigma_readout_provenance` dynamically, and add asserts that Stage B/C telemetry records `sigma_readout_provenance == ("external_lookup" if metadata else "cli_override")` plus non-zero `variance_floor_clamp_fraction` samples.
4. Refresh `docs/TESTING_GUIDE.md` §1.4 and `docs/development/TEST_SUITE_INDEX.md` Stage-smoke row so metadata instructions cover Stage B/C selectors, env vars (`DBEX_SMOKE_SIGMA_SOURCE`, `DBEX_SMOKE_DETECTOR_SIZE`), and artifact naming (e.g., `pytest_stage_b_metadata.log`, `pytest_stage_c_metadata.log`).
5. Run the mapped pytest selectors with metadata enabled, storing stdout/stderr under `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/` and capturing telemetry JSON if `DBEX_SMOKE_TELEMETRY_PATH` is set.

## Pitfalls To Avoid
1. Do not drop the CLI guard ordering—metadata is a fallback when neither scalar nor map overrides are passed.
2. Keep REFINE-008 Stage B gates intact (≤±1% modifier drift, χ² regression ≤1e-6) even when metadata changes the variance tensor.
3. Stage C strict gates (REFINE-007) still require ≥80% detector offset reduction and ≤0.05% χ² regression relative to Stage A; metadata runs must assert the same thresholds.
4. Ensure telemetry asserts use the canonical Stage A chi-squared snapshot so metadata provenance can be compared across stages.
5. Guard metadata fixtures with actionable skips when `sp.proc/idx-0000_sigma_metadata.expt` or `.sigma_tiles.pkl` is missing; never auto-regenerate inside tests.
6. Keep KMP_DUPLICATE_LIB_OK=TRUE + NANOBRAGG_DISABLE_COMPILE=1 in every command to satisfy runtime guardrails (RUNTIME-001).

## If Blocked
Capture failing pytest output plus `DBEX_SMOKE_SIGMA_SOURCE=metadata` env values in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/blocked.log`, note whether metadata fixtures exist under `sp.proc/`, and record the blocker + remedial steps inside `docs/fix_plan.md` Attempts History before pausing the initiative.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — Stage B/C must consume the same variance-weighted denominator as Stage A; metadata runs prove provenance parity.
- PHYSICS-LOSS-002 — Sigma-floor guards only work when variance tensors remain positive/finite; metadata fixtures must obey the same clamps.
- PHYSICS-LOSS-003 — Stage A chi-squared snapshots drive Stage C gating; metadata wiring keeps those units aligned.
- PHYSICS-LOSS-004 — Loader helper validations (shape/positivity) extend to the synthetic metadata assets; reuse the helper rather than rolling new parsing logic.
- PHYSICS-LOSS-005 — DIALS `external_lookup` remains the normative sigma source; tests must assert `sigma_readout_provenance="external_lookup"` when metadata is active.
- REFINE-007 — Stage C detector-offset gates rely on telemetry deltas; metadata runs cannot relax the ≥80% reduction rule.

## Pointers
- docs/fix_plan.md:15 — PHYSICS-LOSS-001 ledger + Attempts History.
- plans/active/PHYSICS-LOSS-001/implementation.md:70 — Phase G/H checklists tracking metadata fixture + smoke coverage.
- docs/TESTING_GUIDE.md:80 — Sigma readout workflows + Stage smoke command templates that must mention Stage B/C metadata coverage.
- docs/development/TEST_SUITE_INDEX.md:12 — Stage-smoke registry row to update with metadata selector instructions.
- tests/dbex/test_torch_refine_smoke.py:211 — `refinement_inputs` guard that currently skips metadata unless tests carry the `allow_metadata_sigma` marker.

## Next Up (optional)
1. After Stage B/C metadata runs pass, thread the metadata sigma source through DB-AT-024 and CLI diagnostics selectors so telemetry evidence spans all acceptance gates.
2. Package a reusable script (T2) that regenerates sigma metadata fixtures for other datasets if future detectors demand different tile values.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full --smoke-sigma-source=metadata > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/collect_stage_b_metadata.log`
