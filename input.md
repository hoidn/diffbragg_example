# Input

- Summary: Finish PHYSICS-LOSS-001 by upgrading Stage B/C to the chi-squared loss and emitting chi-squared + masked-MSE telemetry/diagnostics.
- Mode: none
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/nanobrag_refinement.py::compute_loss_stage_b + compute_loss_stage_c + RefinementTelemetry/run_nanobrag_refinement` (reuse `inputs.sigma_readout` so Stage B/C minimize the same chi-squared denominator as Stage A, capture per-stage chi-squared + masked-MSE traces, and expose those metrics via telemetry); `dbex/refine_one.py::_write_torch_outputs` (persist per-stage `chi_squared` + `masked_mse` attrs/datasets while keeping legacy trace fields); `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (assert new diagnostics attributes so regressions surface).
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`, and `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (tee logs into the artifacts directory).
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/

## How-To Map
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` before editing to document provenance for every command/run in the artifacts log.
2. In `dbex/nanobrag_refinement.py`, thread `inputs.sigma_readout` through Stage B/C: convert to device/dtype once, fetch panel slices like Stage A, reuse the chi-squared formula (detached denominator) for both sample/full evaluations, and keep masked-MSE companions for telemetry reporting. Ensure Stage B’s improvement gates compare Stage A vs Stage B chi-squared values, and Stage C’s improvement uses Stage A vs Stage C chi-squared. Guard `sigma_readout` shape mismatches explicitly.
3. Extend `RefinementTelemetry` (and the per-stage builders inside `run_nanobrag_refinement`) with explicit `chi_squared_trace_full`, `chi_squared_best`, `masked_mse_trace_full`, and `masked_mse_best` fields plus scalar `chi_squared_initial/final` helpers so downstream consumers can read both metrics without re-parsing traces.
4. Update `_write_torch_outputs` to emit the new metrics under `/torch_diagnostics` (top-level Stage A attrs + per-stage `stage_<label>` groups). Keep existing datasets/attrs for backward compatibility; simply add new attrs/datasets for chi-squared + masked-MSE where appropriate.
5. Refresh `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` to assert the new telemetry attrs exist and reflect the mocked values so CLI regressions trip quickly.
6. Run the Stage B and Stage C smokes with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/pytest_stage_b.log` and the analogous Stage C command (tee to `pytest_stage_c.log`). Capture the CLI diagnostics unit test log as `pytest_cli_diag.log`. Note skips/missing assets explicitly in the artifacts summary.

## Pitfalls To Avoid
- Keep the variance denominator detached per spec-db-core.md:67; detaching numerators or ROI masks will break gradients.
- Stage B must stay behind halo/interpolation guards (REFINE-005); don’t bypass the halo check when wiring `sigma_readout`.
- Do not mutate `RefinementTelemetry` fields in-place after serialization; copy tensors to CPU scalars/lists to keep JSON encoding safe.
- Stage B/C ROI samplers rely on deterministic panel IDs; avoid re-randomizing when plumbing new tensors.
- `tests/dbex/test_torch_refine_smoke.py` requires refGeom assets; skip politely if `refGeom.refl` missing and record the skip reason in artifacts instead of forcing failures.

## If Blocked
- If refGeom assets are unavailable, run each smoke selector with `--collect-only`, save the log under `plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/collect_stage_b.log` (and `_stage_c.log`), mark PHYSICS-LOSS-001 as blocked in `docs/fix_plan.md`, and halt implementation work.
- If CLI diagnostics test fails because `score_trainer` or `h5py` is missing, capture the ImportError trace in the artifacts summary and record the failure in `docs/fix_plan.md` before stopping.

## Findings Applied (Mandatory)
- DIAGNOSTICS-001 — `/torch_diagnostics` must retain standardized metadata; extend attrs without removing `masked_mse`, `loss_mask_coverage`, etc.
- REFINE-005 — Stage B/C must keep tricubic interpolation with haloed HKL grids while reworking the loss.
- REFINE-007 — Stage C improvement gate is calibrated to ≈0.003% on refGeom; keep chi-squared telemetry to preserve that guard.
- REFINE-008 — Stage B improvement ceiling is ~1e-8, so telemetry must still track deterministic ROI sampling and best-loss iterations under the chi-squared metric.
- PHYSICS-LOSS-001 — Stage B/C telemetry must capture chi-squared + masked-MSE so cross-stage comparisons stay meaningful.

## Pointers
- `docs/spec-db-core.md:32-68` — Variance-weighted loss contract (sigma plumbing + detached denominator).
- `plans/active/PHYSICS-LOSS-001/implementation.md:31-63` — Phase B checklist split (B2b/B2c describe the Stage B/C tasks plus telemetry exit criteria).
- `tests/dbex/test_torch_refine_smoke.py:602-741` — Stage B smoke requirements, gates, and ROI sampling expectations.
- `tests/dbex/test_torch_refine_smoke.py:453-590` — Stage C smoke requirements and calibrated improvement gate.
- `dbex/refine_one.py:520-640` — `_write_torch_outputs` structure for `/torch_diagnostics`; extend here for chi-squared attrs.

## Next Up (optional)
1. DB-AT-024 (C2) — Re-run the mapping selector once telemetry is stable to confirm variance plumbing didn’t regress zero-iteration parity.
2. Stage A smoke revisit — Re-tune `min_loss_improvement` if chi-squared scaling alters convergence (C3).

## Doc Sync Plan (Conditional)
- Not needed this loop (no new selectors); reuse existing Stage B/C smoke + CLI unit selectors.

## Mapped Tests Guardrail
- Each Stage B/C smoke selector currently collects one test when refGeom assets exist; if `pytest --collect-only` drops to 0, stop and document the missing assets instead of proceeding.
- `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` always collects 1 test; treat missing `score_trainer` as a blocker and log the ImportError.
