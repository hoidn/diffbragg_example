# DOCS-ROADMAP-001 Planning Analysis
## Loop: i=275, Timestamp: 2025-11-24T130000Z, Owner: Galph

## 1. Initiative Context
**Focus**: DOCS-ROADMAP-001 — Thin `nanobrag_integration_plan` to reference specs instead of repeating normative content
**Status**: pending (stub implementation plan exists)
**Priority**: Medium (documentation hygiene, no blocking dependencies)
**Estimated Effort**: 2-3 loops (~4-6 hours total: 1 loop analysis + thin/refactor ~2h, 1-2 loops validation + cross-reference updates ~2-4h)

**Dependencies**: specs/spec-db-workflow.md (Stage A/B/C definitions), docs/spec-db-core.md (units, masks, variance), docs/nanobrag_api.md (detector config mapping)
**Blockers**: None (all dependencies satisfied per Tier 1-2 completion)

## 2. Current State Analysis

### Target File Assessment
- **File**: `plans/nanobrag_integration_plan.md`
- **Size**: 305 lines
- **Problem**: Contains normative requirements that duplicate content already in specs (detector mapping rules, Stage policy SHALL/SHOULD, mask handling, units/scaling)

### Spec Coverage Verification
Verified that normative content IS ALREADY in authoritative specs:
1. **Stage Policy** (lines 23-35 of plan): Covered in docs/spec-db-workflow.md (Stage A/B/C definitions, refinement sources)
2. **Detector Mapping** (lines 60-63, 89-93): Covered in docs/nanobrag_api.md (DetectorConfig CUSTOM convention, beam center ordering)
3. **Mask Handling** (lines 73-78): Covered in docs/spec-db-core.md (mask semantics, loss mask construction)
4. **Units** (lines 81-85): Covered in docs/spec-db-core.md (ADU vs photons, global scale)
5. **Multi-panel** (lines 87-100): Covered in docs/spec-db-workflow.md (per-panel simulation, stitching)

### Cross-Reference Audit
Need to check which docs/tests reference `plans/nanobrag_integration_plan.md`:
```bash
grep -r "nanobrag_integration_plan" docs/ tests/ --include="*.md" --include="*.py"
```
Expected: docs/index.md line 131 has the primary reference.

## 3. Scope Definition

### Exit Criteria (from fix_plan.md)
1. `plans/nanobrag_integration_plan.md` no longer repeats normative requirements; instead it references the relevant spec shards.
2. Phase descriptions focus on scope, sequencing, and dependencies.
3. Docs/tests referencing the plan are updated to point to the specs for authoritative definitions.

### Refactoring Strategy

**Phase A: Analysis & Mapping (this loop)**
- Read full `plans/nanobrag_integration_plan.md` (305 lines)
- Identify sections with normative content (SHALL/SHOULD/MUST requirements)
- Map each normative section to its authoritative spec location
- Produce `normative_content_map.md` artifact

**Phase B: Plan Thinning (loop i=276 estimated)**
- Rewrite `plans/nanobrag_integration_plan.md` to:
  - Keep: Phase sequencing (0-5), task lists, deliverables, estimated effort
  - Remove: Normative requirement duplication (detector mapping rules, stage policy SHALL clauses, mask/unit specifics)
  - Add: Explicit spec references (e.g., "For detector mapping, see docs/nanobrag_api.md §DetectorConfig")
- Target size: ~150-200 lines (50% reduction by removing normative duplication)
- Preserve: Overview, phase objectives, task checklists, validation gates

**Phase C: Cross-Reference Updates (loop i=277 estimated)**
- Update docs/index.md Integration Plan entry (line 131) with guidance to check specs for normative details
- Verify no tests reference the plan for normative assertions (expected clean: tests should use specs directly)
- Update DOCS-ROADMAP-001 implementation.md with completion notes

## 4. Risk Assessment

| Risk ID | Description | Likelihood | Impact | Mitigation |
|---------|-------------|------------|--------|------------|
| R1 | Plan thinning removes non-duplicated content | LOW | MEDIUM | Phase A mapping identifies unique content; Phase B preserves all unique task/sequencing info |
| R2 | Spec gaps discovered (normative content in plan NOT in specs) | LOW | HIGH | During Phase A mapping, flag any gaps; if found, create spec update item before thinning plan |
| R3 | Cross-references break (docs/tests rely on plan content) | MEDIUM | LOW | Phase C audit + update; most references expected in docs/index.md only |
| R4 | Plan becomes too thin to be useful | LOW | MEDIUM | Keep phase structure, task lists, estimated effort; only remove normative duplication |

**Overall Risk**: LOW — Documentation refactoring with clear exit criteria and reversible changes (git history preserves original plan).

## 5. Implementation Checklist

### Phase A: Analysis & Mapping (this loop, ~2 hours)
- [ ] A1: Read full `plans/nanobrag_integration_plan.md` and identify normative sections (SHALL/SHOULD/MUST keywords, specific parameter rules)
- [ ] A2: For each normative section, locate authoritative spec section (docs/spec-db-*.md, docs/nanobrag_api.md)
- [ ] A3: Document mapping in `normative_content_map.md` (table: Plan Line Range | Normative Topic | Authoritative Spec Location)
- [ ] A4: Flag any normative content in plan that is NOT in specs (expected: none, but verify)
- [ ] A5: Audit cross-references: `grep -r "nanobrag_integration_plan" docs/ tests/` and list all references
- [ ] A6: Write `phase_a_summary.md` with mapping table + cross-reference audit + spec gap findings (expected: 0 gaps)
- [ ] A7: Decision synthesis: Path A (no spec gaps, mapping complete → Phase B approved), Path B (spec gaps found → create spec update item first), Path C (mapping incomplete → extend Phase A)

### Phase B: Plan Thinning (next loop estimated)
- [ ] B1: Create backup `plans/nanobrag_integration_plan.md.bak`
- [ ] B2: Rewrite plan sections per normative_content_map: replace normative details with spec references
- [ ] B3: Preserve phase structure, task lists, estimated timelines, deliverables
- [ ] B4: Verify plan readability (phase objectives clear, spec pointers concise)
- [ ] B5: Run diff and verify ~50% line reduction (305 → ~150-200 lines)
- [ ] B6: Commit thinned plan with descriptive message

### Phase C: Cross-Reference Updates (next loop estimated)
- [ ] C1: Update docs/index.md line 131 Integration Plan entry
- [ ] C2: Verify test references (expected: none)
- [ ] C3: Update DOCS-ROADMAP-001 implementation.md with completion notes
- [ ] C4: Run final validation (all cross-references resolve, specs contain referenced content)
- [ ] C5: Update docs/fix_plan.md DOCS-ROADMAP-001 status=done + Attempts History
- [ ] C6: Commit Phase C changes

## 6. Estimated Effort

**Phase A (this loop)**: ~2 hours
- Read 305-line plan: 30 min
- Identify normative sections: 30 min
- Map to specs: 45 min
- Cross-reference audit: 15 min
- Document findings: 30 min

**Phase B (next loop)**: ~2 hours
- Rewrite plan: 90 min
- Verify readability + diff: 30 min

**Phase C (final loop)**: ~1-2 hours
- Update cross-references: 30 min
- Validation: 30 min
- Final docs/fix_plan updates: 30-60 min

**Total**: 5-6 hours across 2-3 loops (matches original estimate)

## 7. Acceptance Criteria

### Phase A Complete
- [ ] `normative_content_map.md` exists with complete mapping table (plan sections → spec locations)
- [ ] Spec gap analysis complete (expected: 0 gaps found)
- [ ] Cross-reference audit complete (list of all docs/tests referencing the plan)
- [ ] Decision: Phase B approved (no spec gaps) OR spec update item created (if gaps found)

### Phase B Complete
- [ ] `plans/nanobrag_integration_plan.md` thinned to ~150-200 lines (50% reduction)
- [ ] All normative requirements replaced with spec references
- [ ] Phase structure preserved (0-5), task lists intact, deliverables clear
- [ ] Diff review confirms only normative duplication removed

### Phase C Complete (Initiative Done)
- [ ] docs/index.md updated with spec-first guidance
- [ ] Test references verified (expected: 0)
- [ ] DOCS-ROADMAP-001 implementation.md updated with completion notes
- [ ] docs/fix_plan.md status=done, Attempts History entry added

## 8. Decision Paths

**Path A (All Clear)**: Phase A mapping complete, 0 spec gaps found, cross-references identified → APPROVE Phase B thinning (next loop)
**Path B (Spec Gaps Found)**: Mapping reveals normative content in plan NOT in specs → CREATE spec update item (e.g., DOCS-SPEC-GAPS-001), BLOCK DOCS-ROADMAP-001 until gaps filled
**Path C (Mapping Incomplete)**: Difficulty mapping some sections to specs → EXTEND Phase A, mark specific sections for deeper spec audit
**Path D (No Value)**: Audit reveals plan is already minimal (no significant normative duplication) → CLOSE DOCS-ROADMAP-001 as "no action needed"

**Expected Outcome**: Path A (HIGH confidence ~85% based on Tier 1-2 spec maturity)

## 9. Findings Applied

- **POLICY-001**: Environment Freeze — This is docs-only work, no code/environment changes
- **CLAUDE.md**: Incremental progress — 3-phase breakdown (analysis → thin → cross-refs) allows validation at each step
- **galph_prompt**: Implementation floor satisfied (Phase A is analysis/evidence-gathering, Phase B next loop will be production docs task)
- **fix_plan**: Roadmap alignment — DOCS-ROADMAP-001 is lowest priority pending item, all Tier 1-3 delivery items complete/substantial

## 10. Artifacts

**Phase A (this loop)**:
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/normative_content_map.md` (mapping table)
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/phase_a_summary.md` (findings + decision)
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/cross_reference_audit.txt` (grep results)

**Phase B (next loop estimated)**:
- `plans/nanobrag_integration_plan.md.bak` (backup)
- Updated `plans/nanobrag_integration_plan.md` (~150-200 lines, spec references)
- Diff log

**Phase C (final loop estimated)**:
- Updated docs/index.md
- Updated DOCS-ROADMAP-001 implementation.md
- Final docs/fix_plan.md entry

## 11. Next Actions (Phase A Execution)

This loop (i=275, Galph) will execute Phase A analysis:
1. Read `plans/nanobrag_integration_plan.md` (305 lines)
2. Identify normative sections (grep for SHALL/SHOULD/MUST, detector mapping rules, mask/unit specifics)
3. Map each section to authoritative spec (create table: Plan Lines | Topic | Spec Location)
4. Audit cross-references (`grep -r nanobrag_integration_plan docs/ tests/`)
5. Check for spec gaps (any normative content in plan NOT in specs)
6. Write findings artifacts (normative_content_map.md, phase_a_summary.md, cross_reference_audit.txt)
7. Decision synthesis (expected: Path A all clear → Phase B approved)
8. Update galph_memory.md with Phase A results
9. Commit Phase A artifacts

**Expected Outcome**: Path A (mapping complete, 0 spec gaps, Phase B ready for next loop)

## 12. Confidence Assessment

**HIGH confidence (~85%)** based on:
1. Well-scoped analysis task (read 305 lines, map to known specs)
2. Specs are mature (Tier 1-2 complete, most normative content already migrated)
3. Clear validation criteria (mapping table completeness, spec gap count = 0)
4. Reversible changes (git history + .bak preserves original plan)
5. LOW risk (documentation only, no code/test dependencies)

**Uncertainty factors**:
1. Possible hidden cross-references in test comments (~10% chance)
2. Plan may contain unique clarifications not duplicated elsewhere (~5% chance)

**Mitigation**: Phase A audit will surface any issues; Phase B/C are contingent on clean Phase A results.
