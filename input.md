# Input

- Summary: Land the variance-weighted chi-squared loss path so Stage A/B run against the PhysSpec denominator and emit chi-squared telemetry.
- Mode: none
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: dbex/refine_one.py::create_parser + run_nanobrag_backend (add --sigma-rdout CLI plumbing, compute/emit chi_squared), dbex/nanobrag_refinement.py::run_nanobrag_refinement (Stage A/B/C closures consume inputs.sigma_readout tensors and minimize `Sum((pred-obs)^2 / (pred.detach()+sigma_rdout^2))` while persisting chi-squared telemetry), dbex/nanobrag_bridge.py::compute_masked_mse_loss + tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck (replace the masked-MSE helper with a variance-weighted version, update gradcheck fixtures/selectors to feed sigma tensors, and assert diagnostics capture chi_squared alongside masked_mse).
- Test: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/

## How-To Map
1. Extend `dbex.refine_one` parser with `--sigma-rdout` (units: photons) and default to CLI override or metadata helper; plumb the parsed float into `prepare_refinement_inputs(..., sigma_readout=sigma)`.
2. Convert `inputs.sigma_readout` to a torch tensor in `run_nanobrag_refinement`, slice it per ROI sample, and compute `variance = torch.clamp(bragg_scaled.detach() + sigma_slice**2, min=1e-12)` before forming the chi-squared numerator/denominator in Stage A/B/C `compute_loss*` helpers.
3. While updating `run_nanobrag_refinement`, add telemetry fields for `chi_squared_initial/final` (per stage) and have `_write_torch_outputs` persist both `chi_squared` and `masked_mse` into `/torch_diagnostics` along with existing loss traces.
4. Refactor `dbex.nanobrag_bridge.compute_masked_mse_loss` into a variance-weighted helper (e.g., accept `sigma_readout` and rename as needed); update `tests/dbex/test_gradients.py` fixtures to synthesize deterministic sigma tensors so DB-AT-010 continues to run with float64 tolerances.
5. Capture logs with `KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/gradcheck NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/pytest_db_at_010.log`.

## Pitfalls To Avoid
- Detach only the variance term (`pred.detach() + sigma^2`); never detach numerator or ROI tensors that influence gradients.
- Do not let sigma broadcast silently change dtype/device—ensure conversions happen once near the top of `run_nanobrag_refinement`.
- Guard the denominator with a tiny epsilon to avoid divide-by-zero when Bragg hits exactly 0 and sigma defaults to 0.
- Maintain Stage B’s deterministic ROI sampler so weighted loss comparisons remain apples-to-apples with Stage A traces (REFINE-008 gate still applies).
- Update `RefinementTelemetry` without breaking existing consumers in `_write_torch_outputs` (keep JSON serializable fields, include chi-squared but preserve masked-mse traces for legacy readers).
- Environment stays frozen: no package installs or CLI dependencies beyond the repo.
- Keep CLI help text explicit about sigma units so users don’t mix ADU vs photons; add warning when both CLI + metadata disagree.
- Make sure DB-AT-010 fixtures fall back gracefully (skip) if canonical assets absent; never catch-and-ignore gradcheck failures.
- Document any default sigma (e.g., zeros) in the plan if metadata unavailable so future loops know this still needs CLI support per specs.

## If Blocked
- If canonical refGeom assets are missing, run the selector with `--collect-only`, stash the log under the artifacts path, mark PHYSICS-LOSS-001 as blocked in docs/fix_plan.md with the missing asset list, and halt further code changes.
- If sigma metadata cannot be sourced (no CLI or detector auxiliary files), capture the attempted lookup + error in `plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/summary.md`, leave placeholders in code guarded behind feature flags, and mark the initiative blocked until data ownership is resolved.

## Findings Applied
- DIAGNOSTICS-001 — Torch diagnostics must emit standardized metrics; add `chi_squared` alongside `masked_mse` in `/torch_diagnostics`.
- REFINE-008 — Stage B loss gating and ROI sampling must match Stage A semantics, so weighted loss wiring cannot change the sampler or telemetry structure.

## Pointers
- docs/fix_plan.md:15 — PHYSICS-LOSS-001 entry (status, exit criteria, attempts).
- plans/nanobrag_integration_plan.md:142 — Phase 3 Loss/Staging requirements for variance-weighted chi-squared and per-reflection Stage B.
- docs/spec-db-core.md:53 — Variance model (detach denominator, sigma in photon units).
- docs/TESTING_GUIDE.md:70 — DB-AT-010 selector/env flags for gradcheck coverage.

## Next Up (optional)
1. ARCH-REFINE-FLOW-001 — codify Stage A/B/C into protocol objects once chi-squared loss is stable.
2. TOOLING-VIS-001 — update `dbex.vis` / ROI viewer once chi-squared telemetry is persisted.

## Mapped Tests Guardrail
- `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a` collects 1 test when assets exist; if collection drops to 0 after changes, stop, capture `--collect-only` output, and treat the fix as incomplete.
