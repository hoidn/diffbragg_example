# ARCH-REFINE-FLOW-001 Phase B1a-loop1 — Extract `_build_stage_a_params` Helper ONLY

## Summary
Extract ONLY the first helper function (`_build_stage_a_params`) from inline LBFGS closure in `run_nanobrag_refinement`. This is loop 1 of 3 for Phase B1a extraction (approved multi-loop strategy per blocker escalation 2025-11-23T040000Z).

## Mode
none (incremental production refactoring, partial progress commit)

## Focus
ARCH-REFINE-FLOW-001 — Refactor to Protocol-based Refinement Engine (Phase B1a-loop1: Extract first helper)

## Branch
integration

## Mapped Tests
- **NONE** — This loop extracts a helper but does NOT wire it into the runtime (no regression guard needed)
- **Compilation verification only:** Ensure imports/syntax are valid after extraction

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/`
- `helper1_extraction_summary.md` (MANDATORY — extraction notes, line ranges, parameter list)
- `compilation_check.log` (MANDATORY — python -m py_compile dbex/nanobrag_refinement.py output)
- `summary.md` (MANDATORY — Turn Summary block)

## Do Now (Simplified — Extract Helper 1 ONLY)

### Context
Ralph's i=191 blocker report identified that extracting all 3 helpers + refactoring in one loop exceeded single-loop capacity (token budget + accidental state loss from `git checkout` reversion). Supervisor APPROVED multi-loop extraction strategy (3 sub-loops). This is **loop 1 of 3**.

**Scope Reduction from i=191:**
- i=191 attempted: Extract all 3 helpers + refactor main function (~1000 lines total)
- **This loop (i=192):** Extract `_build_stage_a_params` ONLY (~335 lines including beam fix)
- **Next loop (i=193):** Extract `_build_stage_a_lbfgs_closure` (~575 lines with nested functions)
- **Loop after (i=194):** Extract `_run_stage_a_lbfgs` + refactor main function + regression guard

### Step 1: Review Prior Extraction Documentation
Read your own extraction analysis from i=190:
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T032647Z/phase_b1a_extraction.md`
  - Section 1 boundaries: lines ~761-876 (parameter initialization)
  - Nonlocal variables: ~30 documented
  - Helper signature: `_build_stage_a_params(crystal, detector, inputs, config, device, dtype, hkl_grid, hkl_metadata, sigma_floor_sq_cache, baseline_crystal, baseline_detector)`

**DO NOT re-document.** Proceed directly to extraction.

### Step 2: Extract `_build_stage_a_params` Helper

**Location:** Add BEFORE `run_nanobrag_refinement` in `dbex/nanobrag_refinement.py` (around line 650-680)

**Action:** Copy lines ~761-876 from `run_nanobrag_refinement` (Stage A LBFGS parameter initialization section) into this new helper function.

**Exact Signature (from your phase_b1a_extraction.md):**
```python
def _build_stage_a_params(
    crystal,
    detector,
    inputs,
    config: RefinementConfig,
    device,
    dtype,
    hkl_grid,
    hkl_metadata,
    sigma_floor_sq_cache,
    baseline_crystal,
    baseline_detector,
    beam  # IMPORTANT: Add this parameter (identified in i=191 Attempt 1)
):
    """
    Build trainable parameters for Stage A LBFGS refinement.

    Supports 3 parameterization modes:
    - cell + misset (default)
    - U-matrix (config.use_u_matrix_parameterization=True)
    - incremental UB (config.use_incremental_ub=True)

    Returns:
        Dict with keys: params, param_values, telemetry_state, stage_a_context, optimizer
    """
    # ... extract lines ~761-876 here ...

    return {
        'params': params,
        'param_values': param_values,
        'telemetry_state': telemetry_state,
        'stage_a_context': stage_a_context,
        'optimizer': optimizer
    }
```

**Critical Implementation Notes:**

1. **Include beam parameter:** In i=191 Attempt 1, you discovered that `beam` is needed for MOSFLM A* calculation. Add it to the signature.

2. **Preserve ALL 3 parameterization modes:**
   - Lines ~817-876: `if config.use_incremental_ub:` branch
   - Lines ~937-996: `if config.use_u_matrix_parameterization:` branch
   - Lines ~761-816: Default cell+misset branch

3. **Keep optimizer initialization exactly as-is:**
   ```python
   optimizer = torch.optim.LBFGS(
       params,
       history_size=config.lbfgs_history_size,
       line_search_fn="strong_wolfe"
   )
   ```

4. **Preserve telemetry accumulator initialization:**
   - All list comprehensions: `chi_squared_trace_sampled = [[0, 0.0]]`
   - Mutable counters: `iteration_count = [0]`
   - Dict builders: `param_deltas = {'initial': {}, 'final': {}}`

5. **Keep warm-cache context building:**
   - `stage_a_context = _build_stage_a_context(...)` call
   - ROI/panel sampling logic
   - Perf counter initialization

6. **Return Dict structure:**
   ```python
   return {
       'params': params,              # List of torch.nn.Parameter objects
       'param_values': param_values,  # Dict mapping param names to tensors
       'telemetry_state': {           # Mutable telemetry accumulators
           'chi_squared_trace_full': chi_squared_trace_full,
           'chi_squared_trace_sampled': chi_squared_trace_sampled,
           'iteration_count': iteration_count,
           'param_deltas': param_deltas,
           # ... all other telemetry fields ...
       },
       'stage_a_context': stage_a_context,  # StageAContext object
       'optimizer': optimizer         # torch.optim.LBFGS instance
   }
   ```

7. **DO NOT change logic:** This is a pure extraction. Copy lines exactly, no refactoring.

8. **DO NOT wire into main function yet:** Leave `run_nanobrag_refinement` unchanged. The helper exists but is not called.

### Step 3: Verify Compilation

```bash
python -m py_compile dbex/nanobrag_refinement.py \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/compilation_check.log 2>&1

echo $?  # Should be 0 (success)
```

**If compilation fails:**
- Check for missing imports
- Verify helper is defined BEFORE `run_nanobrag_refinement`
- Check indentation (must be module-level function, not nested)
- Document error in blocker report if unresolvable

### Step 4: Document Extraction

Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/helper1_extraction_summary.md`:

```markdown
# Helper 1 Extraction Summary

**Date:** 2025-11-23T040000Z
**Loop:** i=192 (ralph)
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop1

## Extracted Helper

**Function:** `_build_stage_a_params`
**Location:** dbex/nanobrag_refinement.py (added before run_nanobrag_refinement)
**Line Range (Source):** ~761-876 (original inline location)
**Line Count:** ~335 lines (including docstring + return statement)

## Parameters (11 total)

1. crystal
2. detector
3. inputs
4. config: RefinementConfig
5. device
6. dtype
7. hkl_grid
8. hkl_metadata
9. sigma_floor_sq_cache
10. baseline_crystal
11. baseline_detector
12. beam (added per i=191 Attempt 1 fix)

## Return Value

Dict with 5 keys:
- `params`: List[torch.nn.Parameter]
- `param_values`: Dict[str, torch.Tensor]
- `telemetry_state`: Dict[str, Any]
- `stage_a_context`: StageAContext
- `optimizer`: torch.optim.LBFGS

## Parameterization Modes Preserved

- [x] Default: cell + misset (lines ~761-816 source)
- [x] U-matrix: config.use_u_matrix_parameterization (lines ~937-996 source)
- [x] Incremental UB: config.use_incremental_ub (lines ~817-876 source)

## Telemetry Fields Initialized

- chi_squared_trace_full
- chi_squared_trace_sampled
- masked_mse_trace_full
- iteration_count
- param_deltas
- lifecycle_log (U-matrix mode only)
- quaternion_norm_trace (U-matrix mode only)

## Compilation Check

Status: PASSED / FAILED
Error (if any): ...

## Next Steps (Loop i=193)

Extract `_build_stage_a_lbfgs_closure` helper (~575 lines with nested functions).
```

### Step 5: Update Implementation Checklist

Edit `plans/active/ARCH-REFINE-FLOW-001/implementation.md` line ~86:

Change:
```markdown
- [ ] B1a-loop1: **Extract `_build_stage_a_params` helper ONLY** (Loop i=192):
```

To:
```markdown
- [x] B1a-loop1: **Extract `_build_stage_a_params` helper ONLY** (Loop i=192): ✓ COMPLETE (2025-11-23T040000Z)
```

### Step 6: Write Turn Summary

Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/summary.md`:

```markdown
### Turn Summary
Extracted first Stage A helper function (`_build_stage_a_params`, ~335 lines) from inline LBFGS closure per approved multi-loop strategy.
Helper not yet wired into runtime (no behavior change, no regression guard needed).
Compilation check PASSED, all 3 parameterization modes preserved (cell+misset, U-matrix, incremental UB).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/ (helper1_extraction_summary.md, compilation_check.log)
```

### Step 7: Commit and Push

```bash
git add dbex/nanobrag_refinement.py \
  plans/active/ARCH-REFINE-FLOW-001/implementation.md \
  plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/

git commit -m "ARCH-REFINE-FLOW-001 Phase B1a-loop1: Extract _build_stage_a_params helper

Extracted first of three Stage A helper functions (~335 lines) from inline
LBFGS closure per approved multi-loop extraction strategy (i=191 blocker).

Helper signature includes 12 parameters (added beam per i=191 Attempt 1).
Supports 3 parameterization modes: cell+misset, U-matrix, incremental UB.
Returns dict with params, param_values, telemetry_state, stage_a_context, optimizer.

Helper not yet wired (no runtime changes, no regression guard needed).
Compilation check PASSED.

Next loop (i=193): Extract _build_stage_a_lbfgs_closure (~575 lines).

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/

tests: not run"

git push
```

---

## How-To Map

### Extraction Location
Add `_build_stage_a_params` at line ~650-680 in `dbex/nanobrag_refinement.py`, BEFORE the `run_nanobrag_refinement` function definition.

### Source Lines
Copy from `run_nanobrag_refinement` lines ~761-876 (Stage A parameter initialization section).

### Beam Parameter Fix
In i=191 Attempt 1, you discovered that `beam` is needed. Add it to the helper signature (12th parameter).

### Compilation Check
```bash
python -m py_compile dbex/nanobrag_refinement.py
```

---

## Pitfalls To Avoid

1. **DO NOT extract helpers 2 or 3** — This loop is ONLY helper 1
2. **DO NOT refactor main function** — Leave `run_nanobrag_refinement` unchanged
3. **DO NOT run regression guard** — Helper is not wired yet (no behavior change)
4. **DO NOT change parameter initialization logic** — Extract as-is
5. **DO NOT forget beam parameter** — You identified this need in i=191 Attempt 1
6. **DO NOT modify telemetry field names** — Preserve backward compatibility
7. **DO NOT remove comments** — Keep TORCH-REFINE-* / PHYSICS-LOSS-* annotations
8. **DO NOT introduce new imports** — All imports stay as they were
9. **DO NOT nest helper inside run_nanobrag_refinement** — Must be module-level function
10. **DO NOT commit if compilation fails** — Debug first, helper must be syntactically valid

---

## If Blocked

### Scenario A: Compilation fails with import errors
**Action:**
1. Check that helper is defined BEFORE `run_nanobrag_refinement`
2. Verify no new imports were added
3. Ensure helper is module-level (not nested inside another function)
4. Document error in blocker report: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/blocker.md`
5. Commit blocker report (do NOT leave workspace dirty)

### Scenario B: Cannot locate exact line ranges
**Action:**
1. Use your i=190 extraction documentation: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T032647Z/phase_b1a_extraction.md`
2. Search for "Stage A: LBFGS parameter initialization" comment in code
3. Look for `params = []` initialization (start of section)
4. Look for `optimizer = torch.optim.LBFGS(` (end of section)
5. Document ambiguity in blocker report if boundaries are unclear

### Scenario C: Accidental state loss (git revert/checkout)
**Action:**
1. **STOP IMMEDIATELY** — Do not attempt recovery via subagents
2. Document what was lost in blocker report
3. Commit blocker report
4. Supervisor will review and provide guidance

---

## Findings Applied

- **CONVERGENCE-001**: Preserve U-matrix lifecycle telemetry in param initialization
- **GEOMETRY-003**: Preserve MOSFLM baseline misset derivation
- **GEOMETRY-004**: Preserve incremental UB initialization
- **REFINE-006**: Preserve ≥0.2% improvement gate (telemetry tracking)
- **PHYSICS-LOSS-001**: Preserve dual metric tracking (chi_squared + masked_mse)
- **PERF-WARM-SIM-001**: Preserve stage_a_ctx, perf counters, sampled indices
- **GRADIENT-001**: Preserve MOSFLM a/b/c_star path (no cell overrides)

---

## Pointers

### Extraction Documentation (From i=190)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T032647Z/phase_b1a_extraction.md:15-80` — Helper 1 boundaries and signature

### Blocker Report (From i=191)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/phase_b1a_blocker.md` — Why multi-loop extraction is needed

### Implementation Plan
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:86-92` — Phase B1a-loop1 checklist

### Code Target
- `dbex/nanobrag_refinement.py:~761-876` — Source lines for helper 1 extraction

---

## Next Up

**Loop i=193 (after this loop completes):**
- Extract `_build_stage_a_lbfgs_closure` helper (~575 lines with TWO nested functions)
- More complex than helper 1 (requires lexical scope preservation for ~30 nonlocal variables)
- Still NO regression guard (helpers not wired until loop i=194)

**Loop i=194 (final extraction loop):**
- Extract `_run_stage_a_lbfgs` helper (~110 lines)
- Refactor `run_nanobrag_refinement` to call all three helpers
- Update final Bragg generation to use dicts
- MANDATORY regression guard: test_stage_a_expansion MUST PASS
- MANDATORY telemetry comparison: chi² traces must match baseline
