# Ralph Task Input: DOCS-ROADMAP-001 Phase C (Minimal Scope)

## Summary
Fix broken test comment reference after integration plan thinning; mark DOCS-ROADMAP-001 complete.

## Mode
Docs

## Focus
DOCS-ROADMAP-001 — Thin `nanobrag_integration_plan` (Phase C: Minimal cross-reference fix)

## Branch
integration

## Mapped Tests
none — documentation-only (test comment fix + docs updates)

## Artifacts
plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/

## Context
Ralph completed Phase B (commit 04618ab2, loop i=276): thinned integration plan 305→146 lines (52% reduction) by replacing normative sections with spec references. **Issue**: Test comment at `tests/dbex/test_torch_refine_smoke.py:1217` references non-existent lines 226-244 in the now-thinned plan. **Minimal Phase C scope**: Fix the ONE broken reference, mark initiative done.

**Phase C Assessment**: Galph analysis (plans/active/SUPERVISOR/reports/2025-11-24T150000Z/phase_c_assessment.md) recommends **Minimal Phase C** (30 minutes, fix critical broken reference only, skip optional polish). Full Phase C would take 1-2 hours for minor additional value (docs/index.md clarity note).

## Do Now (6-Step Protocol)

**Objective**: Fix broken test comment reference and close DOCS-ROADMAP-001.

### Step 1: Read Test Comment Context
Read `tests/dbex/test_torch_refine_smoke.py` lines 1210-1220 to understand context around the broken reference at line 1217.

### Step 2: Fix Broken Test Comment Reference
**File**: `tests/dbex/test_torch_refine_smoke.py:1217`

**Current broken reference**:
```python
    - plans/nanobrag_integration_plan.md:226-244 specifies Stage B shell mode contract
```

**Issue**: Lines 226-244 NO LONGER EXIST after Phase B thinning (plan is now 146 lines).

**Fix**: Replace with spec reference (per Phase B normative mapping):
```python
    - docs/spec-db-workflow.md §Stage B (lines 58-66) specifies Stage B shell mode contract
```

**Validation**: Verify line 1217 now points to existing spec location.

### Step 3: Update Implementation Plan Status
**File**: `plans/active/DOCS-ROADMAP-001/implementation.md`

Mark Phase C checklist status (lines 72-95):
- [x] C2: Verify test references (COMPLETE - fixed line 1217 broken reference)
- [~] C1: Update docs/index.md (SKIPPED - minimal scope, optional polish deferred)
- [~] C3-C6: Final validation/commits (MERGED with Step 5-6)

Add completion note at end of file:
```markdown
## Completion Summary (2025-11-24T150000Z)
**Status**: ✓ COMPLETE (Minimal Phase C)
**Outcome**: Fixed broken test comment reference (line 1217), initiative closed
**Scope Decision**: Minimal Phase C executed per galph_memory.md recommendation (fix critical broken reference, defer optional docs/index.md polish for minimal ROI)
**Value Delivered**:
- Phase A: Normative content mapped to specs (0 gaps found)
- Phase B: Plan thinned 305→146 lines (52% reduction), normative duplication eliminated
- Phase C: Critical cross-reference fix (test comment invalid line range corrected)
**Exit Criteria**: 3/3 satisfied (#1 no normative duplication ✓, #2 phase structure intact ✓, #3 critical cross-refs fixed ✓)
```

### Step 4: Update Fix Plan Ledger
**File**: `docs/fix_plan.md`

Update DOCS-ROADMAP-001 entry:
1. Change status line: `Status: done (2025-11-24T150000Z — Phase C minimal scope: broken test comment fixed, initiative complete)`
2. Add Attempts History entry (prepend to existing history):
```markdown
  * 2025-11-24T150000Z (implementation, i=277) — **Phase C ✓ COMPLETE (Minimal Scope)** — Fixed broken test comment reference at `tests/dbex/test_torch_refine_smoke.py:1217` (OLD: plans/nanobrag_integration_plan.md:226-244 → NEW: docs/spec-db-workflow.md §Stage B lines 58-66). **Scope Decision**: Minimal Phase C per galph_memory.md recommendation (30 minutes, fix critical broken reference only, defer optional docs/index.md polish for minimal ROI). **Value Delivered**: Phase A (normative mapping, 0 gaps), Phase B (plan thinned 305→146 lines 52% reduction), Phase C (critical cross-ref fix). **Exit Criteria**: 3/3 satisfied (#1 no normative duplication ✓ Phase B, #2 phase structure intact ✓ Phase B, #3 critical cross-refs fixed ✓ Phase C minimal). **Confidence**: HIGH (~95%) - broken reference corrected, substantial initiative value delivered, allows faster Tier 3 pivot. **Artifacts**: plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/{decision.json, summary.md, phase_c_assessment.md}.
```

### Step 5: Create Completion Artifacts
**Directory**: `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/`

Create `decision.json`:
```json
{
  "loop_id": "i=277",
  "timestamp": "2025-11-24T150000Z",
  "owner": "ralph",
  "phase": "C_minimal",
  "task": "Fix broken test comment reference after integration plan thinning",
  "decision_path": "A",
  "decision_paths": {
    "A": "Minimal Phase C - Fix critical broken reference only, mark done",
    "B": "Full Phase C - All planned tasks (docs/index.md + test ref + validation)",
    "C": "Skip Phase C - Mark done with broken reference (NOT RECOMMENDED)"
  },
  "scope_decision": "Minimal Phase C per Galph recommendation (30min, fix test comment line 1217 only, defer optional docs/index.md polish)",
  "changes_applied": {
    "test_comment_fix": {
      "file": "tests/dbex/test_torch_refine_smoke.py",
      "line": 1217,
      "old_ref": "plans/nanobrag_integration_plan.md:226-244",
      "new_ref": "docs/spec-db-workflow.md §Stage B (lines 58-66)",
      "rationale": "Lines 226-244 no longer exist after Phase B thinning (plan now 146 lines)"
    }
  },
  "deferred_tasks": {
    "docs_index_update": "DEFERRED - minimal ROI, description remains accurate"
  },
  "exit_criteria_status": {
    "1_no_normative_duplication": "SATISFIED (Phase B)",
    "2_phase_structure_intact": "SATISFIED (Phase B)",
    "3_critical_cross_refs_fixed": "SATISFIED (Phase C minimal - test comment line 1217 fixed)"
  },
  "value_delivered": {
    "phase_a": "Normative content mapped to specs (0 gaps found)",
    "phase_b": "Plan thinned 305→146 lines (52% reduction), normative duplication eliminated",
    "phase_c": "Critical cross-reference fix (broken test comment corrected)"
  },
  "confidence": "HIGH (~95%)",
  "confidence_rationale": "Broken reference fixed (critical), substantial initiative value delivered (Phase A+B+C minimal), allows faster Tier 3 pivot"
}
```

Create `summary.md`:
```markdown
### Turn Summary
Fixed broken test comment reference (test_torch_refine_smoke.py:1217) pointing to non-existent integration plan lines after Phase B thinning.
Minimal Phase C scope executed per supervisor recommendation: corrected critical broken reference, deferred optional docs polish.
Initiative complete: Phase A normative mapping + Phase B plan thinning (52% reduction) + Phase C cross-ref fix delivered substantial value.
Artifacts: plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/ (decision.json, summary.md, phase_c_assessment.md)
```

### Step 6: Commit and Push
```bash
git add -A && \
git commit -m "DOCS-ROADMAP-001 Phase C (minimal): Fix broken test comment reference — tests: not run

Fixed broken reference in tests/dbex/test_torch_refine_smoke.py:1217 after Phase B
integration plan thinning (305→146 lines):
- OLD: plans/nanobrag_integration_plan.md:226-244 (no longer exists)
- NEW: docs/spec-db-workflow.md §Stage B (lines 58-66)

Minimal Phase C scope per supervisor recommendation (30min, fix critical broken
reference only, defer optional docs/index.md polish for minimal ROI).

Initiative complete:
- Phase A: Normative content mapped to specs (0 gaps found)
- Phase B: Plan thinned 305→146 lines (52% reduction)
- Phase C: Critical cross-reference fix

Exit criteria: 3/3 satisfied (#1 no normative duplication ✓, #2 phase structure
intact ✓, #3 critical cross-refs fixed ✓).

Artifacts: plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/" && \
git push
```

**If push rejected**: `timeout 30 git pull --rebase`, resolve conflicts, then `git push` again.

## How-To Map

### Fix Test Comment
```bash
# Read context
cat tests/dbex/test_torch_refine_smoke.py | sed -n '1210,1220p'

# Use Edit tool to replace line 1217:
# OLD: "    - plans/nanobrag_integration_plan.md:226-244 specifies Stage B shell mode contract"
# NEW: "    - docs/spec-db-workflow.md §Stage B (lines 58-66) specifies Stage B shell mode contract"
```

### Update Implementation Plan
Use Edit tool on `plans/active/DOCS-ROADMAP-001/implementation.md`:
1. Update Phase C checklist status (lines 72-95)
2. Append completion summary section at end

### Update Fix Plan
Use Edit tool on `docs/fix_plan.md`:
1. Find DOCS-ROADMAP-001 section (~line 1500-1600 estimated)
2. Update status line
3. Prepend new Attempts History entry (above existing 2025-11-24T145000Z entry)

### Create Artifacts
Use Write tool for:
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/decision.json`
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T150000Z/summary.md`

## Pitfalls To Avoid

1. **Environment Freeze**: Documentation-only work, no code/environment changes ✓
2. **Exact line matching**: Use Edit tool with EXACT old_string from file (include leading spaces)
3. **Spec reference format**: Match existing format "docs/spec-db-workflow.md §Stage B (lines 58-66)"
4. **No over-scope**: Do NOT update docs/index.md (deferred per minimal scope decision)
5. **Commit message format**: Include "DOCS-ROADMAP-001 Phase C (minimal)" prefix
6. **Git push timeout**: Use `timeout 30` for pull/push to avoid hangs
7. **Artifacts path**: Use existing 2025-11-24T150000Z directory (matches timestamp from Phase C assessment)

## If Blocked

1. **Test comment line number mismatch**: Re-read file to find exact line with broken reference
2. **Spec reference uncertainty**: Check Phase B decision.json (line 154-158) for Stage B spec location
3. **Fix plan entry not found**: Grep for "DOCS-ROADMAP-001" to locate section
4. **Git push fails repeatedly**: Document issue in summary.md, return to Galph

## Findings Applied

**Mandatory from docs/findings.md**:
- **POLICY-001** (Environment Freeze): Documentation-only work, no installs/upgrades ✓
- **CLAUDE.md**: Incremental progress (3-phase breakdown), pragmatic (fix critical, defer polish) ✓

**Phase C Assessment Reference**: plans/active/SUPERVISOR/reports/2025-11-24T150000Z/phase_c_assessment.md (Galph recommendation: Minimal Phase C, fix broken test comment only)

## Pointers

**Key Files**:
- Test file: `tests/dbex/test_torch_refine_smoke.py:1217` (broken reference)
- Implementation plan: `plans/active/DOCS-ROADMAP-001/implementation.md:72-95` (Phase C checklist)
- Fix plan ledger: `docs/fix_plan.md` (DOCS-ROADMAP-001 section, search for "### [DOCS-ROADMAP-001]")
- Phase B decision: `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/decision.json:154-158` (Stage B spec location)

**Spec References**:
- Stage B normative location: `docs/spec-db-workflow.md:58-66` (§Stage B)
- Phase A mapping analysis: `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/normative_content_map.md`

## Next Up (Optional, If Finished Early)

NOT APPLICABLE - Single focused task (30 minutes), no early finish expected. If complete early, return to Galph for next focus selection (Tier 3 roadmap pivot).

## Success Criteria

**Primary**:
1. ✅ Test comment line 1217 references valid spec location (docs/spec-db-workflow.md §Stage B)
2. ✅ Implementation plan marked complete with minimal scope note
3. ✅ Fix plan ledger status=done with Phase C Attempts History entry
4. ✅ Artifacts created (decision.json, summary.md in 2025-11-24T150000Z/)
5. ✅ Changes committed and pushed successfully

**Validation**:
- Grep test file line 1217: should show "docs/spec-db-workflow.md §Stage B (lines 58-66)"
- Fix plan DOCS-ROADMAP-001 status line: should show "done (2025-11-24T150000Z"
- Git log HEAD: should show "DOCS-ROADMAP-001 Phase C (minimal)" commit message

**Time Budget**: 30 minutes (6 steps: read 5min, fix comment 5min, update plans 10min, artifacts 5min, commit 5min)
