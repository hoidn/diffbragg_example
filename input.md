# input.md — Loop 2026-01-13T150000Z → Ralph

## Summary
Switch focus from ARCH-SIM-CONSTRUCTION-001 (blocked) to ARCH-IMPL-CONFORMANCE-001 Phase A planning after documenting the omega diagnosis correction.

## Mode
Docs

## ActionType
review_or_housekeeping

## DecisionStatus
exploring

## InitiativeType
architecture

## Focus
ARCH-IMPL-CONFORMANCE-001 — Architecture / Implementation Contract Alignment

## Branch
integration

## Mapped tests
none — docs-only loop

## Artifacts
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/` (block documentation)
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/` (Phase A kickoff planning)

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (`prompts/supervisor.md::diagnostic_script_policy`): No new plan-local probes allowed; ARCH-SIM-CONSTRUCTION-001 exhausted diagnostic capacity without delivering actionable fix
- **SIM-CONSTR-PARTIALITY-001** (`docs/findings.md`): Owner path for partiality/lattice semantics lives in nanobrag_torch.simulator; cannot extend plan scripts beyond existing instrumentation
- **SCALE-008** / **SCALE-009** (`docs/findings.md`): Relevant to ARCH-IMPL-CONFORMANCE-001 contract inventory
- **ARCH-FACTORY-001** (`docs/findings.md`): Simulator factory responsibilities; relevant to ARCH-IMPL-CONFORMANCE-001 contract definitions

## Pointers
- **Spec:** `docs/spec-db-core.md` §§20–40 (simulator construction + calibration contracts)
- **Arch:** `docs/architecture/calibration_scaling.md` (scaling/calibration threading policy)
- **ARCH:** `docs/architecture/module_map.md` (module → responsibility mapping)
- **Testing:** `docs/TESTING_GUIDE.md` §1-2 (smoke/acceptance selectors, artifact policy)
- **Planning:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/summary.md` (C.38 omega instrumentation evidence)
- **Planning:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/summary.md` (Ralph's omega block)
- **Planning:** `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md` (contract alignment plan)

## ARCH Contracts (mandatory)
1. **SCALE-009** (Stage A vs reconstruction scaling):
   - **Owner**: To be determined in Phase A (candidate: canonical forward helper)
   - **Current state**: Implementation bug (deficit in raw sincg accumulation before omega)
   - **Classification**: Environment blocker (nanobrag_torch sincg behavior; cannot fix within PROBE-FREEZE-001 constraints)

2. **ARCH-FACTORY-001** (Unified simulator factory):
   - **Owner**: `dbex.nanobrag_bridge.create_unified_simulator`
   - **Current state**: Factory contract unclear re: calibration threading
   - **Classification**: Architectural contract gap (needs explicit ARCH-CONTRACT definition in ARCH-IMPL-CONFORMANCE-001)

3. **Stage A vs mapping baseline** (from ARCH-IMPL-CONFORMANCE-001 scope):
   - **Owner**: To be determined in Phase A
   - **Current state**: Unknown (not yet inventoried)
   - **Classification**: Candidate ARCH-CONTRACT for Phase A

## Do Now

### Task 1: Document ARCH-SIM-CONSTRUCTION-001 Block (Docs Mode)

1. **Update `docs/fix_plan.md` line 24** (ARCH-SIM-CONSTRUCTION-001 Tier 0 entry):
   - Change status from `in_progress` to `blocked_pending_environment`
   - Replace "Next action: edit the oversample>1 SQUARE path..." with: "**Blocked:** Omega hypothesis rejected (C.39 evidence proves deficit exists in raw subpixel sum before omega application). F_latt shows 11% of expected amplitude, but observed intensity is 9.4% of expected, suggesting sincg lattice factor computation bug in nanobrag_torch. Further instrumentation violates PROBE-FREEZE-001. Blocked pending: (a) nanobrag_torch maintainer investigation, (b) spec_change to relax DB-AT-028/029 criteria, or (c) harness-grade diagnostic initiative outside plan-local probes."
   - Update artifacts pointer: `...2026-01-13T150000Z/summary.md` (omega diagnosis correction)

2. **Append new Attempts History entry to ARCH-SIM-CONSTRUCTION-001 section** (~line 135 or in dedicated section):
   ```markdown
   * 2026-01-13T150000Z — **C.39 OMEGA HYPOTHESIS REJECTED**: Ralph correctly blocked omega compensation implementation, exposing specification contradiction. Re-analysis proved omega is a red herring: deficit of 90.60% appears in `trace_subpixel_F_total_sq_sum` (raw sum before omega) and persists identically after omega application (both base and scaled runs have omega≈1e-6, so it cancels in ratio). Root cause: per-subpixel sincg accumulation produces F_latt at 11% of expected amplitude (4206.5 vs 38,048 for N_cells=41×29×32), which squared gives 1.2% of expected intensity, yet observed is 9.4%, suggesting multiple compounding factors in sincg lattice weight computation. Phase C.34-C.38 instrumentation exhausted diagnostic capacity under PROBE-FREEZE-001 constraints. Marked **blocked_pending_environment** awaiting: (a) nanobrag_torch maintainer investigation of sincg behavior, (b) spec_change to relax DB-AT-028/029 acceptance criteria, or (c) harness-grade diagnostic initiative outside plan-local tools. Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/summary.md` (omega diagnosis correction), cross-refs to C.34-C.39 evidence.
   ```

3. **Update `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`**:
   - Mark Phase C.39 as **BLOCKED** (already done if Ralph updated it)
   - Add Phase C closure note documenting the block and evidence trail
   - No changes to earlier phases; preserve C.34-C.38 completed checkboxes

4. **Create blocking note artifact**:
   - `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/BLOCKED.md` containing:
     - Summary of C.39 omega hypothesis rejection
     - Evidence that deficit is in raw sum before omega (with numbers)
     - F_latt deficit analysis (11% amplitude → 1.2% intensity expected, but observing 9.4%)
     - PROBE-FREEZE-001 constraint preventing further instrumentation
     - Three unblock options (maintainer/spec_change/harness initiative)
     - Cross-references to C.34-C.39 reports

### Task 2: ARCH-IMPL-CONFORMANCE-001 Phase A Kickoff Planning

5. **Create `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/` directory**

6. **Create `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`**:
   - Title: "Phase A Kickoff — Contract Inventory & Reconciliation Planning"
   - Context: ARCH-SIM-CONSTRUCTION-001 blocked; switching to ARCH-IMPL-CONFORMANCE-001 to make progress on architectural contract enforcement while environment blocker is resolved
   - Scope: Phase A planning to inventory SCALE/ARCH findings, identify duplicated semantics, and propose ARCH-CONTRACT definitions for Stage A ↔ reconstruction scaling and Stage A ↔ mapping baseline
   - Next loop will be implementation_ready with Phase A.0-A.3 checklist items

7. **Review and annotate existing findings** (research only; no edits yet):
   - Read `docs/findings.md` entries for SCALE-008, SCALE-009, ARCH-FACTORY-001
   - Note any contradictions or drift vs current implementation
   - Capture notes in `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/findings_inventory.md`

8. **Identify candidate owner modules** (research only):
   - Review `dbex/refinement/stage_a.py`, `dbex/refinement/reconstruction.py`, `dbex/nanobrag_bridge.py`
   - Note which modules currently duplicate scaling/calibration logic
   - Capture module inventory in `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/module_inventory.md`

9. **Update `docs/fix_plan.md`** to reflect ARCH-IMPL-CONFORMANCE-001 focus:
   - Ensure ARCH-IMPL-CONFORMANCE-001 appears in Tier 0 section (should already be there at line ~22)
   - Add minimal Attempts History entry: "2026-01-13T150000Z — Phase A kickoff planning after ARCH-SIM-CONSTRUCTION-001 blocked. Scoped contract inventory for SCALE-008/009 + ARCH-FACTORY-001. Artifacts: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/`."

10. **Update `galph_memory.md`**:
    - Current loop entry already added; no further changes needed

## Forbidden This Loop
- **No production code edits** — Docs mode only
- **No test execution** — Research and planning only
- **No new probes** — PROBE-FREEZE-001 remains in effect
- **No ARCH-SIM-CONSTRUCTION-001 implementation work** — Initiative is blocked

## DMI Section
N/A — No DMI in this docs/planning loop

## ARCH Conformance Remediation
N/A — Phase A planning only; remediation comes in Phase B

## SYNC Closure
N/A — No SYNC mid-air detected

## How-To Map
All tasks are file operations (Read, Edit, Write for markdown docs):

1. Edit `docs/fix_plan.md` line 24 + append Attempts History entry
2. Update `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md` (Phase C.39 closure note)
3. Write `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/BLOCKED.md`
4. Create directory: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/`
5. Write `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`
6. Read `docs/findings.md` (SCALE-008/009, ARCH-FACTORY-001) → Write `findings_inventory.md`
7. Read `dbex/refinement/{stage_a.py,reconstruction.py}`, `dbex/nanobrag_bridge.py` → Write `module_inventory.md`
8. Edit `docs/fix_plan.md` (add ARCH-IMPL-CONFORMANCE-001 Attempts History entry)
9. Verify `galph_memory.md` is up-to-date (already done by supervisor)

No pytest, no compile, no environment changes.

## Pitfalls To Avoid
1. **Do not weaken acceptance criteria** — Document blocks honestly; don't adjust gates to hide problems
2. **Do not create new probes** — PROBE-FREEZE-001 forbids extending plan-local diagnostics
3. **Do not force implementation** — If blocked, document and switch focus per initiative lifecycle
4. **Findings drift** — Ensure SCALE-009 annotations capture current state accurately (may be partially incorrect)
5. **Type discipline** — If ARCH-IMPL-CONFORMANCE-001 work uncovers spec issues, mark them for spec_change; don't sneak normative changes into architecture initiative

## If Blocked
If any docs are missing or contradictory:
1. Note the specific contradiction in the planning summary
2. Mark the relevant Phase A checklist item as blocked with a note
3. Propose resolution in the summary (e.g., "Need maintainer clarification on SCALE-009 intent")
4. Do not proceed to Phase B planning until Phase A blockers are resolved

## Doc Sync Plan
Not applicable this loop (no new tests added/renamed).

---

**Validation**: After completing these tasks, the following should be true:
- `docs/fix_plan.md` shows ARCH-SIM-CONSTRUCTION-001 as `blocked_pending_environment` with clear block rationale
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/BLOCKED.md` exists and documents the omega hypothesis rejection
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md` exists and scopes Phase A
- `findings_inventory.md` and `module_inventory.md` exist with research notes
- `docs/fix_plan.md` includes new Attempts History for both initiatives
- `galph_memory.md` reflects the focus switch

No tests to run this loop; all validation is file existence + content spot-checks.
