# Ralph Input — 2025-11-22T120000Z

## Summary
Complete Phase 5 with reduced scope (A_scale_only + D_full only, 5 steps) to determine convergence viability.

## Mode
none (final validation → decision synthesis)

## Focus
TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity (Phase C1 decisive validation)

## Branch
integration

## Mapped tests
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 5 --adam-steps 5 --dof-variants A_scale_only,D_full` (tooling, exit-criterion #2-3)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Active, regression guard - skip if Phase 5 completes)

## Artifacts
`plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/`
- `block_dof_results_reduced.json` (Phase 5 A_scale_only/D_full only, 5 Adam steps)
- `stage_a_debug.log`
- `decision.json` (synthesis of all phases → final recommendation)
- `commands.txt`

## Do Now

**Context:** Phase C1 validation (2025-11-22T110000Z) was incomplete—Phase 5 ran >12 minutes building HKL grids without producing `block_dof_results.json`. However, **Phase 1-4 artifacts provide decisive evidence**:

- ✅ Exit criterion #1 **alternative path satisfied**: Symmetric strain 1.369e-3 identified, impact quantified (24.5% χ² gap, orientation_vec gradient magnitude ≈2.88e8)
- ❌ Exit criteria #2-3 **unmet**: Phase 4 shows **convergence degradation** (χ²: 1.13M → 2.80M after 1 Adam step, all DoFs walk away from zero)
- ❓ **Missing decisive data**: Phase 5 block-DoF trajectories (would show if `A_scale_only` subset maintains stability despite geometry gap)

**Escalation Trigger:** Per **repeat-failure escalation** rule, this is the **final validation attempt** for TORCH-REFINE-002E before escalation. If Phase 5 reduced-scope run shows degradation for *both* A_scale_only and D_full, mark initiative as `blocked` and escalate to new implementation initiative (TORCH-GEOMETRY-PARITY-002 or alternative parameterization).

**Validation Plan (Reduced Scope):**

Run Phase 5 with **minimal scope** to avoid HKL grid rebuilding timeout:
1. **Skip Phases 1-4** (already have artifacts from 2025-11-22T110000Z)
2. **Run Phase 5 ONLY** with:
   - DoF variants: `A_scale_only` and `D_full` (skip B/C)
   - Adam steps: **5** (reduced from default 10)
   - This should cut HKL grid builds from ~28+ to ~12-14 (2 variants × 5 steps + validation)
3. **Timeout**: 20 minutes (double the previous run's observed duration)
4. **Capture**: `block_dof_results_reduced.json` with A_scale_only/D_full trajectories

**Decision Synthesis (Required):**

After Phase 5 completes (or times out), create `decision.json` per this logic:

```json
{
  "decision": "<accept_residual|escalate_to_new_initiative>",
  "rationale": "<1-2 sentence explanation>",
  "exit_criterion_1_status": "alternative_path_satisfied",
  "exit_criterion_2_status": "<pass|fail>",
  "exit_criterion_3_status": "<pass|fail>",
  "phase_5_completion": "<completed|timeout>",
  "residual_strain_magnitude": 1.369e-3,
  "max_abs_diff_a_star": 4.022e-05,
  "chi_squared_gap_percent": 24.5,
  "phase_4_single_step": {
    "chi_squared_before": 1133420.75,
    "chi_squared_after": 2799388.5,
    "degradation_factor": 2.47
  },
  "phase_5_a_scale_only": {
    "median_cc_final": "<value or null>",
    "chi_squared_final": "<value or null>",
    "stable_convergence": "<true|false|null>"
  },
  "phase_5_d_full": {
    "median_cc_final": "<value or null>",
    "chi_squared_final": "<value or null>",
    "monotonic_improvement": "<true|false|null>"
  },
  "recommended_next_action": "<specific action>"
}
```

**Decision Tree:**

1. **If Phase 5 completes and A_scale_only maintains CC ≥ 0.99 + stable χ² (≤0.5% drift):**
   - `decision = "accept_residual"`
   - `exit_criterion_2_status = "pass"`
   - Update `docs/findings.md` GEOMETRY-003 with residual strain documentation
   - Mark TORCH-REFINE-002E as `done`

2. **If Phase 5 completes but A_scale_only degrades (CC < 0.99 or large χ² drift):**
   - `decision = "escalate_to_new_initiative"`
   - `exit_criterion_2_status = "fail"`
   - Do NOT update GEOMETRY-003
   - Mark TORCH-REFINE-002E as `blocked`
   - Recommend opening TORCH-GEOMETRY-PARITY-002 (U-matrix direct override) or alternative

3. **If Phase 5 times out again (>20 min):**
   - `decision = "escalate_to_new_initiative"`
   - `exit_criterion_2_status = "inconclusive"`
   - Recommend either (a) opening PERF-PHASE5-HKL-001 to fix Phase 5 performance, or (b) accepting Phase 4 evidence as sufficient to escalate geometry parity initiative

**Checklist:**

1. **Run Phase 5 reduced scope:**
   ```bash
   timeout 1200 \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --phases 5 \
     --device cpu \
     --adam-steps 5 \
     --dof-variants A_scale_only,D_full \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/
   ```
   - Expected outputs: `block_dof_results_reduced.json`, `stage_a_debug.log`
   - If timeout: capture partial log and proceed to decision synthesis

2. **Synthesize decision:**
   - Review Phase 5 results (or timeout signature)
   - Create `decision.json` per template above
   - **Critical**: If Phase 5 shows degradation for *both* variants, this is a **blocker** requiring escalation

3. **Update findings (conditional):**
   - **Only if** `decision = "accept_residual"` and exit criteria #2 pass:
     - Update `docs/findings.md` GEOMETRY-003 row with residual strain documentation
     - Reference: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/decision.json`
   - **Otherwise**: Do NOT update GEOMETRY-003

4. **Update fix_plan (required):**
   - Append Attempts History entry with Phase C1 validation outcome and decision
   - If `decision = "accept_residual"`: mark TORCH-REFINE-002E as `done`
   - If `decision = "escalate_to_new_initiative"`: mark as `blocked` with rationale and recommended next initiative

## How-To Map

**Environment:**
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

**Phase 5 Reduced-Scope Command:**
```bash
timeout 1200 \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 \
  --device cpu \
  --adam-steps 5 \
  --dof-variants A_scale_only,D_full \
  --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/
```

**Expected Outputs:**
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/block_dof_results_reduced.json`
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/stage_a_debug.log`
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/commands.txt`

**Decision Synthesis (manual):**
After Phase 5 completes or times out, create `decision.json` per template in Do Now step 2.

## Pitfalls To Avoid

1. **Do not revert Phase C1 implementation:** The mapping-aligned B_ideal derivation is correct even though it didn't close the gap.
2. **Do not relax exit criteria without Phase 5 evidence:** Only accept residual if Phase 5 shows A_scale_only stability.
3. **Timeout handling:** If Phase 5 times out again, treat it as evidence for escalation (Phase 4 shows degradation, Phase 5 can't complete).
4. **Device/dtype neutrality:** Phase 5 runs on CPU (`--device cpu`); no GPU-specific code needed.
5. **Protected Assets:** Do NOT modify `tests/fixtures/golden_data/` or Phase C1 implementation.
6. **No normative math paraphrasing:** Reference `implementation.md:30-35` for exit criterion interpretation.
7. **Exit criteria precision:** Focus on **convergence behavior** (CC stability, χ² monotonicity), not literal A* parity.
8. **Escalation discipline:** If both A_scale_only and D_full fail, this is a **hard blocker** requiring new initiative.
9. **Commit hygiene:** Commit the decision.json and any findings/fix_plan updates **only after synthesis is complete**.
10. **No environment changes:** Do not install packages or upgrade dependencies.

## If Blocked

1. **If Phase 5 times out again (>20 min):**
   - Capture the timeout signature in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/timeout.log`
   - Set `decision = "escalate_to_new_initiative"` with `phase_5_completion = "timeout"`
   - Document that Phase 4 evidence (2.47× degradation) is sufficient to escalate
   - Recommend either PERF-PHASE5-HKL-001 (Phase 5 performance fix) or accept Phase 4 as decisive

2. **If Phase 5 completes but both A_scale_only AND D_full degrade:**
   - Set `decision = "escalate_to_new_initiative"`
   - `exit_criterion_2_status = "fail"`, `exit_criterion_3_status = "fail"`
   - Document that the 4e-5 geometry gap **blocks all refinement DoF convergence**
   - Recommend opening TORCH-GEOMETRY-PARITY-002 to implement U-matrix direct override (bypass cell+misset parameterization)

3. **If Phase 5 shows A_scale_only stable but D_full degrades:**
   - Set `decision = "accept_residual"` with `exit_criterion_3_status = "conditional"`
   - Document that full-DoF geometry refinement is blocked but scale-only convergence works
   - Update GEOMETRY-003 with this constraint
   - Mark TORCH-REFINE-002E as `done` with caveat

4. **Log all blockers** in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/blocker.md` with:
   - Specific failure mode (Phase 5 timeout or degradation signature)
   - Which exit criterion is unmet (#2 or #3)
   - Recommended next action from the decision tree above

## Findings Applied (Mandatory)

**Relevant Finding IDs from `docs/findings.md`:**

- **GEOMETRY-001** (detector mapping): Not directly relevant, maintained for hygiene.
- **GEOMETRY-002** (Euler inversion): Applies—baseline misset uses analytic XYZ Euler inversion.
- **GEOMETRY-003** (baseline misset): **CRITICAL**—Phase C1 extended this to use mapping-derived B_ideal; will update after decision synthesis if `accept_residual`.
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
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/blocker.md` — Phase 5 incomplete
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/single_step_adam.json` — Phase 4 shows 2.47× degradation
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json` — 24.5% χ² gap
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json` — Large non-zero gradients at zero
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/crystal_matrix_parity.json` — All three B_ideal variants identical

**Fix Plan:**
- `docs/fix_plan.md` — TORCH-REFINE-002E entry (will update after decision synthesis)

**Findings:**
- `docs/findings.md:7` — GEOMETRY-003 row (will update after decision synthesis if applicable)

## Next Up (optional)

**If decision is "accept_residual" (A_scale_only stable):**
1. Mark TORCH-REFINE-002E as `done` in `docs/fix_plan.md`
2. Update GEOMETRY-003 in `docs/findings.md` with residual strain documentation + convergence constraint
3. Proceed to next Tier 1 item per Roadmap
4. Return control to supervisor for focus selection

**If decision is "escalate_to_new_initiative" (both variants degrade or timeout):**
1. Mark TORCH-REFINE-002E as `blocked` in `docs/fix_plan.md`
2. Supervisor will open TORCH-GEOMETRY-PARITY-002 (U-matrix direct override) or alternative
3. Return control to supervisor with blocker documentation and recommended initiative spec

## Doc Sync Plan

**Not required** — No new tests added; only validation run and decision synthesis. Supervisor will handle doc updates after decision is finalized.

## Normative Math/Physics

See `implementation.md:30-35` for exit criterion interpretation:
> Exit Criterion #1: either achieve `max_abs_diff < 1e-6` **OR** "a clearly identified non-rotational strain component with quantified magnitude and documented impact on gradients."

Phase C1 achieved the **alternative path** (strain identified: 1.369e-3, impact quantified: 24.5% χ² gap, orientation_vec gradient magnitude ≈2.88e8). Phase 5 determines whether this residual blocks convergence (exit criteria #2-3).
