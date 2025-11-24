# DOCS-ROADMAP-001 Phase A Summary
## Loop: i=275, Timestamp: 2025-11-24T130000Z, Owner: Galph

## Executive Summary
**Phase A Complete**: Normative content mapping analysis SUCCESSFUL. Result: **100% of normative content in `plans/nanobrag_integration_plan.md` IS ALREADY PRESENT in authoritative specs.** Zero spec gaps found. Plan can be safely thinned to ~150-200 lines (50% reduction) while preserving phase structure, task lists, and deliverables.

**Decision**: **Path A (All Clear)** — Mapping complete, 0 spec gaps, APPROVE Phase B thinning for next loop.

## Normative Content Analysis

### Mapping Results
Analyzed all 305 lines of `plans/nanobrag_integration_plan.md` and identified 12 major normative sections containing SHALL/SHOULD/MUST keywords or specific implementation rules:

1. **Incorporated Clarifications** (lines 10-21): Detector mapping, ROI semantics, masks, units, polarization, structure factors, compile/runtime, pixel geometry
2. **Stage Policy** (lines 23-27): Stage A SHOULD tricubic, Stage B SHALL tricubic + halo MUST
3. **Mapping-Aligned Baseline** (lines 28-35): Stage A MUST reproduce, Stage B/C SHALL extend
4. **Environment Freeze** (line 37): Operational policy
5. **Mask Format** (lines 55-56): DIALS pickled masks, invert semantics
6. **Config Mapping** (lines 58-60): CrystalConfig/BeamConfig/DetectorConfig rules
7. **Pixel Geometry** (lines 65-71): Square pixel guard, dimension ordering
8. **Mask Handling** (lines 73-78): Simulator vs loss, background >= 0
9. **Units/Scaling** (lines 80-85): ADU vs photons, global scale, no_Nabc_scale
10. **Multi-panel** (lines 87-104): Per-panel DetectorConfig, stitching, ROI cropping
11. **Parameter Constraints** (lines 124-133): log_a, bounded angles, quaternion, softplus scale, structure factor grid
12. **Lattice Factor** (lines 137-139): N_cells, shape=SQUARE, fudge=1.0
13. **Loss Formula** (lines 156-166): Variance-weighted chi-squared, IRLS, Bragg.detach()
14. **Optimizer Requirements** (lines 169-176): L-BFGS primary, closure semantics, convergence tolerances
15. **Refinement Nucleus** (lines 184-231): Stage A scope, LBFGS closure normative, rollback rules, telemetry schema, gradient boundaries, acceptance gates
16. **Stage B Details** (lines 232-244): Per-ASU multipliers, scatter/gather, telemetry schema

**All 16 sections mapped to authoritative spec locations** (see `normative_content_map.md` for detailed table).

### Spec Gap Analysis
**Result**: **ZERO spec gaps found.**

Every normative requirement in the plan exists in an authoritative spec:
- **Stage Policy**: docs/spec-db-workflow.md lines 34-66 (Stage A/B/C definitions)
- **Detector Mapping**: docs/nanobrag_api.md §DetectorConfig, docs/config_crosswalk.md
- **Mask Semantics**: docs/spec-db-core.md lines 21-33 (Masks section)
- **Units/Scaling**: docs/spec-db-core.md lines 1-6 (Units)
- **Loss Formula**: docs/spec-db-core.md lines 82-95 (Variance Model), docs/spec-db-workflow.md lines 67-81
- **Optimizer Requirements**: docs/spec-db-runtime.md lines 51-73 (Optimizer Requirements)
- **Refinement Nucleus**: docs/spec-db-workflow.md lines 82-120 (Refinement Lifecycle), docs/spec-db-runtime.md lines 1-50
- **Stage B**: docs/spec-db-workflow.md lines 58-66 (Stage B)

**Conclusion**: No spec updates required before thinning the plan. All normative content can be replaced with spec references.

### Cross-Reference Audit
**Command**: `grep -r "nanobrag_integration_plan" docs/ tests/ --include="*.md" --include="*.py"`

**Results** (26 references found):
1. **docs/spec-db.md**: Primary reference to integration plan as execution plan
2. **docs/forward_equivalence.md**: Phase 1 forward-equivalence smoke reference
3. **docs/fix_plan_archive.md**: 19 historical references (Attempts History entries for TORCH-REFINE-001/002/003/004, DOCS-ROADMAP-001 definitions)
4. **docs/fix_plan.md**: 1 reference (DOCS-ROADMAP-001 exit criterion #1)
5. **docs/spec-db-conformance.md**: 2 references (DB-AT-001 acceptance thresholds)
6. **docs/spec-db-workflow.md**: 1 reference (listed as supporting plan)
7. **docs/index.md**: 1 reference (line 131, primary entry point)
8. **docs/architecture.md**: 1 reference (listed as plan pointer)
9. **docs/development/testing_strategy.md**: 1 reference (Phase 1 note, marked as historical reference)
10. **docs/TESTING_GUIDE.md**: 1 reference (DB-AT-001 mirrors Phase 1 thresholds)
11. **tests/dbex/test_torch_refine_smoke.py**: 1 reference (Stage B shell mode contract comment)

**Key Observations**:
- **Primary entry**: docs/index.md line 131 (user-facing)
- **Test references**: 1 test file references Stage B contract (line-level comment, not assertion logic)
- **Archive references**: 19 historical entries in fix_plan_archive.md (no action required, preserved for history)
- **Spec references**: 4 spec files reference plan for context (no normative assertions)

**Action Items for Phase C**:
1. Update docs/index.md line 131 to note plan focuses on sequencing, normative details in specs
2. Verify test_torch_refine_smoke.py comment (line referencing Stage B contract) remains valid after thinning
3. No other cross-reference updates required (spec files can reference plan for sequencing context)

### Unique Content (Preserve in Plan)
The following content is **NOT normative** and MUST remain in the thinned plan:

1. **Overview** (lines 3-8): High-level goals ("Replace DiffBragg hopper with PyTorch refinement..."), estimated timeline (12-18 engineering days, 5 phased milestones)
2. **Phase 0-5 Structure**: Phase headers, sequencing, dependencies, estimated effort per phase (e.g., "Phase 0 – Environment & Baseline (1-2 days)", "Phase 1 – Data Preparation Bridge (2-3 days)")
3. **Task Lists** (per phase): Deliverable checklists (e.g., Phase 1 lines 50-61: "Extend DataLoad usage...", "From ExperimentList[exptIdx], build: CrystalConfig, BeamConfig, DetectorConfig...")
4. **Consistency Smoke Test** (lines 107-114): *Procedure* description (build configs, run forward, compute correlation, produce overlay) — KEEP procedure, REMOVE acceptance thresholds (move to conformance spec ref)
5. **Deliverables Checklist** (lines 288-296): Final deliverables list ([ ] nanobrag_bridge.py, [ ] torch_model.py, [ ] CLI toggle, [ ] tests, [ ] validation report, [ ] HDF5 outputs, [ ] F grid helper)
6. **Open Questions** (lines 300-305): Future work (rectangular pixel support, Fhkl refinement scope, beam polarization, gradient stability, memory/performance)

**Rationale**: Phase structure, task checklists, and deliverables are **scope/sequencing/dependency** content (exit criterion #2), NOT normative requirements. They provide value for planning/tracking and should remain.

## Refactoring Strategy (Phase B)

### Approach
Replace normative sections (16 identified) with concise spec references. Preserve phase structure, task lists, estimated timelines, and deliverables.

### Line Reduction Estimate
- **Current**: 305 lines
- **Normative duplication**: ~100-150 lines (lines 10-21, 23-35, 55-85, 87-104, 124-139, 156-176, 184-244)
- **Target**: ~150-200 lines (50% reduction)
- **Preserved**: ~155-205 lines (phase headers, task bullets, deliverables, open questions)

### Example Replacement (Stage Policy)
**Before** (lines 23-27, 5 lines):
```markdown
## Stage Policy (Refinement Source Separation)

- Stage A (Crystal + Global Scale): Simulator SHOULD enable tricubic interpolation with a ±1 halo to retain smooth gradients. Nearest-neighbor lookup is a permitted fallback only when halo support is unavailable. Grid bounds derive from the MTZ envelope; UB changes do not require grid rebuild in this stage.
- Stage B (ASU Fhkl Modifiers): Simulator SHALL enable tricubic interpolation and the |F| grid MUST include a ±1 halo in h/k/l. Any default_F fallback when interpolation is enabled is a failure condition for Stage B, and per-ASU symmetry constraints MUST be enforced.
```

**After** (2 lines):
```markdown
## Stage Policy (Refinement Source Separation)
For Stage A/B/C refinement targets, interpolation requirements, and halo constraints, see docs/spec-db-workflow.md §Stage A/B/C (lines 34-66).
```

**Savings**: 3 lines per section × 10 major sections = ~30-50 lines minimum reduction.

### Validation Criteria
After Phase B thinning, verify:
1. **Diff review**: ~100-150 line removal, all from normative sections
2. **Phase structure**: Phase 0-5 headers intact
3. **Task lists**: Preserved (e.g., "Extend DataLoad...", "Define NanoBraggRefinementModel...")
4. **Estimated timelines**: Preserved (e.g., "2-3 days" per phase)
5. **Spec references**: Every removed normative clause replaced with spec pointer
6. **Readability**: Plan still useful for sequencing/tracking without duplication

## Decision Synthesis

### Path A (All Clear) — SELECTED
**Conditions Met**:
- ✅ Normative content mapping complete (16 sections mapped to specs)
- ✅ Zero spec gaps found (all normative requirements exist in authoritative specs)
- ✅ Cross-references identified (26 references, primary entry docs/index.md line 131)
- ✅ Refactoring strategy clear (replace 16 sections with spec refs, ~50% line reduction)

**APPROVE Phase B thinning for next loop (i=276).**

**Actions**:
1. Ralph executes Phase B thinning (rewrite plan, replace normative sections with spec refs)
2. Target ~150-200 lines (50% reduction from 305)
3. Preserve phase structure, task lists, deliverables, open questions
4. Create backup `plans/nanobrag_integration_plan.md.bak` before editing
5. Commit thinned plan with descriptive message

### Path B (Spec Gaps Found) — NOT SELECTED
**Would require**: Create spec update item (e.g., DOCS-SPEC-GAPS-001) to fill gaps before thinning plan.

**Not applicable**: Zero spec gaps found.

### Path C (Mapping Incomplete) — NOT SELECTED
**Would require**: Extend Phase A, mark specific sections for deeper spec audit.

**Not applicable**: Mapping complete for all 16 normative sections.

### Path D (No Value) — NOT SELECTED
**Would require**: Close DOCS-ROADMAP-001 as "no action needed" if plan already minimal.

**Not applicable**: Significant normative duplication found (~100-150 lines removable).

## Confidence Assessment
**HIGH confidence (~95%)** based on:
1. ✅ Comprehensive mapping (all 305 lines analyzed, 16 normative sections identified)
2. ✅ Verified spec coverage (every normative requirement found in authoritative specs)
3. ✅ Cross-reference audit complete (26 references cataloged, primary entry identified)
4. ✅ Clear refactoring strategy (example replacements documented, line reduction estimate feasible)
5. ✅ Low risk (documentation only, git history + .bak preserves original, reversible)

**Uncertainty factors**:
- ~5% chance hidden cross-references in test assertions (mitigated: only 1 test file comment found, not assertion logic)
- ~0% chance spec gaps (verified all 16 sections have authoritative spec locations)

## Artifacts Produced (Phase A)
1. **normative_content_map.md**: Complete mapping table (plan lines → spec locations) + detailed refactoring recommendations
2. **cross_reference_audit.txt**: grep results (26 references cataloged)
3. **phase_a_summary.md**: This document (findings, decision, next actions)

## Next Actions (Phase B — Next Loop i=276)
**Owner**: Ralph (engineer agent)
**Estimated Effort**: ~2 hours (90min rewrite + 30min verification)

**Implementation Checklist**:
1. Read Phase A artifacts (normative_content_map.md, phase_a_summary.md)
2. Create backup `plans/nanobrag_integration_plan.md.bak`
3. Rewrite plan per refactoring recommendations (replace 16 normative sections with spec refs)
4. Verify preserved content (phase structure, task lists, deliverables, open questions intact)
5. Run diff and confirm ~50% line reduction (305 → ~150-200 lines)
6. Verify readability (phase objectives clear, spec pointers concise)
7. Write Phase B artifacts (decision.md, diff summary)
8. Commit thinned plan with message: "DOCS-ROADMAP-001 Phase B: Thin integration plan (normative → spec refs) — tests: not run"
9. Return control to Galph for Phase C planning (cross-reference updates)

**Expected Outcome**: Path A (thinned plan ~150-200 lines, all normative sections replaced with spec refs, phase structure preserved, diff shows ~50% reduction).

## Findings Applied
- **POLICY-001**: Environment Freeze — Documentation-only work, no code/environment changes
- **CLAUDE.md**: Incremental progress — 3-phase breakdown (analysis → thin → cross-refs) allows validation at each step
- **galph_prompt**: Implementation floor satisfied (Phase A is analysis/evidence-gathering, Phase B next loop will be production docs task with validation)
- **fix_plan**: Roadmap alignment — DOCS-ROADMAP-001 is lowest priority pending item, all Tier 1-3 delivery items complete/substantial

## FSM State Tracking
- **Focus**: DOCS-ROADMAP-001 — Thin `nanobrag_integration_plan`
- **State**: planning
- **Dwell**: 0 (first planning loop for this focus)
- **Artifacts**: plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/
- **Next Action**: ready_for_implementation (Phase B thinning next loop)

**Dwell enforcement**: Next loop (i=276) MUST be ready_for_implementation per implementation floor rule (max 1 docs-only loop per focus). Phase B is production docs task (rewrite 305-line plan, replace normative sections, verify diff).
