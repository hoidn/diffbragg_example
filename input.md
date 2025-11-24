# DOCS-ROADMAP-001 Phase B: Plan Thinning

## Summary
Rewrite `plans/nanobrag_integration_plan.md` to remove normative requirement duplication (~100-150 lines) and replace with spec references, while preserving phase structure, task lists, and deliverables. Target ~150-200 lines (50% reduction from 305).

## Mode
Docs

## Focus
DOCS-ROADMAP-001 — Thin `nanobrag_integration_plan`

## Branch
integration

## Mapped Tests
none — documentation-only (no test selectors)

## Artifacts
`plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/` (create this timestamp directory for Phase B)
- `plans/nanobrag_integration_plan.md.bak` (backup before editing)
- `diff_summary.txt` (diff output showing line reduction)
- `decision.json` (Path A/B/C/D decision + validation results)
- `summary.md` (Turn Summary)

## Do Now

**Phase B: Plan Thinning (Rewrite Integration Plan)**

Replace 16 normative sections identified in Phase A with concise spec references. Follow `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/normative_content_map.md` refactoring recommendations.

### Implementation Checklist

1. **Read Phase A artifacts** (~10min)
   - Read `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/normative_content_map.md` (mapping table + refactoring recommendations)
   - Read `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/phase_a_summary.md` (findings + example replacements)

2. **Create backup** (~1min)
   - `cp plans/nanobrag_integration_plan.md plans/nanobrag_integration_plan.md.bak`

3. **Rewrite plan** (~90min)
   - Edit `plans/nanobrag_integration_plan.md` per normative_content_map refactoring recommendations (10 major replacements)
   - **Section 1 (lines 10-21)**: Replace "Incorporated Clarifications" details with: "For detector config mapping, masks, units, and ROI semantics, see docs/nanobrag_api.md, docs/spec-db-core.md, and docs/dials_api.md."
   - **Section 2 (lines 23-27)**: Replace "Stage Policy" SHALL/SHOULD clauses with: "Stage refinement targets and interpolation requirements are defined in docs/spec-db-workflow.md §Stage A/B/C (lines 34-66)."
   - **Section 3 (lines 28-35)**: Replace "Mapping-Aligned Baseline" MUST clauses with: "For mapping parity requirements and Stage A zero-point conventions, see docs/spec-db-conformance.md (DB-AT-024) and docs/spec-db-workflow.md §Baseline Convention (lines 29-32)."
   - **Section 4 (lines 55-61)**: Replace config mapping rules with: "Config construction from DIALS Experiment metadata is documented in docs/config_crosswalk.md and docs/nanobrag_api.md."
   - **Section 5 (lines 65-85)**: Replace pixel geometry/masks/units details with: "For pixel geometry constraints, mask handling, and unit conventions, see docs/spec-db-core.md."
   - **Section 6 (lines 87-104)**: Replace multi-panel code snippet with: "Multi-panel simulation and stitching workflow is specified in docs/spec-db-workflow.md §Per-Panel Simulation (lines 13-16)."
   - **Section 7 (lines 124-139)**: Replace parameter constraints details with: "Parameter constraints and baseline crystal state are defined in docs/spec-db-core.md §Baseline Crystal State and Parameterization (lines 34-57)."
   - **Section 8 (lines 156-176)**: Replace loss formula/optimizer details with: "Variance-weighted loss definition and optimizer requirements are specified in docs/spec-db-core.md §Variance Model (lines 82-95) and docs/spec-db-runtime.md §Optimizer Requirements (lines 51-73)."
   - **Section 9 (lines 184-231)**: Replace refinement nucleus contract with: "Refinement lifecycle, convergence gates, and telemetry schema are defined in docs/spec-db-workflow.md §Refinement Lifecycle (lines 82-120) and docs/spec-db-runtime.md."
   - **Section 10 (lines 232-244)**: Replace Stage B specifics with: "Stage B structure-factor refinement implementation is specified in docs/spec-db-workflow.md §Stage B (lines 58-66)."
   - **Preserve**: Overview (lines 3-8), Phase 0-5 headers, task lists (e.g., lines 50-61 Phase 1 tasks), estimated timelines, Deliverables Checklist (lines 288-296), Open Questions (lines 300-305)

4. **Verify preserved content** (~15min)
   - Check Phase 0-5 headers intact (grep "## Phase" plans/nanobrag_integration_plan.md)
   - Check task lists preserved (grep "^- " plans/nanobrag_integration_plan.md | wc -l should show similar count)
   - Check estimated timelines preserved (grep "days" plans/nanobrag_integration_plan.md)
   - Check Deliverables Checklist intact (lines 288-296)

5. **Run diff and verify line reduction** (~10min)
   - `diff -u plans/nanobrag_integration_plan.md.bak plans/nanobrag_integration_plan.md > plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/diff_summary.txt`
   - `wc -l plans/nanobrag_integration_plan.md` → should be ~150-200 lines (target 50% reduction from 305)
   - Verify diff shows ~100-150 line removal (all from normative sections, not task lists)

6. **Verify readability** (~10min)
   - Read through thinned plan end-to-end
   - Verify phase objectives clear (Overview + Phase 0-5 headers)
   - Verify spec pointers concise (e.g., "see docs/spec-db-workflow.md §Stage A")
   - Verify no broken markdown formatting

7. **Write decision.json** (~5min)
   - Document which decision path (A/B/C/D) based on validation results
   - Path A (ideal): Line reduction ~50%, phase structure preserved, all spec refs valid
   - Path B (partial): Line reduction <40%, need additional thinning
   - Path C (issue): Phase structure damaged, need to restore
   - Path D (blocker): Cannot complete thinning, escalate to Galph

8. **Write summary.md** (~5min)
   - Create `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/summary.md`
   - Include Turn Summary with: line reduction achieved, sections replaced, validation results, next actions (Phase C cross-refs)

9. **Commit** (~5min)
   - `git add plans/nanobrag_integration_plan.md plans/active/DOCS-ROADMAP-001/`
   - `git commit -m "DOCS-ROADMAP-001 Phase B: Thin integration plan (normative → spec refs) — tests: not run"`
   - Do NOT commit `.bak` file (keep as local backup only)

10. **Return control to Galph** (~1min)
    - Ensure artifacts directory created with all required files
    - Ensure decision.json + summary.md written
    - Ensure commit pushed (not required this loop, Galph will handle)

## How-To Map

### Environment
```bash
# No special environment setup required (documentation-only)
pwd  # Should be /home/ollie/Documents/diffbragg_example
```

### Commands

1. **Phase A artifact review**:
```bash
ls -lh plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/
cat plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/normative_content_map.md
```

2. **Backup plan**:
```bash
cp plans/nanobrag_integration_plan.md plans/nanobrag_integration_plan.md.bak
```

3. **Edit plan** (manual):
   - Use your text editor to apply 10 replacements per normative_content_map.md
   - Replace normative sections (lines 10-21, 23-35, 55-85, 87-104, 124-139, 156-176, 184-244) with concise spec references
   - Preserve phase structure, task lists, timelines, deliverables, open questions

4. **Diff and line count**:
```bash
mkdir -p plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z
diff -u plans/nanobrag_integration_plan.md.bak plans/nanobrag_integration_plan.md > plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/diff_summary.txt
wc -l plans/nanobrag_integration_plan.md  # Target ~150-200 lines
grep "^-" plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/diff_summary.txt | wc -l  # Should show ~100-150 lines removed
```

5. **Verification checks**:
```bash
grep "## Phase" plans/nanobrag_integration_plan.md  # Should show Phase 0-5 headers
grep "^- " plans/nanobrag_integration_plan.md | wc -l  # Task list count (should be similar to original)
grep "days" plans/nanobrag_integration_plan.md  # Verify timelines preserved
```

6. **Commit**:
```bash
git add plans/nanobrag_integration_plan.md plans/active/DOCS-ROADMAP-001/
git commit -m "DOCS-ROADMAP-001 Phase B: Thin integration plan (normative → spec refs) — tests: not run"
# Note: Do NOT add .bak file to git
```

## Pitfalls To Avoid

1. **Do NOT remove task lists** — Phase 1-5 task bullets (e.g., "Extend DataLoad usage...", "Define NanoBraggRefinementModel...") are NOT normative, they are deliverable checklists. KEEP them.
2. **Do NOT remove phase headers** — "Phase 0 – Environment & Baseline", "Phase 1 – Data Preparation Bridge", etc. are sequencing structure. KEEP them.
3. **Do NOT remove estimated timelines** — "1-2 days", "2-3 days" per phase are planning estimates. KEEP them.
4. **Do NOT remove Deliverables Checklist** — Lines 288-296 list final deliverables ([ ] nanobrag_bridge.py, [ ] torch_model.py, etc.). KEEP them.
5. **Do NOT remove Open Questions** — Lines 300-305 list future work. KEEP them.
6. **Do NOT add new normative content** — You are REMOVING normative duplication, not rewriting requirements. Only add spec references.
7. **Do NOT change spec references** — Use exact spec pointers from normative_content_map.md (e.g., "docs/spec-db-workflow.md §Stage A/B/C (lines 34-66)").
8. **Do NOT skip backup** — Always create .bak before editing in case you need to revert.
9. **Do NOT commit .bak file** — Keep it as local backup only, do not add to git.
10. **Do NOT create new files** — Only edit existing `plans/nanobrag_integration_plan.md` and create artifacts under `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T145000Z/`.

## If Blocked

If you cannot complete Phase B thinning:
1. Document the blocker in `decision.json` (Path D)
2. Preserve any partial progress (commit partial work with clear message)
3. Write `summary.md` explaining what was attempted and why it failed
4. Return control to Galph with blocker documented

Example blockers:
- Cannot parse normative_content_map.md (formatting issue)
- Cannot determine what to preserve vs remove (ambiguous section)
- Diff shows phase structure was damaged (need to restore from .bak)
- Line reduction <30% (insufficient thinning, need Galph guidance)

## Findings Applied

**Mandatory Reading**:
- POLICY-001: Environment Freeze — Documentation-only work, no code/environment changes
- TESTING-003: Test registry sync NOT required for documentation-only changes
- CLAUDE.md: Incremental progress — 3-phase breakdown (analysis → thin → cross-refs)

**Relevant Phase A Results**:
- 100% normative content duplication confirmed (all 16 sections exist in authoritative specs)
- Zero spec gaps found (no spec updates required before thinning)
- 26 cross-references cataloged (will be updated in Phase C)
- Target line reduction: 305 → ~150-200 lines (50%)

## Pointers

**Phase A Artifacts** (mandatory reading):
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/normative_content_map.md` — Detailed mapping table + refactoring recommendations
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/phase_a_summary.md` — Findings + example replacements
- `plans/active/DOCS-ROADMAP-001/reports/2025-11-24T130000Z/phase_a_summary.md:48-85` — Example replacement (Stage Policy section)

**Specs Referenced** (verify these exist before citing):
- docs/spec-db-workflow.md (Stage A/B/C definitions, refinement lifecycle)
- docs/spec-db-core.md (units, masks, variance, parameterization)
- docs/spec-db-runtime.md (optimizer requirements, PyTorch guardrails)
- docs/nanobrag_api.md (detector config mapping, HKL IO)
- docs/config_crosswalk.md (DIALS → simulator config mapping)
- docs/spec-db-conformance.md (DB-AT-024 mapping parity)

**Target File**:
- `plans/nanobrag_integration_plan.md` — 305 lines currently, target ~150-200 lines after thinning

**Implementation Plan**:
- `plans/active/DOCS-ROADMAP-001/implementation.md` — Phase A ✅ COMPLETE, Phase B checklist (lines 46-70)

## Next Up (Optional)
If Phase B completes early (<2 hours) and you have time remaining:
- Phase C task C2: Verify test references in `tests/dbex/test_torch_refine_smoke.py` (expected: 1 comment line referencing Stage B contract, no assertion changes needed)
- Document C2 result in `summary.md` (e.g., "Verified test reference: line 123 comment valid, no changes required")

Do NOT attempt Phase C tasks C1/C3/C4/C5/C6 (cross-reference updates, fix_plan updates) — those require Galph review first.

## Doc Sync Plan
Not applicable — Documentation-only changes, no test registry sync required per TESTING-003.

## Normative Math/Physics
Not applicable — This is documentation hygiene, no normative math/physics changes.
