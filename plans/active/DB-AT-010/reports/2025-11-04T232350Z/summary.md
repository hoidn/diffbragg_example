# DB-AT-010 Regression Snapshot — Gradcheck failure returns

**Timestamp:** 2025-11-04T23:23:50Z (UTC)
**Focus:** DB-AT-010 — Gradient correctness guard (regression recovery)
**Mode:** Parity
**Action Type:** gathering_evidence

## Current Signal
- `pytest` full-suite log from MAP-SCALE-005 loop (`plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_full_suite.log`) shows `test_db_at_010_gradcheck_crystal_cell_a` and wrapper `test_db_at_010_gradcheck` failing with `torch.autograd.gradcheck.GradcheckError: Numerical gradient for function expected to be zero`.
- Failures reproduce both inside the parameter-specific test and the aggregate wrapper, confirming the gradcheck harness regressed.
- Other DB-AT-010 parameter tests (cell_gamma, detector_distance, beam_wavelength) still pass, narrowing scope to the crystal `cell_a` override path.

## Hypotheses
1. **Override path drift** — `simulate_forward_torch` still accepts `crystal_overrides`, but a recent change may be mutating the override tensors (e.g., casting to numpy or float) when rebuilding `CrystalConfig`, zeroing numerical gradients for `cell_a`.
2. **Loss surface mismatch** — Differences in scaling or mask handling (SCALE-001/002) could introduce asymmetry that pushes the finite-difference check outside tolerances for `cell_a` only.
3. **Gradcheck environment drift** — Environment variables (`NANOBRAGG_DISABLE_COMPILE=1`) might not be honored in the failing run; need to confirm before refactoring helpers.

## Evidence Collected
- Failure signature excerpt:
  - `torch.autograd.gradcheck.GradcheckError: Numerical gradient for function expected to be zero` at `tests/dbex/test_gradients.py:210`.
  - Wrapper failure repeats same signature (`tests/dbex/test_gradients.py:295`).
- `simulate_forward_torch` (dbex/nanobrag_bridge.py:1103-1236) still writes tensor overrides directly into `CrystalConfig`. Need to validate whether downstream `TorchCrystal` re-casts these values to Python floats.

## Exit Criteria Alignment
- `docs/fix_plan.md` entry for DB-AT-010 must be reopened to `Status: in_progress` with a new Attempts History row capturing the regression evidence.
- `plans/active/DB-AT-010/implementation.md` Phase D checklist already tracks override refactor work; reuse D1–D3 to drive the recovery loop.

## Proposed Next Investigation Steps
1. Reproduce failure locally with `pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --maxfail=1` to capture fresh logs under this timestamp.
2. Instrument `simulate_forward_torch` and `TorchCrystal` initialization to confirm whether `crystal_overrides['cell_a']` arrives as a differentiable tensor or gets coerced into a scalar before reaching autograd.
3. If coercion occurs, introduce a tensor-preserving bridge (e.g., keep overrides separate until TorchCrystal builds internal tensors) and update gradcheck tests accordingly.
4. Re-run DB-AT-010 selectors (collect-only + targeted) and sync documentation once the gradient path is restored.

Artifacts for this loop will accumulate under `plans/active/DB-AT-010/reports/2025-11-04T232350Z/`.
