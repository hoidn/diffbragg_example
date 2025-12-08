# Implementation Plan: TORCH-REFINE-CLEANUP-001

## Initiative
- ID: TORCH-REFINE-CLEANUP-001
- Title: Stage A/B/C Refinement Probes Consolidation Roll-up
- Status: in_progress (Phase A scoped 2025-12-08T150000Z)

## Goals
- Consolidate status of 6 TORCH-REFINE member plans (001/002/002D/002E/003/004)
- Determine which pending Phase C/D tasks should be revived vs deferred/archived
- Clean up stale artifacts and update ledger coverage
- Provide portfolio steering visibility for refinement probe infrastructure

## Member Plans

| Plan ID | Current Status | Phases Complete | Remaining Work |
|---------|---------------|-----------------|----------------|
| TORCH-REFINE-001 | substantial_progress | A1-A3 ✅ | B1-B2, C1-C2 (stage scheduling, CLI wiring) |
| TORCH-REFINE-002 | substantial_progress | P1.1-P3.2 ✅ | P4.1-P4.3 (HKL perturbation) → delegated to 002D |
| TORCH-REFINE-002D | in_progress | P0.1, P1.1-P1.3 ✅ | P2.1-P2.2, P3.1-P3.2 (xfail removal, docs sync) |
| TORCH-REFINE-002E | in_progress | A0, A2-A3, B1 ✅ | B2-B5, C1-C3 (gradient probe, action & revalidation) |
| TORCH-REFINE-003 | pending | None | P0-P4 (Stage C detector microslip) |
| TORCH-REFINE-004 | done | All phases ✅ | None (cleanup tasks already done) |

## Exit Criteria
1. Member plan status matrix validated against implementation.md checklists
2. Decision documented: revive vs defer for each pending phase
3. TORCH-REFINE-004 confirmed ready for archive (all phases complete)
4. TORCH-REFINE-003 blocked status documented with dependency chain
5. fix_plan.md updated with roll-up completion status and artifacts

## Spec Alignment
- **Governed by:** REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016

## Phase A — Member Plan Reality Check

### Checklist
- [ ] A1: Audit each of 6 member plans' implementation.md and reports directories for completion status
- [ ] A2: Identify blocking dependencies (ARCH-GRADIENT-FLOW-001 for gradient work, ARCH-SIM-CONSTRUCTION-001 for DB-AT-028/029)
- [ ] A3: Classify remaining work as: revive (actionable now), blocked (pending Tier 0), deferred (low priority)
- [ ] A4: Author member_plan_status_audit.md with status matrix and classification
- [ ] A5: Author summary.md for Phase A deliverables

### Exit Criteria for Phase A
- All 6 member plans audited with current phase status
- Blocking dependency chain documented
- Classification (revive/blocked/deferred) for each pending phase

## Phase B — Portfolio Decision & Archival

### Checklist
- [ ] B1: Mark TORCH-REFINE-004 ready for archive (all phases complete, no pending work)
- [ ] B2: For revive-classified phases, queue in fix_plan.md or create follow-on initiatives
- [ ] B3: For blocked/deferred phases, update member plan implementation.md with deferral rationale
- [ ] B4: Update fix_plan.md TORCH-REFINE-CLEANUP-001 entry with Phase A/B completion

## Phase C — Closure

### Checklist
- [ ] C1: Run relevant test selectors (Stage A/B smoke) to confirm no regressions
- [ ] C2: Archive artifacts under reports directory
- [ ] C3: Mark roll-up done if no actionable work remains (all revive items queued elsewhere)

## Dependencies

### Tier 0 Blockers
- **ARCH-GRADIENT-FLOW-001** (blocked_pending_upstream): Blocks TORCH-REFINE-002E gradient work
- **ARCH-SIM-CONSTRUCTION-001** (blocked_pending_environment): Blocks DB-AT-028/029 acceptance criteria

### Internal Sequencing
- TORCH-REFINE-002D depends on TORCH-REFINE-002 Phase 1-3 (complete)
- TORCH-REFINE-003 depends on Stage A gate being live (blocked by 002D/002E)
- TORCH-REFINE-004 is standalone (complete)

## Findings Applied
- **REFINE-001** (warm-start + clamp): Stage A nucleus telemetry
- **REFINE-002** (0.1% nucleus baseline): Acceptance gate
- **GRADIENT-001** (tensor overrides preserve autograd): Crystal config passthrough
- **REFINE-004/005** (HKL halo/interpolation): 002D dependency

## Pointers
- Member plan directories: `plans/active/TORCH-REFINE-00X/`
- Refinement smoke tests: `tests/dbex/test_torch_refine_smoke.py`
- Stage A expansion: `test_stage_a_expansion`
- Stage B shell modifiers: `test_stage_b_shell_modifiers`

## Artifacts Index
- Reports root: `plans/active/TORCH-REFINE-CLEANUP-001/reports/`
