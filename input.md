# Input for Ralph — Loop i=141

## Summary
Portfolio lifecycle review + environment blocker escalation documentation after ARCH-GRADIENT-FLOW-001 Phase B.1 Option C hypothesis rejection.

## Metadata
- **Mode**: Docs
- **ActionType**: review_or_housekeeping
- **DecisionStatus**: exploring
- **InitiativeType**: architecture
- **Focus**: ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)
- **Branch**: integration
- **Mapped tests**: none — documentation-only loop
- **Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T000000Z/`

## Findings Applied (Mandatory)
- **GRADIENT-001** (Gradient test patterns): Phase B.1 Option C correctly avoided `.item()` coercion in production code paths, but detector/beam tests remain blocked by suspected nanobrag_torch internal gradient handling issues (DetectorConfig.distance_mm field assignment OR simulator.py:761 torch.tensor() detachment). Adherence: No production code changes violate GRADIENT-001; blocker is external.
- **RUNTIME-001** (Runtime execution guardrails): All gradcheck test commands use `NANOBRAGG_DISABLE_COMPILE=1` per canonical flags. Adherence: Test execution follows TESTING_GUIDE.md selectors.
- **TESTING-003** (Acceptance test registry): TEST_SUITE_INDEX.md will require update post-fix. Adherence: Deferred to Phase B.4 per implementation.md.

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-GRADIENT-HYGIENE** (Gradient flow preservation in physics/refinement):
   - **Owner**: `dbex/physics/forward.py::simulate_forward_torch`, `dbex/geometry/crystallography.py::TorchCrystal`
   - **Forbidden duplicates**: `.item()` / `.detach()` calls on tensors with `requires_grad=True` in production refinement paths
   - **Failure classification**: **external_dependency_blocker** — Production code audit (Phase A.2, i=138) found 0 UNSAFE patterns. Test harness gradient breaks identified but involve dxtbx geometry construction requirements (.item() extraction for scalar distances/wavelengths). Phase B.1 Options A/B/C all attempted to preserve gradient flow via tensor-valued overrides, but detector Jacobian numerical/analytical mismatch (~21,556×) persists and beam test remains blocked by nanobrag_torch.simulator.py:761 external detachment. Hypothesis: nanobrag_torch DetectorConfig field handling OR simulator gradient chain issue.

## Do Now (hard validity contract)

**Context**: Loop i=140 (Ralph) rejected Phase B.1 Option C hypothesis. Post-creation override pattern (detector/beam fields assigned AFTER config construction, symmetrical to crystal_overrides) produced IDENTICAL detector Jacobian mismatch signature as i=139 pre-creation approach (numerical 2.39e+12, analytical 1.11e8, ~21,556× off). Both detector AND beam tests now blocked_pending_environment. ARCH-GRADIENT-FLOW-001 exceeds implementation budget (3 loops: i=138 evidence, i=139 Option A/B, i=140 Option C) without successful gradient flow restoration.

**Decision**: Mark ARCH-GRADIENT-FLOW-001 as **blocked_pending_environment** and prepare maintainer escalation artifacts.

**Tasks**:
1. **Read** `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/option_c_implementation_summary.md` to confirm Option C rejection evidence
2. **Author** lifecycle decision document at `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T000000Z/lifecycle_decision.md` with:
   - Hypothesis timeline (Options A/B/C)
   - Evidence summary (detector Jacobian mismatch signature unchanged, beam external blocker persists)
   - Blocker classification: external_dependency (nanobrag_torch DetectorConfig / simulator gradient handling)
   - Three unblock paths: (A) maintainer investigation with reproducer [RECOMMENDED], (B) spec_change to relax gradcheck tolerances / mark DB-AT-010 xfail, (C) defer gradient-safe profile to future release
   - Artifacts inventory (pytest logs, implementation summaries for i=138/139/140)
3. **Update** `docs/fix_plan.md` line 22: change status from `in_progress` to `blocked_pending_environment`, append blocker summary to Attempts History
4. **Update** `galph_memory.md` line 1: record focus=ARCH-GRADIENT-FLOW-001, state=lifecycle_decision, action=review_or_housekeeping, next_action=tier1_focus_selection
5. **Author** `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T000000Z/summary.md` summarizing this loop's lifecycle decision
6. **Commit** all changes with message prefix `ARCH-GRADIENT-FLOW-001 lifecycle:`

## Forbidden This Loop
- No production code edits (docs/planning only)
- No new probe/instrumentation scripts
- No pytest execution (evidence already exists from i=138-140)

## How‑To Map
```bash
# No test execution this loop
# Artifacts directory creation only
mkdir -p plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T000000Z/
```

## Pitfalls To Avoid
1. **Type discipline**: This is an architecture initiative; do not retype to bugfix/harness
2. **Blocker escalation**: Document THREE unblock paths (maintainer/spec_change/defer), recommend maintainer investigation
3. **Portfolio steering**: After marking ARCH-GRADIENT-FLOW-001 blocked, Tier 0 is exhausted (all items done/archived/blocked); next loop must select Tier 1 focus or perform roll-up scoping
4. **Evidence-driven**: Lifecycle decision MUST cite concrete evidence from i=138/139/140 (Jacobian mismatch unchanged, beam external blocker)
5. **Dwell tracking**: Reset dwell counters for this selector+signature when switching focus next loop
6. **No probe saturation violation**: Do not extend Phase A.3 gradient probe; implementation budget exhausted
7. **ARCH conformance**: Blocker classification is external_dependency_blocker, NOT implementation_bug_within_architecture
8. **Dominant-hypothesis lock violation**: After 3 implementation loops (i=138 evidence, i=139 partial fix, i=140 Option C refactor), cannot plan additional implementation work until external blocker resolved

## If Blocked
If lifecycle decision authoring discovers missing evidence, stop and explicitly note the gap in summary.md rather than inventing findings. All required evidence exists in i=138/139/140 artifacts.

## Doc Sync Plan
Not applicable this loop (no test collection changes).

## Pointers
- **ARCH-GRADIENT-FLOW-001 implementation.md**: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md` (Phases A-C, Phase B.1 tasks)
- **Evidence artifacts**:
  - i=138: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/` (call graph, suspect audit)
  - i=139: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/` (Option A/B planning, tensor-valued overrides)
  - i=140: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/` (Option C implementation, hypothesis rejection)
- **Fix plan ledger**: `docs/fix_plan.md` line 22 (ARCH-GRADIENT-FLOW-001 status)
- **Galph memory**: `galph_memory.md` line 1 (focus tracking)
- **SPEC references**: `docs/spec-db-conformance.md` §Gradient-Safe Profile, `docs/spec-db-runtime.md` §Gradient Hygiene
- **ARCH references**: `docs/architecture.md` §13 Common Pitfalls (to be updated Phase B.4 when unblocked)
- **Testing docs**: `docs/TESTING_GUIDE.md` §1.4 DB-AT-010 selector, `docs/development/TEST_SUITE_INDEX.md` DB-AT-010 row
