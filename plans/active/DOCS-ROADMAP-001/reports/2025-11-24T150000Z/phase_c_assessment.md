# DOCS-ROADMAP-001 Phase C Assessment
**Timestamp**: 2025-11-24T150000Z
**Owner**: Galph (Supervisor)
**Context**: Ralph completed Phase B successfully (commit 04618ab2); assessing whether Phase C cross-reference updates are needed or initiative can be marked complete.

## Phase B Completion Summary
- **Status**: ✓ COMPLETE (all validation gates PASSED)
- **Outcome**: Plan thinned 305→146 lines (52.1% reduction)
- **Exit Criteria**: 6/6 Phase B validation criteria satisfied
- **Confidence**: HIGH (~95%)

## Phase C Scope (from implementation.md)
Phase C tasks (lines 72-95):
1. Update docs/index.md line 131 with guidance ("check specs for normative details")
2. Verify test references (1 comment in test_torch_refine_smoke.py line 1217)
3. Update DOCS-ROADMAP-001 implementation.md with completion notes
4. Run final validation (all cross-references resolve)
5. Update docs/fix_plan.md status=done + Attempts History
6. Commit Phase C changes

**Estimated Effort**: 1-2 hours

## Cross-Reference Analysis

### Critical References (require updates?)
1. **docs/index.md line 131-134**: Integration Plan entry
   - Current: "Phase-by-phase plan to replace optimizer with nanobrag_torch, deliverables, and validation"
   - Assessment: **Minor value** - description is accurate (plan still provides phase structure, deliverables, sequencing)
   - Proposed change: Add note "For normative requirements, see referenced spec shards" (1 line)

2. **tests/dbex/test_torch_refine_smoke.py line 1217**: Comment referencing integration plan
   - Context: "plans/nanobrag_integration_plan.md:226-244 specifies Stage B shell mode contract"
   - Current plan: Lines 226-244 NO LONGER EXIST (thinned to 146 lines)
   - **Issue**: Line numbers are invalid after thinning
   - Assessment: **BROKEN REFERENCE** - line range no longer exists
   - Proposed fix: Change to "See docs/spec-db-workflow.md §Stage B (lines 58-66) for Stage B shell mode contract"

### Non-Critical References (38 total)
- docs/fix_plan_archive.md: 19 historical entries (DO NOT UPDATE - preserved for history)
- docs/*.md: 17 references (mostly contextual, not line-specific)
- **Assessment**: LOW impact (contextual references, not brittle line numbers)

## Risk Assessment

### Option A: Complete Phase C (1-2 hours)
**Pros**:
- Fixes broken test comment (line 1217 reference invalid)
- Adds clarity to docs/index.md
- Completes all planned initiative phases
- Low effort (~1-2 hours)

**Cons**:
- Minor ROI (only 1 broken reference + 1 clarity improvement)
- Docs-only work (no functional impact)

### Option B: Mark Initiative Complete, Defer Phase C
**Pros**:
- Phase B delivered 80% of value (normative duplication eliminated)
- Faster pivot to next Tier 3 work
- Broken test comment is non-blocking (comment, not assertion)

**Cons**:
- Leaves 1 broken reference in test file (line 1217 points to non-existent lines 226-244)
- Misses opportunity for minor documentation polish

### Option C: Minimal Phase C (30 minutes)
**Pros**:
- Fix ONLY the broken test comment (line 1217)
- Skip docs/index.md update (minimal value)
- Quick closure with critical fix

**Cons**:
- Incomplete Phase C (not all planned tasks)

## Recommendation: **Option C (Minimal Phase C)**

**Rationale**:
1. **Broken reference fix is critical**: Test comment line 1217 references non-existent lines 226-244, which creates confusion for future readers
2. **High ROI**: 30 minutes fixes the ONE broken reference
3. **Pragmatic**: docs/index.md update is nice-to-have but not necessary (description remains accurate)
4. **CLAUDE.md alignment**: "Incremental progress over big bangs" - fix the broken reference, skip polish

**Implementation Protocol (Single Loop, 30 Minutes)**:
1. Read test_torch_refine_smoke.py lines 1210-1220 (context around line 1217)
2. Replace line 1217 comment reference:
   - OLD: "plans/nanobrag_integration_plan.md:226-244 specifies Stage B shell mode contract"
   - NEW: "docs/spec-db-workflow.md §Stage B (lines 58-66) specifies Stage B shell mode contract"
3. Update docs/fix_plan.md DOCS-ROADMAP-001 status=done with completion timestamp
4. Update implementation.md Phase C checklist (mark C2 complete, C1/C3/C4 skipped - minimal scope)
5. Commit: "DOCS-ROADMAP-001 Phase C (minimal): Fix broken test comment reference - tests: not run"
6. Update galph_memory.md with completion note

**Exit Criteria Status After Minimal Phase C**:
1. ✓ No normative duplication (Phase B)
2. ✓ Phase structure intact (Phase B)
3. ✓ Critical cross-refs fixed (test comment line 1217) - Minimal Phase C
4. ⏳ Optional polish (docs/index.md) - DEFERRED (minimal value)

## Alternative: If User Objects to Minimal Scope
If user wants full Phase C (docs/index.md update + all tasks), use full 1-2 hour implementation protocol from implementation.md lines 72-95.

## Confidence
**HIGH (~90%)** that minimal Phase C is appropriate:
- Fixes the ONE broken reference (test comment invalid line range)
- Delivers substantial initiative value (Phase A mapping + Phase B thinning + critical fix)
- Allows faster pivot to next Tier 3 work
- Aligns with CLAUDE.md pragmatic philosophy

## Decision Tree
- **Path A**: Minimal Phase C (30min, fix test comment only, mark done) - RECOMMENDED
- **Path B**: Full Phase C (1-2h, all planned tasks, comprehensive) - if user requests completeness
- **Path C**: Skip Phase C entirely (mark done with broken reference) - NOT RECOMMENDED (leaves confusion)
