# Input

- Summary: Add the spec-required sigma-floor guard and telemetry so the variance-weighted loss stops diverging in Stage B/C and the clamp metrics appear in `/torch_diagnostics`.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/nanobrag_refinement.py::run_nanobrag_refinement` (plumb `sigma_floor` through Stage A/B/C variance calculations + telemetry) and `dbex/refine_one.py::_write_torch_outputs` (CLI flag + `/torch_diagnostics` attrs for the floor value and clamp fraction).
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_a.log`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_b.log`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_c.log`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_cli_diag.log`.
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/

## How-To Map
1. Extend `dbex/refine_one.py` CLI parsing with `--sigma-floor` (float ≥0, default 1.0) and document that it shares units with `sigma_rdout`. When `adu_per_photon` is set, divide both `sigma_rdout` and `sigma_floor` by the gain so the tensors stay in photons; plumb the scalar into `RefinementConfig(sigma_floor_value=...)`.
2. Update `dbex/nanobrag_refinement.py` to add `sigma_floor_value` to `RefinementConfig`, `variance_floor_value/variance_floor_clamp_fraction` to `RefinementTelemetry`, and compute `sigma_floor_sq = torch.tensor(config.sigma_floor_value**2, device=device, dtype=dtype)` once per stage.
3. In the Stage A/B/C loss functions, replace the `torch.clamp(..., min=1.0)` calls with `variance = torch.maximum(bragg_scaled.detach() + sigma^2, sigma_floor_sq)` and maintain integer counters of masked pixels vs. clamped pixels so telemetry can report the exact clamp fraction (fall back to 0.0 when no pixels contribute).
4. Thread the new telemetry fields through the per-stage dictionaries as well as `_write_torch_outputs` so `/torch_diagnostics/stage_{A,B,C}` now exposes `variance_floor_value` and `variance_floor_clamp_fraction` attrs; keep legacy masked-MSE traces untouched per DIAGNOSTICS-001.
5. Refresh `tests/dbex/test_torch_refine_smoke.py` Stage A/B/C cases to assert the new telemetry attrs (value matches the config, clamp fraction is within [0,1]) and re-enable the Stage B GPU path now that sigma-floor makes it numerically stable; update `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` mocks to include the new dataclass fields and assert the HDF5 group writes them.
6. Run the mapped pytest selectors with the documented env vars, tee logs into the artifact directory, and summarize chi-squared improvements plus clamp ratios in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/summary.md`.

## Pitfalls To Avoid
- Do not drop the `.detach()` on `I_model` inside the denominator; the IRLS behavior from spec-db-core.md must stay intact.
- `sigma_floor_value` lives in target units: convert when `adu_per_photon` is active and square it only once before clamping.
- Clamp fractions must count only masked pixels—don’t divide by total image pixels or include sentinel regions.
- Keep Stage B running on CUDA; if you flip it back to CPU the perf telemetry no longer covers the GPU divergence we just fixed.
- Update dataclasses, serialization, and tests together so `RefinementTelemetry` instances in unit tests don’t miss the new attributes.
- `/torch_diagnostics` schema is append-only: add new attrs/datasets but never remove or rename the legacy `masked_mse` fields.
- Preserve the existing Stage B/Stage C improvement gates (REFINE-008/REFINE-007); sigma_floor should not relax acceptance criteria.

## If Blocked
- If Stage B or Stage C still emit NaN/Inf gradients with the floor enabled, capture the failing pytest log plus the clamp statistics JSON (if any), stash them under the artifacts directory, and mark PHYSICS-LOSS-001 as `blocked` in docs/fix_plan.md citing spec-db-core.md:67.
- If the CLI metadata test fails because `_write_torch_outputs` lacks the new attrs, stop, save the pytest log, and update docs/fix_plan.md + this report instead of partially landing code.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — Stage A/B/C must share the weighted-loss denominator and emit both chi-squared + masked-MSE telemetry; this change keeps that invariant while hardening the variance floor.
- PHYSICS-LOSS-002 — Implement the sigma-floor guard and expose the clamp fraction so Stage B/C stop diverging on GPU.
- REFINE-005 — Stage B still requires halo-padded HKL grids + interpolation; make sure telemetry updates don’t bypass that guard.
- REFINE-007 — Stage C detector microslip gate stays at ≥0.002% improvement; compare chi-squared traces after the floor lands.
- REFINE-008 — Stage B improvement ceiling is ~1e-8; use chi-squared telemetry (with the new floor) when checking monotonicity.
- DIAGNOSTICS-001 — `/torch_diagnostics` schema must remain backward compatible when adding the variance-floor attrs.

## Pointers
- docs/spec-db-core.md:57 — Normative variance-weighted loss definition and the sigma-floor clause that motivates this loop.
- plans/active/PHYSICS-LOSS-001/implementation.md:31 — Phase B4/B5 checklist describing variance flooring + telemetry deliverables.
- tests/dbex/test_torch_refine_smoke.py:360, 621, 500 — Stage A/B/C smoke acceptance criteria you are extending with the new telemetry asserts.
- tests/dbex/test_refine_one_cli.py:600 — CLI diagnostics metadata test that verifies `/torch_diagnostics` attrs/datasets.
- docs/TESTING_GUIDE.md:1 — Authoritative command references and required env vars for the mapped selectors.

## Next Up (optional)
1. Replay DB-AT-024 mapping smoke under the chi-squared telemetry once sigma-floor plumbing is stable to close Phase C2.

## Mapped Tests Guardrail
- Each smoke selector above collects exactly one test; if fixtures misbehave, run the same command with `--collect-only`, stash the log, and mark the attempt blocked rather than claiming completion.
- The CLI metadata unit test should always collect; if it fails due to schema drift, halt and update the Do Now instead of pushing code without telemetry parity.
