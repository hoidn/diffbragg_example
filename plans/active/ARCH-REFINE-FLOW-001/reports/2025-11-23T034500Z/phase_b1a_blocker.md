# Phase B1a Blocker Report

**Date:** 2025-11-23T034500Z
**Initiative:** ARCH-REFINE-FLOW-001
**Phase:** B1a (Extract Stage A helper functions)
**Loop:** i=191 (ralph)

## Blocker Summary

**Step Failed:** Step 3-4 (Extract `_build_stage_a_params` and `_build_stage_a_lbfgs_closure`)

**Status:** BLOCKED — Extraction scope exceeds single-loop capacity given accidental reversion and complexity

## What Was Attempted

### Attempt 1: Direct Extraction (Successful, then Lost)
1. Successfully created `_build_stage_a_params` helper (lines 680-1014, ~335 lines)
2. Added `beam` parameter to function signature
3. File was at 3383 lines after first helper insertion
4. **PROBLEM:** During debugger subagent invocation, file was accidentally reverted via `git checkout`, losing all progress
5. File returned to original 3048 lines

### Attempt 2: Recovery via Debugger Subagent (Failed)
1. Invoked `Task` tool with `debugger` subagent to complete extraction
2. Subagent identified the reversion issue
3. Subagent created temp files for helpers 2 and 3 but couldn't complete insertion
4. Left file in reverted state (3048 lines)

## Root Cause Analysis

### Primary Issue: Extraction Complexity
- **Scope:** ~1000 lines across 3 helpers (335 + 575 + 110 lines)
- **Nested Functions:** Helper 2 contains TWO nested functions (`compute_loss` + `closure`) that must capture ~30 nonlocal variables via lexical scope
- **Critical Requirements:**
  - Preserve lazy imports (nanobrag_bridge INSIDE nested functions)
  - Maintain exact telemetry field names
  - Keep lifecycle tracking (U-matrix lifecycle_log, A* reconstruction)
  - Preserve gradient validation NaN/Inf checks
  - Keep periodic full validation logic
  - Maintain 3 parameterization modes (cell+misset, U-matrix, incremental UB)

### Secondary Issue: Accidental Reversion
- Debugger subagent ran `git checkout` reverting uncommitted changes
- Lost ~335 lines of first helper extraction
- Would need to re-extract all three helpers from scratch

### Tertiary Issue: Token Budget
- Single Edit operation for 575-line helper 2 approaches token limits
- Need multiple Edit operations + verification for each
- Risk of introducing bugs in nested function captures

## Exact Error/Behavior

No error message — blocker is **task scope** and **accidental state loss**.

**Observable State:**
```bash
$ wc -l dbex/nanobrag_refinement.py
3048 dbex/nanobrag_refinement.py
```

Expected after all 3 helpers: ~3400 lines (1000 extracted inline → 1000 in helpers + dict wiring in main function)

## Recommended Escalation Path

### Option A: Multi-Loop Extraction (RECOMMENDED)
Split Phase B1a into 3 sub-loops:
1. **Loop 1 (this loop):** Extract `_build_stage_a_params` only (Step 3)
   - Add helper before `run_nanobrag_refinement`
   - Regression guard: PASS (no behavior change, helper not yet called)
   - Commit partial progress
2. **Loop 2:** Extract `_build_stage_a_lbfgs_closure` (Step 4)
   - Add helper after `_build_stage_a_params`
   - Regression guard: PASS (helpers not yet wired)
   - Commit partial progress
3. **Loop 3:** Extract `_run_stage_a_lbfgs` + Refactor main function (Steps 5-10)
   - Add third helper
   - Refactor `run_nanobrag_refinement` to call all three
   - Update final Bragg generation dict access
   - Regression guard: MUST PASS with telemetry parity
   - Compare telemetry, update implementation.md, commit

**Advantages:**
- Each loop is manageable scope (~300-600 lines per extraction)
- Can verify compilation/imports after each helper
- Reduces risk of introducing bugs
- Aligns with CLAUDE.md incremental progress principle

**Disadvantages:**
- Takes 3 loops instead of 1
- Violates input.md "MUST complete ALL of Steps 3-10 in this loop" requirement
- Delays Phase B1b

### Option B: Simplified Helper Extraction
Keep all 1000 lines inline, extract only parameter initialization and optimizer setup:
- `_build_stage_a_params`: lines 761-996 (params + telemetry + optimizer)
- Keep closures inline in `run_nanobrag_refinement`
- Defer full closure extraction to Phase B1b

**Advantages:**
- Smaller extraction (~235 lines)
- Easier to verify
- Still makes progress toward modularization

**Disadvantages:**
- Doesn't achieve Phase B1a goal (extract closure logic)
- Leaves monolithic closure inline
- May need to re-extract later

### Option C: Supervisor Review + Manual Extraction
1. Ralph documents exact extraction boundaries with line numbers
2. Supervisor (Galph) reviews and approves multi-loop split
3. Ralph completes Loop 1 (Step 3 only) in this turn
4. Galph authors next input.md for Loop 2

**Advantages:**
- Clear supervision of large refactoring
- Explicit approval for multi-loop approach
- Maintains quality gates

**Disadvantages:**
- Requires supervisor round-trip
- Delays completion

## Artifacts

### Temp Files (from debugger subagent, may be stale):
- `/tmp/complete_second_helper.py` (687 lines, helper 2 draft)
- `/tmp/third_helper.py` (171 lines, helper 3 draft)

**WARNING:** These files were created before reversion and may reference old line numbers. Recommend re-extraction from current state.

### Extraction Documentation:
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T032647Z/phase_b1a_extraction.md` (350 lines, boundaries + nonlocal variables)

## Decision Required

**Recommended Action:** Option A (Multi-Loop Extraction)

**Justification:**
1. CLAUDE.md §"When Stuck (After 3 Attempts)" → "Is there a simpler approach entirely?" → Multi-loop is simpler per-loop
2. CLAUDE.md §"Incremental progress over big bangs" → 3 smaller commits better than 1 risky massive refactoring
3. input.md blocker escalation allows stopping and documenting
4. Quality gate: Prefer safe incremental extraction over rushing all 3 helpers + refactoring in one loop

**Next Actions (if Option A approved):**
1. Ralph completes Step 3 only in this loop: Extract `_build_stage_a_params`, commit
2. Supervisor reviews + approves multi-loop approach
3. Next loop: Ralph extracts `_build_stage_a_lbfgs_closure`
4. Loop after: Ralph extracts `_run_stage_a_lbfgs` + refactors main function

**Supervisor Decision Point:** Approve Option A (multi-loop) OR provide alternative guidance.
