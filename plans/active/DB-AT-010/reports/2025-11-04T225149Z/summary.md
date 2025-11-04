# DB-AT-010 Regression Triage — 2025-11-04T225149Z

## Focus
Reopen DB-AT-010 (Gradient correctness guard) after gradcheck regressions surfaced in the latest full-suite run. Goal: document failure signature, isolate the gradient break, and outline repair tasks for Ralph.

## Evidence
- `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_full_suite.log` — `test_db_at_010_gradcheck_crystal_cell_a` and wrapper selector fail with `torch.autograd.gradcheck.GradcheckError: Numerical gradient for function expected to be zero` (lines 82-280).
- `tests/dbex/test_gradients.py:202-229` — test harness converts the differentiable parameter tensor to a Python float via `cell_a_tensor.item()`, recreates a dxtbx crystal, and feeds it into `simulate_forward_torch`.
- `docs/development/testing_strategy.md:416-418` — gradient debugging guardrails call out `.item()` as a common cause for losing gradients (exact scenario observed here).

## Root Cause Hypothesis
Calling `.item()` on the gradcheck input detaches it from the autograd graph. The forward simulation still changes numerically when finite differences perturb the input (hence the non-zero numerical Jacobian), but PyTorch sees no differentiable path and reports the mismatch. Other parameter-specific tests happen to rebuild tensors differently (or rely on cached configs) so they still pass, but `cell_a` and the wrapper immediately fail, indicating we need a reusable pattern that keeps gradients alive when threading DIALS crystals through the bridge.

## Suggested Fix Scope for Ralph
1. Extend `simulate_forward_torch` (or a new helper) to accept crystal parameter overrides as `torch.Tensor` inputs so gradcheck callers can avoid `.item()` round-trips through dxtbx. One option: expose an optional `grad_config` dataclass that mirrors `CrystalConfig` but stores tensor-valued fields with `requires_grad` preserved, falling back to the current path when explicit overrides are absent.
2. Update the DB-AT-010 tests to use the new helper path: keep the differentiable tensor alive (e.g., clone + typecast) and feed it into the bridge without touching `.item()`/`.numpy()`. Confirm all four parameter-specific gradchecks pass with eps=1e-6, atol=1e-5, rtol=0.05.
3. Record the regression and remediation steps in `docs/fix_plan.md` and sync fresh gradcheck logs (`collect` + targeted run) under this timestamped report once Ralph lands the fix.

## Open Questions / Follow-ups
- Do we need additional bridge hooks for detector/beam parameters, or can we reuse the same strategy (tensor override) across all parameter types? Audit `create_detector_config` and `create_beam_config` before coding.
- Should we promote a new knowledge-base finding reminding engineers to avoid `.item()` in gradient-sensitive paths? If the fix introduces a reusable helper, we can reference it in `docs/findings.md`.

## Next Steps
- Update `docs/fix_plan.md` with a reopened DB-AT-010 entry (status `in_progress`) referencing this report.
- Produce a ready-for-implementation Do Now in `input.md` for Ralph covering the helper refactor + test adjustments + gradcheck selectors.
