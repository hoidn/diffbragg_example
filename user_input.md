# MANUAL OVERRIDE: Specification & Roadmap Realignment

**Directives:**
1. We have changed the Spec out-of-band. The current agent state is obsolete.
2. You must align the repository files (`plans/nanobrag_integration_plan.md` and `docs/fix_plan.md`) with the new scientific direction (Variance-Weighted Loss, Per-Reflection Stage B).
3. You must reset `input.md` to force the next loop to start the new critical initiative (`PHYSICS-LOSS-001`).

**Action 1: Patch `plans/nanobrag_integration_plan.md`**
Replace the "Loss" and "Staging" sections with this exact text:
```markdown
6) Loss (Variance-Weighted / Chi-Squared)
   - Loss SHALL be `Sum( (Bragg - target)^2 / (Bragg.detach() + sigma_rdout^2) )` over trusted pixels.
   - This implements an IRLS (Iteratively Reweighted Least Squares) objective. `Bragg.detach()` prevents the optimizer from minimizing the variance term to cheat the loss.
   - `sigma_rdout` must be in photon units.
7) Staging
   - Stage A (Geometry & Scale): Simulator SHOULD use tricubic interpolation (`interpolate=True`) if halo is available to ensure smooth gradients for orientation; nearest-neighbor is a permitted fallback.
   - Stage B (Structure Factors): Refine **per-reflection multipliers** (Full Fhkl).
     • **ASU Mapping:** The bridge MUST generate an `asu_mapping_tensor` mapping dense grid indices to unique ASU indices (symmetry constrained).
     • **Gather/Scatter:** The engine uses `torch.gather` to map unique params to the grid.
     • Requires differentiable HKL interpolation (tricubic) with ±1 halo.
```
Action 2: Update docs/fix_plan.md
Insert these new initiatives at the top of the "Active Initiatives" list:
```markdown
### [PHYSICS-LOSS-001] Implement variance-weighted loss function
- Depends on: docs/spec-db-core.md (Variance Model)
- Status: pending
- Priority: Critical (Scientific Validity)
- Owner/Date: Unassigned
- Exit Criteria:
  1. `RefinementInputs` carries `sigma_rdout` (photon units) derived from detector metadata or CLI args.
  2. `run_nanobrag_refinement` minimizes `Sum((pred - obs)^2 / (pred.detach() + sigma^2))` instead of MSE.
  3. DB-AT-010 gradchecks pass with the new loss function.
  4. Telemetry records `chi_squared` (weighted loss) alongside `masked_mse`.
- Working Plan: plans/active/PHYSICS-LOSS-001/implementation.md

### [ARCH-REFINE-FLOW-001] Refactor to Protocol-based Refinement Engine
- Depends on: PHYSICS-LOSS-001
- Status: pending
- Priority: High (Architectural Maturity)
- Owner/Date: Unassigned
- Exit Criteria:
  1. `RefinementEngine` class exists and accepts a list of `RefinementStage` objects.
  2. `run_nanobrag_refinement` is refactored to construct a default protocol (A->B->C) and execute it via the Engine.
  3. Stages are defined as data (dataclasses), not procedural code blocks.
  4. Existing smoke tests pass without modification to external behavior.

### [TOOLING-VIS-001] Standardize visual diagnostics library
- Depends on: PHYSICS-LOSS-001
- Status: pending
- Priority: Medium
- Owner/Date: Unassigned
- Exit Criteria:
  1. `dbex.vis` module created implementing `spec-db-vis.md` standards (Z-scores, triptychs).
  2. `dbex/look.py` refactored to use `dbex.vis` for rendering.
  3. CLI automatically generates a standard report (PNG/PDF) at the end of refinement.
```
Crucial: Update the existing item [TORCH-REFINE-005] to depend on ARCH-REFINE-FLOW-001.
