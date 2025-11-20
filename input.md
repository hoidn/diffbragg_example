# Input

- Summary: Kick off PHYSICS-LOSS-001 by wiring sigma_rdout through the bridge + CLI and switching Stage A to the variance-weighted chi-squared loss with telemetry updates.
- Mode: TDD
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -k DB_AT_010
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T000000Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: dbex/nanobrag_bridge.py::prepare_refinement_inputs (thread `sigma_rdout` from detector metadata/CLI into RefinementInputs), dbex/refine_one.py::main (expose `--sigma-rdout` CLI flag and plumb it), and dbex/nanobrag_refinement.py::run_nanobrag_refinement (replace masked MSE with `Sum((pred - obs)^2 / (pred.detach() + sigma_rdout^2))`, persist `chi_squared` telemetry, and guard against zero denominators).
- Test: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -k DB_AT_010
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T000000Z/

## How-To Map
1. Read detector metadata via `DataLoad`/experiment files; normalize sigma to photon units and default to CLI override when provided; document fallback path in plans/active/PHYSICS-LOSS-001/implementation.md.
2. Update `RefinementInputs` dataclass plus serialization so sigma is mandatory (shape `[panel, slow, fast]` or broadcastable scalar); add unit assertions inside `prepare_refinement_inputs`.
3. Modify `run_nanobrag_refinement` Stage A closure to compute `chi_squared = torch.sum((bragg - target) ** 2 / (bragg.detach() + sigma_rdout**2 + eps))` on the trusted mask, keep `masked_mse` for telemetry during migration, and log both.
4. Extend DB-AT-010 gradcheck selector to assert gradients agree with numerical diff when sigma varies per panel; capture fail logs if gradients explode.
5. Update docs/spec-db-core.md references inside `plans/nanobrag_integration_plan.md` or telemetry docs if expectations move.

## Pitfalls To Avoid
- Do not detach tensors that participate in gradients (only the denominator receives `.detach()` per spec).
- Guard sigma against zeros/negatives; failing to clamp or validate units will destabilize LBFGS.
- Telemetry must include `chi_squared` for every stage transition so downstream dashboards stay coherent.
- Respect Environment Freeze—modify only local source; record issues in docs/fix_plan.md if dependencies are missing.

## If Blocked
- If detector metadata lacks sigma, log the missing field, set placeholder zeros, and mark PHYSICS-LOSS-001 as blocked with rationale in docs/fix_plan.md before proceeding.
- If DB-AT-010 selector is absent or broken, capture pytest --collect-only output and document the gap in plans/active/PHYSICS-LOSS-001/reports/2025-11-21T000000Z/summary.md.

## Findings Applied
- Re-aligning with PHYSICS-LOSS-001 spec update (variance-weighted chi-squared objective) per user_input.md override.

## Pointers
- plans/nanobrag_integration_plan.md: Phase 3 Loss/Staging definitions (Variance-Weighted / Stage B per-reflection multipliers).
- docs/spec-db-core.md §Variance Model: normative sigma_rdout guidance.
- docs/fix_plan.md: new initiatives + dependencies for PHYSICS-LOSS-001 and ARCH-REFINE-FLOW-001.

## Next Up (optional)
1. After chi-squared loss lands, schedule ARCH-REFINE-FLOW-001 to introduce the protocol-based refinement engine.
2. Update telemetry/visualization stack (TOOLING-VIS-001) once weighted losses are recorded in HDF5.

## Mapped Tests Guardrail
- `pytest -k DB_AT_010` must collect and fail until chi-squared implementation is complete; capture logs + gradcheck deltas in the artifacts directory.
