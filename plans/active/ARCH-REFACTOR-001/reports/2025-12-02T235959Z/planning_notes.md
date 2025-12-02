# ARCH-REFACTOR-001 Phase C.9 Planning Notes
**Timestamp:** 2025-12-02T235959Z
**Focus:** Stage A Module Deletion (final cleanup)
**Galph Loop:** i=432

## Context
Phase C.8 completed (commit 937f47d4): all Stage A private helpers (_sync_stage_a_crystal, _build_stage_a_params, _run_stage_a_lbfgs) have been inlined into the StageA class.

Ralph's 2025-12-04T215000Z artifacts show all 4/4 validation tests PASSED:
- test_stage_a_expansion (7.45s)
- test_stage_a_engine_delegation_telemetry (49.55s)
- test_stage_b_baseline_guard_diff_payload (0.92s)
- test_stage_b_shell_modifiers (87.72s)

## Remaining Work for Phase C.9

### Items still in `stage_a_impl.py`
From `rg "^(def |class )" dbex/refinement/stage_a_impl.py`:

**Already extracted to `stage_a_utils.py` (Phase C.7, 2025-12-02T200000Z):**
- vec_to_unit_quaternion, quaternion_to_rotation_matrix, quaternion_to_xyz_euler
- _retarget_stage_a_simulators, _get_sigma_floor_sq_tensor, _build_stage_a_context
- _clamp_log_cell_deltas, _compute_panel_loss

**Already inlined into `StageA` class (Phase C.8, 2025-12-04T215000Z):**
- _sync_stage_a_crystal → `StageA._sync_crystal()`
- _build_stage_a_params → `StageA._build_stage_a_params()`
- _run_stage_a_lbfgs → `StageA._run_lbfgs()`

**Remaining in `stage_a_impl.py` that need relocation:**
- `StageAROIEntry` (dataclass, ~15-20 lines)
- `StageAContext` (dataclass, ~30-40 lines)

### Import Analysis

Current imports from `stage_a_impl.py`:

```bash
$ rg "from dbex.refinement.stage_a_impl import|from .stage_a_impl import" --type py
```

Results:
1. **dbex/nanobrag_refinement.py**: imports quaternion helpers (already in stage_a_utils)
2. **dbex/tools/stage_a_adam.py**: imports quaternion helpers (already in stage_a_utils)
3. **dbex/refinement/stage_c.py**: imports `StageAContext` (dataclass)
4. **dbex/refinement/stage_a_utils.py**: imports `StageAContext, StageAROIEntry` (dataclasses)
5. **dbex/refinement/stage_a.py**: imports `_compute_variance_weighted_loss` (BUG - should import from dbex.physics.loss, not stage_a_impl)

### Migration Strategy

#### Option 1: Move dataclasses to `dbex/refinement/context.py`
**Pros:**
- Consistent with other Stage contexts (StageBContext, StageCContext likely there)
- Single source of truth for all refinement contexts
- Aligns with ARCH-STAGE-CONTEXT-001 conventions

**Cons:**
- context.py may already be large

#### Option 2: Keep dataclasses in `stage_a_utils.py`
**Pros:**
- Minimal import changes (stage_a_utils already imports these)
- Keeps Stage A-specific items together

**Cons:**
- Slightly inconsistent (other stage contexts in context.py)

**Decision: Option 1 (move to context.py)** - follows the precedent from StageCContext (added in C.1.A to context.py per fix_plan.md line 66).

### Implementation Steps (Phase C.9)

**C9.A — Relocate StageAROIEntry and StageAContext dataclasses**
1. Copy `StageAROIEntry` and `StageAContext` from `stage_a_impl.py` to `dbex/refinement/context.py`
2. Place them near other Stage contexts (after StageATelemetryState, before/after StageCContext)
3. Ensure imports are updated (torch, typing, nanobrag_torch.Simulator, etc.)
4. Add cross-reference comments per ARCH-REFACTOR-001

**C9.B — Update all import sites (5 files)**
1. **dbex/refinement/stage_a_utils.py** (line 28): Change `from dbex.refinement.stage_a_impl import StageAContext, StageAROIEntry` to `from dbex.refinement.context import StageAContext, StageAROIEntry`
2. **dbex/refinement/stage_c.py** (line 42): Change `from dbex.refinement.stage_a_impl import StageAContext` to `from dbex.refinement.context import StageAContext`
3. **dbex/refinement/stage_a.py** (line 39 and inline imports):
   - Fix the bug: change `from dbex.refinement.stage_a_impl import _compute_variance_weighted_loss` to `from dbex.physics.loss import _compute_variance_weighted_loss`
   - Change inline `from dbex.refinement.stage_a_impl import StageAContext` (line ~1248) to `from dbex.refinement.context import StageAContext`
4. **dbex/nanobrag_refinement.py** (lines 58-62): Change quaternion imports from `stage_a_impl` to `stage_a_utils`
5. **dbex/tools/stage_a_adam.py** (lines 22-25): Change quaternion imports from `stage_a_impl` to `stage_a_utils`

**C9.C — Delete stage_a_impl.py**
1. Verify no remaining imports: `rg "from.*stage_a_impl import|import.*stage_a_impl" --type py` (excluding docs/logs/backups)
2. Delete `dbex/refinement/stage_a_impl.py`
3. Update module docstrings if needed

**C9.D — Validation**
Run 6 selectors to ensure no regressions:
1. `test_stage_a_expansion` (Stage A smoke with expansion + telemetry)
2. `test_stage_a_engine_delegation_telemetry` (Stage A engine delegation)
3. `test_stage_b_baseline_guard_diff_payload` (Stage B parity guard)
4. `test_stage_b_shell_modifiers` (Stage B shell smoke)
5. `test_stage_c_detector_microslip` (Stage C smoke, uses StageAContext)
6. `test_refgeom_integration` (Reconstruction integration, may use quaternion helpers)

All must PASS with canonical env flags.

## Expected Metrics
- **Files deleted:** 1 (`stage_a_impl.py`, ~1524 lines)
- **Files modified:** 5 (context.py +~50 lines for dataclasses, 4 import updates -5 to -10 lines each)
- **Net change:** -1450 to -1470 lines across repo
- **Import verification:** `rg "stage_a_impl"` should return only docs/logs/backups/comments

## Risk Analysis
**Low Risk:**
- Dataclasses are just type definitions with no logic
- All consumers already tested in Phase C.8
- Quaternion helpers already extracted to stage_a_utils in Phase C.7

**Mitigation:**
- Comprehensive validation suite (6 selectors)
- Explicit import verification step before deletion

## Exit Criteria Alignment
Completing C.9 satisfies ARCH-REFACTOR-001 Exit Criterion #1:
> `dbex/refinement/stage_a_impl.py`, `stage_b_impl.py`, `stage_c_impl.py` are deleted.

✓ stage_b_impl.py deleted (Phase C.6, 2025-12-02T190946Z)
✓ stage_c_impl.py deleted (Phase C.3, 2025-12-04T150500Z)
⧗ stage_a_impl.py pending (Phase C.9, this loop)

## References
- ARCH-REFACTOR-001 exit criteria: docs/fix_plan.md lines 58-61
- ARCH-STAGE-CONTEXT-001: Typed context precedent (StageCContext added to context.py)
- ARCH-LAZY-IMPORTS-001: Module-scope import hygiene
- Phase C.7 completion: fix_plan.md line 77 (stage_a_utils extraction)
- Phase C.8 completion: fix_plan.md line 78 (Stage A private helper inlining)
