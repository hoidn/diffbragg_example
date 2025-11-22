# Ralph Input — 2025-11-22T100021Z

## Summary
Implement Phase C1 Branch G geometry fix to align Stage-A baseline with mapping effective cell.

## Mode
none (code changes + parity validation)

## Focus
TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity (Phase C1: Branch G)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Active, regression guard)
- `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py` (tooling, exit-criterion #1)
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --phases 1,2,4,5` (tooling, exit-criterion #2-3)

## Artifacts
`plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/`
- `crystal_matrix_parity.json` (must show `max_abs_diff < 1e-6`)
- `crystal_matrix_parity.log`
- `pytest_stage_a_regression.log`
- `stage_a_debug_phase5.json` (A_scale_only/D_full results)
- `stage_a_debug.log`
- `commands.txt`

## Do Now

**Context:** Phase A/B evidence conclusively proves the geometry encoding gap:
- Phase A0: symmetric strain dominates (`log_u_symmetric_norm ≈ 1.4e-3`, antisymmetric ≈ 1.4e-7)
- Phase A2: cell recovery from MOSFLM A* matches dxtbx cell, strain persists regardless of B_ideal source
- Phase B1: gradients at "zero" are massive (orientation_vec magnitude ≈ 2.88e8), proving zero deltas ≠ mapping geometry
- Phase A3: forward models differ by 24.5% chi-squared (χ²_mapping=2.394e6 vs χ²_stage_a_zero=2.980e6), confirming this is a **parameterization artifact**, not a simulator bug

**Root Cause:** The GEOMETRY-003 baseline misset (`dbex/nanobrag_bridge.py:723,752`) derives U from `A* · B_ideal^{-1}` where B_ideal is constructed from the **dxtbx unit cell**, but the mapping MOSFLM A* injection path uses an **effective cell** that differs slightly (1.4e-3 strain). When Stage-A explicit parameterization sets all deltas to zero, it produces a physically different orientation than mapping, causing the chi-squared penalty.

**Solution (Branch G):** Adjust the Stage-A baseline geometry construction so the explicit cell+misset path uses the **same effective cell as the mapping path**. The minimal fix:
1. Extract the effective B_ideal from the mapping MOSFLM A* matrix itself (via cctbx or direct reciprocal metric)
2. Use this mapping-derived B_ideal (not the dxtbx unit cell B_ideal) when computing `baseline_misset_deg` for Stage-A configurations
3. This ensures `U = A*_mapping · B_ideal_mapping^{-1}` is a pure rotation (no strain), closing the parity gap to <1e-6

**Checklist (C1: minimal geometry fix):**
1. **Implement:** Add `derive_b_ideal_from_mosflm_a_star(a_star: np.ndarray) -> np.ndarray` helper in `dbex/nanobrag_bridge.py` that:
   - Accepts the 3×3 MOSFLM A* matrix from dxtbx crystal
   - Computes the effective real-space basis `B = (A*)^{-T}` (inverse transpose)
   - Returns the 3×3 reciprocal basis B_ideal = B^{-T} suitable for nanobrag_torch
   - Document: this is the **mapping-aligned B_ideal** that Stage-A explicit path must use to reproduce mapping zero-point

2. **Implement:** Extend `derive_robust_misset` (or create new variant `derive_mapping_aligned_misset`) to:
   - Accept optional `use_mapping_b_ideal: bool = False` parameter
   - When True: call `derive_b_ideal_from_mosflm_a_star(a_star)` to get mapping B_ideal, then compute `U = A* · B_mapping^{-1}`
   - Project U to proper rotation via polar decomposition, invert to XYZ Euler angles
   - Return `baseline_misset_deg` that encodes the mapping orientation **around the mapping-effective cell**

3. **Implement:** Update `create_crystal_config` (or Stage-A crystal builder) in `dbex/nanobrag_bridge.py` to:
   - When `crystal_overrides` are used AND mapping alignment is requested (e.g., new flag `align_to_mapping_cell: bool`):
     - Derive mapping-aligned baseline misset via `derive_robust_misset(..., use_mapping_b_ideal=True)`
     - Construct `CrystalConfig` with the mapping-derived baseline misset
   - Preserve existing behavior (dxtbx unit-cell B_ideal) when flag is False or mapping alignment is not requested

4. **Validate:** Re-run parity probe:
   ```bash
   python plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py \
     --device cpu \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/
   ```
   - Expected: `max_abs_diff < 1e-6`, `log_u_symmetric_norm < 1e-6`, confirming A* parity achieved
   - Capture `crystal_matrix_parity.json` and `crystal_matrix_parity.log`

5. **Validate:** Re-run Stage-A mapping Adam debug Phase 5:
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --phases 1,2,4,5 \
     --device cpu \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/
   ```
   - Expected (exit criterion #2): A_scale_only maintains median ROI CC ≥ 0.99 and stable χ² after 10 steps
   - Expected (exit criterion #3): D_full shows monotonic χ² improvement, no large CC collapses
   - Capture `stage_a_debug_phase5.json`, `zero_point_check.json`, `block_dof_results.json`

6. **Regression guard:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
   ```
   - Capture `pytest_stage_a_regression.log`
   - Must PASS with no new failures

7. **Update GEOMETRY-003:** If the fix succeeds (exit criteria #1-3 met), update `docs/findings.md` row GEOMETRY-003 to reflect:
   - The mapping-aligned baseline misset derivation uses `B_ideal_mapping = (A*_mapping)^{-T}`
   - This closes the 1.4e-3 symmetric strain gap and achieves <1e-6 A* parity
   - Reference: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/`

## How-To Map

**Environment:**
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
```

**Phase C1 Implementation Steps:**

Step 1: **Add mapping B_ideal helper** (`dbex/nanobrag_bridge.py`)
```python
def derive_b_ideal_from_mosflm_a_star(a_star: np.ndarray) -> np.ndarray:
    """
    Derive the effective reciprocal basis B_ideal from mapping MOSFLM A* matrix.

    Args:
        a_star: 3×3 MOSFLM A* matrix from dxtbx crystal.get_A() (reshaped)

    Returns:
        3×3 reciprocal basis B_ideal = (A*)^{-T} suitable for nanobrag_torch

    Notes:
        This is the **mapping-aligned B_ideal** that Stage-A must use to reproduce
        the mapping zero-point geometry without symmetric strain artifacts.
    """
    # B_real = (A*)^{-T}
    b_real = np.linalg.inv(a_star).T
    # B_ideal (reciprocal) = B_real^{-T}
    b_ideal = np.linalg.inv(b_real).T
    return b_ideal
```

Step 2: **Extend derive_robust_misset** (or create variant)
Add parameter `use_mapping_b_ideal: bool = False` to `derive_robust_misset`. When True:
- Call `derive_b_ideal_from_mosflm_a_star(a_star)` to get mapping-aligned B_ideal
- Compute `U = A* @ np.linalg.inv(b_ideal_mapping)`
- Rest of the logic (polar decomposition, XYZ Euler inversion) remains the same

Step 3: **Wire into create_crystal_config**
When constructing Stage-A crystal configs with `crystal_overrides`, check if mapping alignment is requested:
- If yes: derive baseline misset with `use_mapping_b_ideal=True`
- If no: preserve existing GEOMETRY-003 path (dxtbx unit-cell B_ideal)

**Note:** You may need to add a configuration flag (e.g., `align_to_mapping_cell: bool`) to `RefinementConfig` or pass it explicitly to the crystal builder. For now, you can hardcode `use_mapping_b_ideal=True` in the Stage-A mapping paths (`build_mapping_stage_a_context`, `stage_a_mapping_adam_debug.py`) and test the impact.

Step 4-7: **Validation** (run commands above, capture artifacts)

## Pitfalls To Avoid

1. **Device/dtype neutrality:** All numpy operations (inverse, transpose) are CPU-only; convert torch tensors to numpy before calling the helper, then back to torch if needed.
2. **Protected Assets:** Do NOT modify `tests/fixtures/golden_data/` or `sp.proc/` fixtures. The geometry fix only touches bridge code.
3. **Vectorization:** The helper operates on single 3×3 matrices (per-crystal); no batching required.
4. **No environment changes:** Do not install packages or upgrade dependencies. If imports fail, record in `docs/fix_plan.md`.
5. **No normative math paraphrasing:** Reference `docs/spec-db-workflow.md §Stage A — mapping zero-point invariant` directly; do not rewrite the math.
6. **Exit criteria precision:** `max_abs_diff < 1e-6` is a hard gate; if you only achieve 1e-5, the fix is incomplete—document and return for supervisor review.
7. **Mapping alignment scope:** This fix applies to **mapping-aligned Stage-A runs only** (DB-AT-024, TOOLING-VIS-001 Phase 5). General refinement workflows that don't claim mapping parity are unaffected.
8. **Regression discipline:** Stage-A expansion smoke must PASS. If it fails, diagnose before proceeding to Phase 5 validation.
9. **Gradient hygiene:** The geometry fix is **initialization-only**—no changes to the forward/backward pass or loss functions. All torch.compile and gradcheck guardrails remain in effect.
10. **Commit hygiene:** If tests pass and exit criteria are met, commit the implementation with a message linking to this loop's artifacts. Otherwise, commit evidence artifacts and report blockers.

## If Blocked

1. **If parity probe still shows max_abs_diff > 1e-6 after the fix:**
   - Capture the new `crystal_matrix_parity.json` showing the residual gap
   - Check whether `log_u_symmetric_norm` dropped significantly (e.g., from 1.4e-3 to <1e-4)
   - Document partial progress in Attempts History and return to supervisor
   - **Do not** proceed to Phase 5 validation if exit criterion #1 is unmet

2. **If Stage-A mapping Phase 5 A_scale_only still degrades CC:**
   - Capture `block_dof_results.json` showing the A_scale_only trajectory
   - Compare the new zero-point chi-squared (from Phase 1 `zero_point_check.json`) to the old 2.98e6
   - If zero-point chi-squared is now ≈2.394e6 (matching mapping), but CC still degrades, pivot to Phase B3 (LR sensitivity sweep)
   - Document in Attempts History with explicit next-actions recommendation

3. **If regression guard fails:**
   - Capture `pytest_stage_a_regression.log` showing the failure
   - Isolate whether the failure is geometry-related (e.g., A* mismatch) or unrelated (e.g., flaky test)
   - If geometry-related, revert the changes and document why the fix broke the smoke
   - Return to supervisor with the failure signature

4. **Log all blockers** in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/blocker.md` with:
   - Specific error message or metric that failed
   - Which exit criterion is unmet
   - Hypothesis for why the fix didn't work
   - Recommended next action (e.g., "try alternative B_ideal derivation", "escalate to TORCH-SIMULATOR-PARITY-001")

## Findings Applied (Mandatory)

**Relevant Finding IDs from `docs/findings.md`:**

- **GEOMETRY-001** (detector mapping): Not directly relevant (detector paths unchanged), but maintained for hygiene.
- **GEOMETRY-002** (Euler inversion): Applies—baseline misset still uses analytic XYZ Euler inversion from U matrix.
- **GEOMETRY-003** (baseline misset): **CRITICAL**—this fix extends GEOMETRY-003 to use mapping-derived B_ideal instead of dxtbx unit-cell B_ideal.
- **GRADIENT-001** (tensor overrides): Applies—ensure no .detach() or .cpu() in the forward pass after this change.
- **REFINE-004** (HKL interpolation): Not changed by this fix, but remains in effect for Stage A.
- **REFINE-005** (HKL halo): Resolved; tricubic interpolation is enabled per spec.
- **RUNTIME-001** (torch.compile + gradcheck): Applies—`NANOBRAGG_DISABLE_COMPILE=1` for all tests.
- **CONFORMANCE-001** (DB-AT selectors): Exit criteria reference DB-AT-024 mapping parity.
- **PHYSICS-LOSS-002** (sigma_floor): Not directly relevant, but variance-weighted loss remains active.
- **PHYSICS-LOSS-003** (chi-squared units): Applies—Phase 5 validation will use the unified chi-squared definition.

**Adherence:**
- GEOMETRY-003 extended per Branch G decision (mapping-aligned B_ideal derivation)
- GEOMETRY-002 preserved (XYZ Euler inversion for misset)
- GRADIENT-001 enforced (no detach/cpu in forward pass)
- RUNTIME-001 enforced (NANOBRAGG_DISABLE_COMPILE=1 for all pytest/probe runs)

## Pointers

**Specs:**
- `docs/spec-db-workflow.md:39` — Stage A mapping zero-point invariant (normative requirement)
- `docs/spec-db-core.md` — Geometry Mapping section
- `docs/spec-db-conformance.md` — DB-AT-024 mapping parity spec

**Architecture:**
- `docs/config_crosswalk.md` — Crystal mapping section (A* → CrystalConfig)
- `docs/architecture.md` — ADRs and data flow

**Implementation:**
- `dbex/nanobrag_bridge.py:723` — `compute_baseline_misset_deg` (current GEOMETRY-003 path)
- `dbex/nanobrag_bridge.py:752` — `derive_robust_misset` (main helper to extend)
- `dbex/nanobrag_bridge.py:623` — `recover_cell_from_a_star` (Phase A2 helper, reference for cctbx usage)

**Testing:**
- `docs/TESTING_GUIDE.md §2` — Stage A selectors and environment flags
- `docs/development/TEST_SUITE_INDEX.md` — Test registry (no updates needed unless new tests added)
- `docs/development/testing_strategy.md` — Parity/gradcheck harness philosophy

**Fix Plan:**
- `docs/fix_plan.md` — TORCH-REFINE-002E entry (Attempts History, Exit Criteria)
- `plans/active/TORCH-REFINE-002E/implementation.md` — Phase C checklist, Branch G decision logic

**Findings:**
- `docs/findings.md:7` — GEOMETRY-003 row (update after successful validation)

**Prior Artifacts:**
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json` — Phase A3 results (24.5% χ² gap)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json` — Phase B1 results (large non-zero gradients)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/crystal_matrix_parity.json` — Phase A2 (both B_ideal variants show 1.4e-3 strain)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json` — Phase A0 (symmetric strain dominates)

## Next Up (optional)

If Phase C1 completes successfully (all exit criteria met):
1. **Update findings:** Refresh GEOMETRY-003 row in `docs/findings.md` with the mapping-aligned derivation
2. **Update fix_plan:** Mark TORCH-REFINE-002E as `done` in `docs/fix_plan.md`
3. **Proceed to TOOLING-VIS-001:** Validate that all Stage-A mapping visualizations (Phase 1-5) now pass with the geometry fix in place
4. **Return control to supervisor:** Galph will review artifacts and decide whether to pursue additional parity initiatives or move to the next Roadmap tier

If blocked:
- Document the blocker per "If Blocked" section above
- Return control to supervisor with explicit next-action recommendation
- Do not mark TORCH-REFINE-002E as `done` until all three exit criteria pass

## Doc Sync Plan

**Not required** — No new tests added this loop; only tooling scripts and bridge code changes. If parity probe or debug driver scripts evolve significantly, supervisor will handle `pytest --collect-only` and doc sync in a follow-up loop.

## Normative Math/Physics

See `docs/spec-db-workflow.md §Stage A` for the normative zero-point invariant definition:
> "for any Stage‑A configuration that claims DB‑AT‑024 mapping parity, zero geometry parameters (all cell/angle/orientation deltas equal to zero) and baseline scale MUST reproduce the DB‑AT‑024 mapping Bragg tensor produced by `simulate_forward_once`."

This fix implements the geometry alignment required to satisfy that invariant.
