# Implementation Plan: DOCS-ROADMAP-001
## Thin `nanobrag_integration_plan` to Reference Specs

**Status**: in_progress (Phase A complete 2025-11-24T130000Z, Phase B next)
**Owner**: Galph (planning) / Ralph (implementation)
**Estimated Effort**: 2-3 loops (~5-6 hours: Phase A analysis 2h, Phase B thin 2h, Phase C cross-refs 1-2h)

## Objective
Remove normative requirement duplication from `plans/nanobrag_integration_plan.md` by replacing SHALL/SHOULD/MUST clauses with references to authoritative specs, while preserving phase structure, task lists, and deliverables.

## Exit Criteria
1. `plans/nanobrag_integration_plan.md` no longer repeats normative requirements; instead it references the relevant spec shards.
2. Phase descriptions focus on scope, sequencing, and dependencies.
3. Docs/tests referencing the plan are updated to point to the specs for authoritative definitions.

## Dependencies
- docs/spec-db-workflow.md (Stage A/B/C definitions)
- docs/spec-db-core.md (units, masks, variance, parameterization)
- docs/nanobrag_api.md (detector config mapping)
- docs/config_crosswalk.md (DIALS → simulator config mapping)

**Status**: All dependencies satisfied (Tier 1-2 complete, specs mature)

## Phases

### Phase A: Analysis & Mapping ✅ COMPLETE (2025-11-24T130000Z)
**Objective**: Map normative content in integration plan to authoritative spec locations and verify no spec gaps.

**Status**: ✅ COMPLETE
- [x] A1: Read full integration plan (305 lines)
- [x] A2: Identify normative sections (16 sections with SHALL/SHOULD/MUST or specific implementation rules)
- [x] A3: Map each section to authoritative spec (complete table in normative_content_map.md)
- [x] A4: Flag spec gaps (RESULT: 0 gaps found, all normative content exists in specs)
- [x] A5: Audit cross-references (26 references found, cataloged in cross_reference_audit.txt)
- [x] A6: Write findings artifacts (normative_content_map.md, phase_a_summary.md, cross_reference_audit.txt)
- [x] A7: Decision synthesis (Path A: all clear, Phase B approved)

**Outcome**: Mapping complete, 0 spec gaps, 100% duplication confirmed, refactoring strategy documented.

**Artifacts**: plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/
- normative_content_map.md (complete mapping table + refactoring recommendations)
- phase_a_summary.md (findings + decision + next actions)
- cross_reference_audit.txt (26 references cataloged)
- planning_analysis.md (Phase A-C scope + risk assessment)

### Phase B: Plan Thinning (pending — next loop i=276)
**Objective**: Rewrite integration plan to remove normative duplication and replace with spec references.

**Tasks**:
- [ ] B1: Create backup `plans/nanobrag_integration_plan.md.bak`
- [ ] B2: Rewrite plan sections per normative_content_map (replace 16 normative sections with spec references)
- [ ] B3: Preserve phase structure, task lists, estimated timelines, deliverables
- [ ] B4: Verify plan readability (phase objectives clear, spec pointers concise)
- [ ] B5: Run diff and verify ~50% line reduction (305 → ~150-200 lines)
- [ ] B6: Commit thinned plan with descriptive message

**Validation**:
- Diff shows ~100-150 line removal (all from normative sections)
- Phase 0-5 headers intact
- Task lists preserved (e.g., "Extend DataLoad usage...")
- Estimated timelines preserved (e.g., "2-3 days" per phase)
- Every removed normative clause replaced with spec reference

**Estimated Effort**: ~2 hours (90min rewrite + 30min verification)

**Acceptance Criteria**:
- Target: ~150-200 lines (50% reduction from 305)
- All normative sections (lines 10-21, 23-35, 55-85, 87-104, 124-139, 156-176, 184-244) replaced with spec refs
- Phase structure preserved (Overview, Phase 0-5, Deliverables Checklist, Open Questions)
- Diff shows no changes to task lists or estimated timelines

### Phase C: Cross-Reference Updates (pending — loop i=277 estimated)
**Objective**: Update docs/tests referencing the plan to clarify scope (sequencing/planning) vs normative content (specs).

**Tasks**:
- [ ] C1: Update docs/index.md line 131 Integration Plan entry with guidance to check specs for normative details
- [ ] C2: Verify test references (expected: only 1 comment in test_torch_refine_smoke.py, not assertion logic)
- [ ] C3: Update DOCS-ROADMAP-001 implementation.md with completion notes
- [ ] C4: Run final validation (all cross-references resolve, specs contain referenced content)
- [ ] C5: Update docs/fix_plan.md DOCS-ROADMAP-001 status=done + Attempts History entry
- [ ] C6: Commit Phase C changes

**Validation**:
- docs/index.md updated (spec-first guidance added)
- Test references verified (1 comment, no assertion changes needed)
- All cross-references resolve correctly

**Estimated Effort**: ~1-2 hours (30min cross-ref updates + 30min validation + 30-60min final docs/fix_plan updates)

**Acceptance Criteria** (Initiative Complete):
- docs/index.md Integration Plan entry notes plan is for sequencing, specs for normative requirements
- No broken cross-references (all 26 references checked)
- DOCS-ROADMAP-001 implementation.md updated with completion summary
- docs/fix_plan.md status=done with completion timestamp

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|------------|---------|
| Plan thinning removes unique content | LOW | MEDIUM | Phase A mapping identifies unique content; Phase B preserves task lists/deliverables | Mitigated (Phase A complete) |
| Spec gaps discovered | LOW | HIGH | Phase A audit found 0 gaps | Resolved (no gaps) |
| Cross-references break | MEDIUM | LOW | Phase C audit + update; most refs in docs only | Pending Phase C |
| Plan becomes too thin | LOW | MEDIUM | Keep phase structure + task checklists; only remove normative duplication | Mitigated (Phase A strategy) |

## Progress Tracking
- **Phase A**: ✅ COMPLETE (2025-11-24T130000Z)
- **Phase B**: Pending (next loop i=276)
- **Phase C**: Pending (loop i=277 estimated)
- **Exit Criteria**: 0/3 satisfied (Phase B/C pending)

## Notes
- **Environment Freeze**: Documentation-only work, no code/environment changes
- **Incremental Progress**: 3-phase breakdown allows validation at each step
- **Implementation Floor**: Phase A analysis, Phase B production docs task (rewrite plan)
- **Confidence**: HIGH (~95%) based on comprehensive Phase A analysis
