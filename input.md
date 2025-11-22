# Ralph Input — 2025-11-22T110000Z

## Summary
Validate Phase C1 partial success via Phase 5 convergence testing (exit criteria #2-3).

## Mode
none (validation run + decision synthesis)

## Focus
TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity (Phase C1 validation + decision)

## Branch
integration

## Mapped tests
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 1,2,4,5` (tooling, exit-criterion #2-3)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Active, regression guard already passed in 2025-11-22T100021Z)

## Artifacts
`plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/`
- `stage_a_debug_phase5.json` (Phase 5 A_scale_only/D_full results)
- `zero_point_check.json` (Phase 1 zero-point chi-squared validation)
- `block_dof_results.json` (Phase 5 per-variant trajectories)
- `stage_a_debug.log`
- `decision.json` (synthesis of all phases → final recommendation)
- `commands.txt`

## Do Now

**Context:** Phase C1 (Branch G geometry fix) achieved **partial success**:
- ✅ All three B_ideal variants (dxtbx unitcell, recovered, mapping-aligned) now produce **identical** results
- ✅ Implementation correctly derives B_ideal from MOSFLM A* (verified by identical baseline missets)
- ✅ Regression guard (`test_stage_a_expansion`) PASSED
- ❌ Exit criterion #1 literal threshold unmet: `max_abs_diff = 4.022e-05` (40× above 1e-6)
- ✅ Exit criterion #1 alternative satisfied: "clearly identified non-rotational strain component with quantified magnitude"
  - Symmetric strain: 1.369e-3 (1000× larger than antisymmetric 1.37e-7)
  - Not fixable by B_ideal choice (all variants identical to 4 significant figures)
  - Impact quantified: 24.5% χ² gap between mapping and explicit parameterization at zero deltas

**Decision Point:** Per `implementation.md:30-35`, Exit Criterion #1 has **two paths**:
1. Pure-rotation with `max_abs_diff < 1e-6` (NOT achieved), **OR**
2. Clearly identified strain with quantified magnitude and **documented impact on gradients** (ACHIEVED)

The remaining question is **whether this 4e-5 gap blocks refinement convergence** (exit criteria #2-3). If Phase 5 validation shows stable/improving convergence despite the geometry gap, we can document the residual strain and **proceed**.

**Validation Plan:**
1. Run `stage_a_mapping_adam_debug.py --phases 1,2,4,5` with the **mapping-aligned baseline misset** from Phase C1
2. Capture Phase 1 zero-point chi-squared (expect ≈2.98e6 explicit vs ≈2.39e6 mapping, confirming 24.5% gap persists)
3. Capture Phase 5 A_scale_only and D_full trajectories
4. **Decision synthesis:**
   - If A_scale_only maintains CC ≥ 0.99 and stable χ² (≤0.5% drift) → **Accept documented residual, mark initiative done**
   - If D_full shows monotonic χ² improvement without large CC collapses → **Accept documented residual, mark initiative done**
   - If both fail (degrade CC or diverge) → **Pivot to Phase B3 (LR sensitivity sweep)** to test if convergence can be recovered with tuning
   - If LR sweep also fails → **Escalate to new initiative** (TORCH-SIMULATOR-PARITY-001 or alternative parameterization)

**Checklist:**

1. **Run Phase 5 validation:**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --phases 1,2,4,5 \
     --device cpu \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/
   ```
   - Capture all Phase 1-5 artifacts (zero_point_check.json, block_dof_results.json, etc.)
   - Expected: Phase 1 will show χ²_mapping ≈ 2.39e6, χ²_explicit_zero ≈ 2.98e6 (24.5% gap)
   - Critical metrics from Phase 5:
     - A_scale_only: median_cc_after, chi_squared_after (compare to before)
     - D_full: median_cc_after, chi_squared_after, trajectory monotonicity

2. **Synthesize decision:**
   - Review Phase 5 results and compare to exit criteria #2-3
   - Create `decision.json` capturing:
     ```json
     {
       "decision": "accept_residual" | "pivot_to_lr_sweep" | "escalate_to_new_initiative",
       "rationale": "<1-2 sentence explanation>",
       "exit_criterion_1_status": "alternative_path_satisfied",
       "exit_criterion_2_status": "pass" | "fail" | "conditional",
       "exit_criterion_3_status": "pass" | "fail" | "conditional",
       "residual_strain_magnitude": 1.369e-3,
       "max_abs_diff_a_star": 4.022e-05,
       "chi_squared_gap_percent": 24.5,
       "phase_5_a_scale_only": {
         "median_cc_before": <value>,
         "median_cc_after": <value>,
         "chi_squared_before": <value>,
         "chi_squared_after": <value>,
         "stable_convergence": true | false
       },
       "phase_5_d_full": {
         "median_cc_before": <value>,
         "median_cc_after": <value>,
         "chi_squared_before": <value>,
         "chi_squared_after": <value>,
         "monotonic_improvement": true | false
       },
       "recommended_next_action": "<specific action if not done>"
     }
     ```

3. **Update findings (conditional):**
   - If decision is "accept_residual" and exit criteria #2-3 pass:
     - Update `docs/findings.md` GEOMETRY-003 row with:
       - The mapping-aligned baseline misset uses `B_ideal_mapping = (A*_mapping)^{-T}` (implemented)
       - Residual symmetric strain 1.369e-3 persists across all B_ideal variants (documented)
       - 4e-5 A* parity gap does **not** block Stage-A refinement convergence per Phase 5 validation
       - Reference: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/decision.json`
   - If decision is "pivot_to_lr_sweep", do NOT update GEOMETRY-003 yet

4. **Update fix_plan (conditional):**
   - If decision is "accept_residual" and exit criteria #2-3 pass:
     - Mark TORCH-REFINE-002E as `done` in `docs/fix_plan.md`
     - Append final Attempts History entry with decision synthesis
   - If decision is "pivot_to_lr_sweep":
     - Keep TORCH-REFINE-002E as `in_progress`
     - Append Attempts History with Phase C1 validation outcome and next action (Phase B3)

## How-To Map

**Environment:**
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

**Phase 5 Validation Command:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 1,2,4,5 \
  --device cpu \
  --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/
```

**Expected Outputs:**
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/zero_point_check.json` (Phase 1)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/block_dof_results.json` (Phase 5)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/stage_a_debug.log`
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/commands.txt`

**Decision Synthesis:**
After Phase 5 completes, manually create `decision.json` per template in step 2 above.

## Pitfalls To Avoid

1. **Do not revert Phase C1 implementation:** The mapping-aligned B_ideal derivation is correct even though it didn't close the gap to 1e-6. Keep it.
2. **Do not adjust exit criteria without evidence:** Only relax threshold if Phase 5 shows stable convergence.
3. **Do not skip decision synthesis:** The `decision.json` artifact is **required** to close the loop.
4. **Device/dtype neutrality:** Phase 5 runs on CPU (`--device cpu`); no GPU-specific code needed.
5. **Protected Assets:** Do NOT modify `tests/fixtures/golden_data/` or Phase C1 implementation unless decision is "escalate".
6. **No normative math paraphrasing:** Reference `implementation.md:30-35` for exit criterion interpretation.
7. **Exit criteria precision:** Focus on **convergence behavior** (CC stability, χ² monotonicity), not literal A* parity.
8. **Regression discipline:** Stage-A expansion smoke already passed in 2025-11-22T100021Z; no need to re-run.
9. **Commit hygiene:** Commit the decision.json and any findings/fix_plan updates **only after synthesis is complete**.
10. **No environment changes:** Do not install packages or upgrade dependencies.

## If Blocked

1. **If `stage_a_mapping_adam_debug.py` fails to run:**
   - Capture the error log in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/error.log`
   - Check if the Phase C1 mapping-aligned baseline misset is properly wired into the debug driver
   - Return to supervisor with the failure signature and recommend revisiting Phase C1 integration

2. **If Phase 5 A_scale_only degrades CC below 0.99:**
   - Capture the exact trajectory in `block_dof_results.json`
   - Set `decision = "pivot_to_lr_sweep"` in `decision.json`
   - Document the recommended LR/step grid for Phase B3 (e.g., LR: [1e-5, 5e-5, 1e-4], steps: [1, 3, 10])
   - Return to supervisor with explicit next-action

3. **If Phase 5 D_full shows non-monotonic χ² or large CC collapses:**
   - Capture the trajectory showing the divergence
   - Set `decision = "conditional"` and note that D_full may need to be gated/disabled
   - Return to supervisor with recommendation to either accept A_scale_only-only convergence or pursue Phase B3

4. **If both A_scale_only and D_full fail convergence checks:**
   - Set `decision = "escalate_to_new_initiative"`
   - Document that the 4e-5 geometry gap **does** block refinement convergence
   - Recommend opening TORCH-SIMULATOR-PARITY-001 to investigate crystal tensor numerical precision or alternative parameterizations (quaternion, axis-angle)
   - Return to supervisor with the recommendation

5. **Log all blockers** in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/blocker.md` with:
   - Specific failure mode (Phase 5 variant + metric that failed)
   - Which exit criterion is unmet (#2 or #3)
   - Recommended next action from the decision tree above

## Findings Applied (Mandatory)

**Relevant Finding IDs from `docs/findings.md`:**

- **GEOMETRY-001** (detector mapping): Not directly relevant, maintained for hygiene.
- **GEOMETRY-002** (Euler inversion): Applies—baseline misset uses analytic XYZ Euler inversion.
- **GEOMETRY-003** (baseline misset): **CRITICAL**—Phase C1 extended this to use mapping-derived B_ideal; will update after decision synthesis.
- **GRADIENT-001** (tensor overrides): Applies—no .detach() or .cpu() in forward pass.
- **REFINE-004** (HKL interpolation): Not changed by Phase C1.
- **REFINE-005** (HKL halo): Tricubic interpolation enabled.
- **RUNTIME-001** (torch.compile + gradcheck): Applies—`NANOBRAGG_DISABLE_COMPILE=1` for all tests.
- **CONFORMANCE-001** (DB-AT selectors): Exit criteria reference DB-AT-024 mapping parity.
- **PHYSICS-LOSS-002** (sigma_floor): Variance-weighted loss active.
- **PHYSICS-LOSS-003** (chi-squared units): Unified chi-squared definition across stages.

**Adherence:**
- GEOMETRY-003: Phase C1 implementation preserved (mapping-aligned B_ideal derivation)
- GEOMETRY-002: XYZ Euler inversion for misset (unchanged)
- GRADIENT-001: No detach/cpu in forward pass (unchanged)
- RUNTIME-001: NANOBRAGG_DISABLE_COMPILE=1 for Phase 5 run

## Pointers

**Specs:**
- `docs/spec-db-workflow.md:39` — Stage A mapping zero-point invariant (normative)
- `docs/spec-db-core.md` — Geometry Mapping section
- `docs/spec-db-conformance.md` — DB-AT-024 mapping parity spec

**Implementation Plan:**
- `plans/active/TORCH-REFINE-002E/implementation.md:30-35` — Exit Criteria with OR clause
- `plans/active/TORCH-REFINE-002E/implementation.md:124-156` — Phase C decision branches

**Prior Phase Artifacts:**
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/blocker.md` — Phase C1 outcome
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/crystal_matrix_parity.json` — All three B_ideal variants identical
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json` — 24.5% χ² gap
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json` — Large non-zero gradients at zero

**Fix Plan:**
- `docs/fix_plan.md` — TORCH-REFINE-002E entry (will update after decision synthesis)

**Findings:**
- `docs/findings.md:7` — GEOMETRY-003 row (will update after decision synthesis if applicable)

## Next Up (optional)

**If decision is "accept_residual" (exit criteria #2-3 pass):**
1. Mark TORCH-REFINE-002E as `done` in `docs/fix_plan.md`
2. Update GEOMETRY-003 in `docs/findings.md` with residual strain documentation
3. Proceed to TOOLING-VIS-001 validation (all Stage-A visualizations with geometry fix)
4. Return control to supervisor for Tier 1 completion review

**If decision is "pivot_to_lr_sweep":**
1. Keep TORCH-REFINE-002E as `in_progress`
2. Supervisor will author Phase B3 input.md (LR sensitivity sweep)
3. Do NOT proceed to other initiatives until B3 completes

**If decision is "escalate_to_new_initiative":**
1. Keep TORCH-REFINE-002E as `blocked`
2. Supervisor will open TORCH-SIMULATOR-PARITY-001 or alternative
3. Return control to supervisor with blocker documentation

## Doc Sync Plan

**Not required** — No new tests added; only validation run and decision synthesis. Supervisor will handle doc updates after decision is finalized.

## Normative Math/Physics

See `implementation.md:30-35` for exit criterion interpretation:
> Exit Criterion #1: either achieve `max_abs_diff < 1e-6` **OR** "a clearly identified non-rotational strain component with quantified magnitude and documented impact on gradients."

Phase C1 achieved the **alternative path** (strain identified, quantified, impact measured). Now we validate whether this residual blocks convergence (exit criteria #2-3).
