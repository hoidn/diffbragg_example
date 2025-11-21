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
    - Guardrail (new): If detector metadata cannot supply `sigma_readout`, the CLI MUST require a non-zero override; silent fallback to zeros violates `spec-db-core.md`.
- [x] A3: Update `tests/dbex/test_nanobrag_bridge.py` to assert `sigma_readout` presence, dtype, broadcast handling, and photon conversion.
- [x] A4: Update CLI ingestion (`dbex/refine_one.py`) so `--sigma-rdout` (or equivalent metadata source) is mandatory when the detector lacks calibrated dark noise, and fail fast with actionable messaging; emit telemetry describing the provenance (`calibrated`, `cli_override`).

## Phase B — Engine Logic
### Checklist
- [x] B1: Update `compute_masked_mse_loss` (used in tests) to accept variance or rename/replace with `compute_weighted_loss`.
- [x] B2a: Update Stage A LBFGS closures to minimize `chi_squared = Sum((pred-target)^2 / (pred.detach() + sigma_readout**2))` while logging masked-MSE companions.
- [x] B2b: Update Stage B shell-modifier closures to consume `inputs.sigma_readout` (same variance model as Stage A) so Stage A↔Stage B improvements use consistent units. (Delivered in `ec6f485` with artifacts at `plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/pytest_stage_b.log`.)
- [x] B2c: Update Stage C detector distance closures to consume `inputs.sigma_readout` and report chi-squared traces that align with Stage A’s denominator. (Delivered in `ec6f485`; see `pytest_stage_c.log` in the same artifact set.)
- [x] B3: Add `chi_squared` to `RefinementTelemetry` and `_write_torch_outputs`, preserving masked-MSE traces for legacy consumers. (Validated via `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` artifacts.)
- [x] B4: Implement variance flooring per `spec-db-core.md` (`V = max(I_model + sigma_readout^2, sigma_floor^2)`) across Stage A/B/C, expose `sigma_floor` via CLI/env, and emit telemetry covering clamp rate + floor value.
- [x] B5: Update Stage A/B/C GPU smoke tests (`tests/dbex/test_torch_refine_smoke.py`) to supply deterministic `sigma_readout` fixtures and assert that telemetry reports the correct provenance + clamp statistics.

## Phase C — Validation
- [x] C1: Run `DB-AT-010` (Gradcheck). *Note: The loss value will change, but gradients must remain correct.*
- [x] C2: Run `DB-AT-024` (Mapping). *Re-ran the zero-iteration mapping selector with the new diagnostics, asserted chi-squared/sigma-floor telemetry, and captured artifacts in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/{pytest_db_at_024.log,mapping_metrics.json}`.*
- [x] C3: Run Stage A Smoke. *Replayed `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` on the full detector, asserted the canonical chi-squared snapshot, and stored telemetry/logs in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/{pytest_stage_a_full.log,telemetry_stage_a.json}`.* 

### Risks
- **Scale Shift:** MSE is typically large (~10^6). Chi-squared is normalized (≈ N_pixels). L-BFGS tolerances (`tolerance_change`) are absolute; they may need retuning for the new loss scale (e.g., 1e-9 → 1e-4).

## Phase D — Canonical chi-squared alignment
### Checklist
- [x] D1: Add a shared variance-weighted loss helper in `dbex/nanobrag_refinement.py` that consumes a cached `sigma_floor_sq` tensor and returns Σ((pred-target)^2 / V), masked-MSE companions, and clamp counts so every stage (sampled + full validations) executes the exact spec-db-core.md:57-68 equation. *(Delivered 2025-11-21T051747Z — `_compute_variance_weighted_loss` now powers Stage A/B/C closures.)*
- [x] D2: Thread the helper through Stage A/B/C closures + telemetry, ensuring Stage C improvement logic compares Stage A final chi-squared against Stage C final using identical units and that Stage B gates reference the Stage A canonical chi-squared snapshot. *(Delivered 2025-11-21T051747Z — canonical chi-squared metadata recorded for Stage B/C + CLI diagnostics.)*
- [x] D3: Update `tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` and `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` to assert Stage A/B/C chi-squared traces fall within ≤1e-6 relative agreement when run on the canonical detector, and archive the new telemetry/logs under `plans/active/PHYSICS-LOSS-001/reports/<timestamp>/`. *(Delivered 2025-11-21T051747Z — canonical Stage A telemetry asserted in Stage B/C smokes and CLI metadata test.)*

## Phase E — Calibrated sigma-map ingestion
- [x] E1: Extend the CLI/DataLoad surface to accept calibrated readout-noise tensors (e.g., `--sigma-map` pointing to `.npy` or pickled tuple of per-panel arrays), validate the payload is strictly positive and shape-aligned with `DataLoad.data`, and expose it via `DataLoad.sigma_readout_map`. *(Delivered 2025-11-21T060701Z — `load_sigma_readout_map()` enforces `[panel, slow, fast]` alignment plus positivity before caching the tensor.)*
- [x] E2: Teach `_resolve_sigma_readout()` to consume `DataLoad.sigma_readout_map` when present (priority below CLI scalars), convert to photons when `--adu-per-photon` is specified, compute the reference median, and tag telemetry/`RefinementConfig` with `sigma_readout_provenance="calibrated_map"`. *(Delivered 2025-11-21T060701Z — CLI + telemetry now record calibrated-map provenance and medians.)*
- [x] E3: Add regression coverage (`tests/dbex/test_refine_one_cli.py`) proving nanobrag runs without `--sigma-rdout` when a calibrated map is injected, plus unit tests for the loader helper; update `docs/TESTING_GUIDE.md` + `docs/development/TEST_SUITE_INDEX.md` instructions to describe the new workflow and emit artifacts showing both CLI selectors pass with the sigma-map path. *(Delivered 2025-11-21T060701Z — sigma-map CLI + loader tests recorded under `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/`.)*

## Phase F — DIALS metadata sigma harvesting
- [x] F1: Implement a `DataLoad` helper that inspects `Experiment.imageset.external_lookup` for calibrated readout-noise tiles (`ExternalLookupItemDouble`), converts them to `[panel, slow, fast]` NumPy tensors, validates positivity/shape, and populates `sigma_readout_map` when `--sigma-map` is absent.
- [x] F2: Update `_resolve_sigma_readout()` and telemetry so metadata-derived tensors set `sigma_readout_provenance="external_lookup"` (post ADU→photon conversion) while preserving CLI override precedence and reference medians.
- [x] F3: Extend regression/unit tests (e.g., `tests/dbex/test_data_load_sigma_map.py` plus CLI guard tests) to cover external-lookup ingestion, fallback ordering (CLI scalar > CLI map > metadata), and documentation updates (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) referencing the metadata workflow and new artifacts.

## Phase G — Metadata fixture + Stage smoke validation
- [ ] G1: Author `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` that copies an `.expt` file, injects calibrated `ExternalLookupItemDouble` tiles (from `--sigma-map` or constant `--sigma-value`) for each panel, and documents provenance in a JSON/README so smoke tests can generate metadata fixtures deterministically.
- [ ] G2: Extend smoke fixtures (`tests/conftest.py`) and `tests/dbex/test_torch_refine_smoke.py` to parameterize the sigma source (`cli_override` vs `metadata`), route metadata-backed datasets into `prepare_refinement_inputs`, and assert Stage A telemetry reports `sigma_readout_provenance="external_lookup"` when metadata is selected.
- [ ] G3: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with the metadata-fixture workflow (script invocation, required env vars, mapped selectors) and capture Stage A full-detector logs plus telemetry JSON showing the metadata provenance under `plans/active/PHYSICS-LOSS-001/reports/<timestamp>/`.
