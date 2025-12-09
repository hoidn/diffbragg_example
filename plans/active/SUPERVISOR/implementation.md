# Implementation Plan: SUPERVISOR

## Initiative
- ID: SUPERVISOR
- Title: Supervisor Agent Documentation & Coordination Patterns
- Owner: Galph (supervisor) / Ralph (implementation)
- Spec Owner: N/A (meta-initiative for orchestration)
- Status: scoped — 2025-12-09T020000Z (Loop i=243)

## Goals
1. Document supervisor agent (Galph) responsibilities and decision patterns
2. Establish coordination protocols between supervisor (Galph) and implementation (Ralph) loops
3. Codify portfolio management policies and tier-based prioritization rules
4. Maintain living documentation for agent operation patterns

## Non-Goals
- Changing core DBEX physics or refinement code
- Adding new test infrastructure
- Modifying external dependencies (nanobrag_torch, simtbx)

## Phases Overview
- **Phase A — Documentation Audit** (LOW priority): Identify gaps in existing agent docs
- **Phase B — Policy Formalization** (OPTIONAL): Extract implicit patterns into explicit policies
- **Phase C — Archive Assessment** (DECISION): Determine if initiative should remain active or be archived

## Exit Criteria
1. **EC-1**: Portfolio management rules documented in `docs/` or `AGENTS.md`
2. **EC-2**: Galph/Ralph coordination patterns documented
3. **EC-3**: Decision: Archive vs. Living Documentation determination made

## Compliance Matrix
- [x] **Spec Constraint:** N/A (meta-initiative)
- [x] **Fix-Plan Link:** `docs/fix_plan.md:123` (Tier 4)
- [ ] **Finding/Policy ID:** Pending Phase B formalization

## Spec Alignment
- **Normative Spec:** N/A (meta-initiative)
- **Key Clauses:** N/A

## Context Priming (read before edits)
- Classification reference: `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md`
- Roadmap assessment: `plans/active/SUPERVISOR/reports/2025-11-24T153000Z/roadmap_assessment.md`
- Portfolio health: `plans/active/SUPERVISOR/reports/2025-12-09T020000Z/portfolio_health.md`

## Artifacts Index
- Reports root: `plans/active/SUPERVISOR/reports/`
- Latest run: `2025-12-09T020000Z/` (verification + scoping)
- Historical: `2025-11-24T153000Z/` (roadmap assessment)

## Scoping Decision (2025-12-09)

**Recommendation: LOW PRIORITY — Convert to Living Documentation**

Rationale:
1. Core portfolio management patterns already encoded in `prompts/supervisor.md` and `prompts/main.md`
2. No blocking use cases require formalized documentation
3. Existing `galph_memory.md` captures operational state effectively
4. Loop coordination working well without additional formalization

**Action**: Mark initiative as `scoped_low_priority` in fix_plan.md. Revisit only if coordination issues emerge or onboarding new agent instances becomes necessary.

_Status:_ scoped — 2025-12-09T020000Z. Initiative classified as LOW priority living documentation. No immediate action required; re-evaluate if agent coordination problems arise.
