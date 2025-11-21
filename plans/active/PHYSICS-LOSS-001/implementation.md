# PHYSICS-LOSS-001 — Variance-Weighted Loss Function

## Initiative
- ID: PHYSICS-LOSS-001
- Title: Implement Variance-Weighted Loss (Poisson + Readout)
- Status: in_progress (2025-11-20)

## Goals
- Replace the scientifically incorrect "Masked MSE" (homoscedastic) loss with a variance-weighted loss (heteroscedastic) matching `spec-db-core.md`.
- Ensure the variance term `V = I_model + sigma_readout^2` uses a detached denominator (IRLS approximation) to prevent "attraction to infinity" artifacts.

## Phases Overview
- Phase A — Bridge Data: Plumbing `sigma_rdout` from DataLoad to RefinementInputs.
- Phase B — Engine Logic: Implementing the weighted loss and updating telemetry.
- Phase C — Validation: Gradient checks and convergence verification.

## Exit Criteria
1. `RefinementInputs` contains `sigma_rdout` tensor (photon units).
2. Refinement loop uses `loss = sum((pred - target)^2 / (pred.detach() + sigma_rdout**2))`.
3. DB-AT-010 (Gradcheck) passes with the new loss formulation.
4. Telemetry reports `chi_squared` (weighted) and `masked_mse` (unweighted).

## Phase A — Bridge Data
### Checklist
- [x] A1: Update `RefinementInputs` dataclass in `dbex/nanobrag_bridge.py` to include `sigma_readout` tensors.
- [x] A2: Update `prepare_refinement_inputs` to normalize readout noise (broadcast scalars, convert to photons when `adu_per_photon` supplied, zero outside the loss mask).
    - Logic: If `adu_per_photon` provided, `sigma_photons = sigma_adu / gain`.
    - Fallback: If no metadata, assume `sigma_readout = 0` (Poisson-only variance) and warn via CLI flag help text.
- [x] A3: Update `tests/dbex/test_nanobrag_bridge.py` to assert `sigma_readout` presence, dtype, broadcast handling, and photon conversion.

## Phase B — Engine Logic
### Checklist
- [x] B1: Update `compute_masked_mse_loss` (used in tests) to accept variance or rename/replace with `compute_weighted_loss`.
- [x] B2a: Update Stage A LBFGS closures to minimize `chi_squared = Sum((pred-target)^2 / (pred.detach() + sigma_readout**2))` while logging masked-MSE companions.
- [x] B2b: Update Stage B shell-modifier closures to consume `inputs.sigma_readout` (same variance model as Stage A) so Stage A↔Stage B improvements use consistent units. (Delivered in `ec6f485` with artifacts at `plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/pytest_stage_b.log`.)
- [x] B2c: Update Stage C detector distance closures to consume `inputs.sigma_readout` and report chi-squared traces that align with Stage A’s denominator. (Delivered in `ec6f485`; see `pytest_stage_c.log` in the same artifact set.)
- [x] B3: Add `chi_squared` to `RefinementTelemetry` and `_write_torch_outputs`, preserving masked-MSE traces for legacy consumers. (Validated via `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` artifacts.)

## Phase C — Validation
- [x] C1: Run `DB-AT-010` (Gradcheck). *Note: The loss value will change, but gradients must remain correct.*
- [ ] C2: Run `DB-AT-024` (Mapping). *Re-run the zero-iteration mapping selector (new artifact folder) and confirm chi-squared telemetry matches masked-MSE companions; capture the `pytest_db_at_024.log` output.*
- [ ] C3: Run Stage A Smoke. *Replay `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` with chi-squared telemetry enabled, refresh metrics snapshots, and document any gate adjustments caused by the new loss scale.* 

### Risks
- **Scale Shift:** MSE is typically large (~10^6). Chi-squared is normalized (≈ N_pixels). L-BFGS tolerances (`tolerance_change`) are absolute; they may need retuning for the new loss scale (e.g., 1e-9 → 1e-4).
