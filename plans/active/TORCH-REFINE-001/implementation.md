# TORCH-REFINE-001 — LBFGS Refinement Nucleus (Stage A)

## Purpose
Establish the minimal, verifiable torch refinement loop using `torch.optim.LBFGS` with a closure that recomputes full masked MSE loss. The nucleus optimizes a tiny parameter set (global scale + one crystal DoF) to prove end-to-end descent, convergence gating, and optimizer telemetry, enabling incremental expansion to full staged refinement.

## References
- plans/nanobrag_integration_plan.md — Phase 3 and “Refinement Nucleus”
- docs/spec-db-workflow.md — Optimization Strategy (LBFGS + closure, staged refinement)
- docs/TESTING_GUIDE.md — Pytest selectors and artifact policy
- docs/development/TEST_SUITE_INDEX.md — Suite index (to be augmented once a selector is added)

## Exit Criteria
1) Deterministic ROI-sample loss decreases by ≥ 0.1% within ≤ 20 LBFGS steps; full-frame validation is non-increasing across the last 3 validations or meets LBFGS tolerances (REFINE-002 baseline).
2) `/torch_diagnostics` records optimizer telemetry: optimizer config, stage label, ROI sample fraction/counts, `loss_trace_sample`, `loss_trace_full`, `best_loss_full`, `param_deltas`, `status`.
3) Targeted pytest selector (refinement smoke) collects and passes; logs archived under this initiative.
4) No new collection failures introduced; ledger and docs updated.

## Phase Breakdown
- Phase A — Nucleus + targeted test
  - [x] A1: Implement `run_nanobrag_refinement` (or equivalent) nucleus optimizing {global scale, 1× crystal DoF} via LBFGS closure.
  - [x] A2: Add telemetry emission into `/torch_diagnostics` as specified; include param deltas and status.
  - [x] A3: Author a minimal pytest smoke test asserting loss decrease on deterministic ROI sample.
- Phase B — Stage scheduling + full-trace telemetry
  - [ ] B1: Add periodic full-frame validations and record `loss_trace_full`.
  - [ ] B2: Prepare stage expansion (parameter groups, learning rates) without enabling additional DoFs yet.
- Phase C — CLI wiring + docs sync
  - [ ] C1: Expose a backend flag/mode to run the nucleus; keep default behavior unchanged.
  - [ ] C2: Update docs (fix_plan Attempts History, TESTING_GUIDE/TEST_SUITE_INDEX if a new selector is added); archive artifacts.

### Outcome (2025-11-05T024454Z)
- Warm-started/clamped Stage A nucleus converges reliably: canonical refGeom run improves masked MSE by ~0.15%, satisfying the ≥0.1% REFINE-002 gate with telemetry status="early_stop".
- Telemetry includes required keys/traces; targeted smoke selector and full suite both pass (artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T024454Z/).

## Mapped Tests (active)
- Refinement smoke: `tests/dbex/test_torch_refine_smoke.py::test_loss_decreases`
  - Acceptance: masked MSE decreases by ≥ 0.1% in ≤ 20 steps with telemetry keys present and messaging referencing REFINE-002.

## Artifacts
- Reports directory: `plans/active/TORCH-REFINE-001/reports/<YYYY-MM-DDTHHMMSSZ>/`
  - `pytest_collect.log` — Collection evidence
  - `pytest_refine_smoke.log` — Targeted test run
  - `refine_telemetry.json` (optional) — Extracted telemetry from HDF5 for quick inspection
  - `summary.md` — Loop summary with Outcome / Issues / Next Intent

## How-To (initial draft; update per input.md Do Now)
- Targeted selector (after test lands):
  - `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases`
- Full suite (after nucleus stabilized):
  - `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/`

## Next Up (crumbs for supervisor)
- TORCH-REFINE-002 — Stage A expansion: full crystal (logs a,b,c; angles α,β,γ), orientation, global scale; same LBFGS closure, convergence/telemetry gates. See plans/nanobrag_integration_plan.md §Phase 3.
- TORCH-REFINE-003 — Stage C detector microslip: per‑panel normal translations (and optional small rotations), convergence/telemetry gates. See plans/nanobrag_integration_plan.md §Phase 3.
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional): per‑shell/global multipliers with regularization. See plans/nanobrag_integration_plan.md §Phase 3.
