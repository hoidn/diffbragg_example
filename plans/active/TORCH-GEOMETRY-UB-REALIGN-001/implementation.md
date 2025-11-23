# Implementation Plan: TORCH-GEOMETRY-UB-REALIGN-001

## Initiative
- ID: TORCH-GEOMETRY-UB-REALIGN-001
- Title: Stage A UB Parameterization Realignment
- Owner: Unassigned
- Spec Owner: docs/spec-db-core.md, docs/spec-db-workflow.md, docs/spec-db-runtime.md
- Status: pending

## Goals
- Design and implement a Stage-A geometry parameterization that treats the dxtbx/DIALS crystal state (`U₀ = crystal.get_U()`, `B₀ = crystal.get_B()`, `A*_mapping = U₀ @ B₀`) as authoritative and conforms to the Baseline Crystal State and Parameterization rules in `spec-db-core.md`.
- Parameterize orientation and cell as *increments* (ΔR, Δcell) around the baseline state, so that `U(params) = ΔR(params) @ U₀`, `B(params)` is derived from perturbed cell parameters via a Busing–Levy–compatible metric tensor, and `A*(params) = U(params) @ B(params)` is the only way the simulator geometry is constructed in Stage A.
- Ensure the new parameterization passes a strict UB/A* round-trip check at the mapping zero point (DB-AT-026) and preserves DB-AT-024 mapping parity.

## Phases Overview
- Phase A — Design & Spec Alignment: Translate the normative UB/A* rules into a concrete Stage-A parameterization (Euler, axis-angle, or quaternion for ΔR; logs/angles for Δcell), with explicit zero-point invariants and UB/A* round-trip criteria.
- Phase B — Implementation & Wiring: Implement the new incremental parameterization in the nanobrag_torch Stage-A path (and associated tooling), replacing any reliance on A* decompositions while keeping the cell+misset default path stable.
- Phase C — Validation & Rollout: Add/enable DB-AT-026, re-run DB-AT-024 and the Stage-A smoke tests, and document the migration from the deprecated quaternion U-matrix path to the new incremental UB parameterization.

## Exit Criteria
1. A concrete Stage-A parameterization is defined that:
   - uses `U₀,B₀` from dxtbx as the baseline state,
   - expresses orientation as a small rotation `ΔR(params)` such that `U(params) = ΔR(params) @ U₀`, and
   - expresses cell as perturbations around the baseline that produce `B(params)` via a Busing–Levy–compatible metric tensor map.
2. The implementation of this parameterization in the nanobrag_torch Stage-A path:
   - constructs `A*(params)` only as `U(params) @ B(params)`,
   - does not refactor `A*` back into `U,B` in any production refinement code paths, and
   - preserves the existing cell+misset default behavior where required.
3. A UB/A* round-trip test (DB-AT-026) is implemented and passes:
   - at `params=0`, `U(0)=U₀`, `B(0)=B₀`, and `A*(0)=U₀ @ B₀ = A*_mapping` within documented tolerances.
4. DB-AT-024 mapping consistency continues to pass under the new parameterization, and Stage-A smoke tests (`tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`) remain green.
5. `docs/findings.md` and `docs/fix_plan.md` are updated to:
   - record the deprecation or narrowing of the previous quaternion U-matrix parameterization (if deemed non-viable by TORCH-GEOMETRY-CONVERGENCE-001), and
   - describe usage conventions and constraints for the new incremental UB parameterization.

## Notes
- This initiative is expected to consume the verdict and requirements produced by TORCH-GEOMETRY-CONVERGENCE-001; it SHOULD NOT proceed to implementation until CONVERGENCE-001 has produced an evidence-backed decision about the viability of the current quaternion U-matrix path.
- Quaternion-based increments (ΔR on top of U₀) remain a candidate representation, but only if they can be made to pass the UB/A* round-trip test and the new Stage-A invariants.

