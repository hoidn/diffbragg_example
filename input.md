# Input

- Summary: Align Stage A/B/C chi-squared math with the spec so the new sigma-floor telemetry stops tripping Stage B and the `/torch_diagnostics` traces share one unit system.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/nanobrag_refinement.py::run_nanobrag_refinement` (factor a shared variance-weighted helper so Stage A/B/C all sum `(diff**2 / variance)` with the same precomputed `sigma_floor_sq` tensor + clamp counters, replacing Stage A’s current `(Σ diff^2)/(Σ variance)` shortcut) and `tests/dbex/test_torch_refine_smoke.py::{test_stage_a_expansion,test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` (refresh telemetry assertions to verify the new chi-squared scale + variance-floor stats, plus keep CLI metadata coverage in `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`).
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/pytest_stage_a.log`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/pytest_stage_b.log`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/pytest_stage_c.log`, `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/pytest_cli_diag.log`.
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/

## How-To Map
1. In `dbex/nanobrag_refinement.py`, introduce a small helper (module-local) that accepts `(bragg_tensor, target_tensor, loss_mask, sigma_tensor, sigma_floor_sq_tensor)` and returns `(chi_squared_sum, masked_mse, masked_pixels, clamped_pixels)` using the spec formula `Σ((diff**2)/max(I_model_detached + sigma^2, sigma_floor_sq))`; keep the denominator detached and reuse the helper everywhere.
2. Precompute `sigma_floor_sq_value = config.sigma_floor_value ** 2` once per stage, wrap it in a tensor with `device/dtype` only once (outside panel loops), and feed it plus the helper outputs into the existing variance-floor telemetry accumulators so we stop allocating throwaway tensors per panel.
3. Replace the Stage A `chi_squared_loss = numerator / Σ variance` block with the helper output so chi-squared traces for Stage A/B/C share the same unit system; verify Stage A `best_loss_full` and `chi_squared_trace_*` are updated via the new values so Stage B/C gates compare like-for-like.
4. Update Stage B/Stage C `compute_loss_*` functions to call the helper for each panel instead of open-coding the math, sum the helper outputs, and leave the IRLS detach semantics intact; this should also surface the NaN gradient culprit if any mask generates bogus denominators.
5. Extend `tests/dbex/test_torch_refine_smoke.py` Stage A/B/C cases to assert the new `variance_floor_value`/`variance_floor_clamp_fraction` attrs plus sanity-check the chi-squared magnitudes (Stage A final ≈ Stage B initial ≈ Stage C initial once the helper is shared); refresh the CLI metadata test so its fake telemetry objects include the new fields.
6. Run the mapped pytest selectors with the mandated env vars (see docs/TESTING_GUIDE.md §1.1) and tee logs into this loop’s artifact directory; summarize final chi-squared/improvement/clamp stats in `summary.md` afterward.

## Pitfalls To Avoid
- Do not leave Stage A’s legacy `(Σ diff^2)/(Σ variance)` code path around; the helper must be the single source of truth or Stage B/C will stay mismatched.
- Keep the variance denominator detached; dropping `.detach()` violates spec-db-core.md:57-68 and reopens the “attraction to zero” bug.
- Count clamp fractions only over masked pixels and guard against divide-by-zero (set to 0 when no pixels contribute) to keep telemetry sane.
- Reuse tensors instead of calling `torch.tensor(0.0, ...)` inside tight loops; allocate a cached zero tensor via `torch.zeros(1, device=device, dtype=dtype)` or `torch.zeros_like` to avoid needless grad edges.
- Preserve Stage B’s halo/interpolation guards (REFINE-005) and Stage C’s ≥0.002% gate (REFINE-007); don’t paper over failures by relaxing thresholds.
- When editing tests, keep `KMP_DUPLICATE_LIB_OK=TRUE`/`NANOBRAGG_DISABLE_COMPILE=1` in place so we continue running on the same CUDA path that exposed the bug.
- `/torch_diagnostics` is append-only; only add attrs/datasets, never rename the existing `masked_mse` keys.
- Make sure telemetry dataclasses and CLI serialization stay in sync; updating one without the other will break the CLI metadata test immediately.

## If Blocked
- If Stage B still throws the NaN/Inf gradient after the helper refactor, capture the failing pytest log plus any new clamp stats JSON under this loop’s artifacts, mark PHYSICS-LOSS-001 as `blocked` in docs/fix_plan.md with the error signature, and stop implementation work.
- If the helper refactor uncovers missing imports or unavailable modules, treat the missing dependency as a blocker per Environment Freeze policy and log it in docs/fix_plan.md instead of attempting installs.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — All stages must emit both chi-squared and masked-MSE traces using the same variance-weighted denominator; the helper ensures that invariant.
- PHYSICS-LOSS-002 — Sigma-floor guard + clamp telemetry stays mandatory for GPU stability; keep the floor tensorized once per stage.
- PHYSICS-LOSS-003 — Stage A must stop using `(Σ diff^2)/(Σ variance)` so Stage B/C gates compare identical chi-squared units.
- REFINE-005 — Stage B shells still require halo-padded HKL interpolation; do not bypass those guards while refactoring the loss.
- REFINE-007 — Stage C detector microslip gate remains ≥0.002% improvement; validate against the new chi-squared trace.
- DIAGNOSTICS-001 — `/torch_diagnostics` schema must stay backward compatible while adding new attrs.

## Pointers
- docs/spec-db-core.md:57-80 — Normative variance-weighted loss definition + sigma-floor clause guiding this refactor.
- dbex/nanobrag_refinement.py:740-795 — Current Stage A ratio-of-sums code that needs to move to the shared helper.
- plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_b.log:60-99 — Evidence of Stage B dying before recording any samples because of the NaN/Inf gradient guard.
- plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_c.log:112-134 — Stage C gate comparing 8.09e3 vs 3.02e8 chi-squared values due to mixed definitions.
- docs/TESTING_GUIDE.md:1-34 — Required env flags and guardrails for the mapped selectors.

## Next Up (optional)
1. Replay DB-AT-024 mapping (tests/dbex/test_db_at_024_mapping.py) with the new chi-squared telemetry once Stage A/B/C smokes pass to close Phase C2.

## Mapped Tests Guardrail
- Each smoke selector above collects one test; if `pytest --collect-only` shows 0 items, author a minimal reproducer before proceeding and log the block.
- Keep the CLI metadata unit test in the mapped list; if the telemetry shape changes again, update the test in the same loop rather than downgrading it.
