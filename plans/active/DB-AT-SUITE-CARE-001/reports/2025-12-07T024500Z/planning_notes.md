# DB-AT-SUITE-CARE-001 Phase A Planning Notes

## Loop Context
- **Loop**: i=131 (Galph)
- **Date**: 2025-12-07T024500Z
- **Action**: Planning (Phase A scoping + implementation.md authoring)
- **Prior Focus**: MAP-SCALE-SYNC-001 (closed this loop, 5/5 member plans complete)
- **Current Focus**: DB-AT-SUITE-CARE-001 (Tier 1, unblocked)

## Initiative Overview

**Initiative ID**: DB-AT-SUITE-CARE-001
**Title**: Acceptance Suite Upkeep (DB-AT-002/010/020—024)
**Type**: harness (test infrastructure maintenance)
**Status**: pending (no implementation.md exists yet)
**Tier**: 1 (Core Physics & Stability)

## Problem Statement

Per fix_plan.md Tier 1 entry:
> The plan directories under `plans/active/DB-AT-002/`, `.../DB-AT-010/`, and `.../DB-AT-020` through `.../DB-AT-024/` already contain implementation plans, but none were represented in this ledger. Scope: keep the DB-AT selectors mapped to fix-plan items, document status per selector, and surface artifacts/blocked states in the Attempts History.

**Gap Identified**:
- 7 DB-AT acceptance test initiatives exist with implementation.md files
- None have ledger coverage in fix_plan.md Attempts History
- Test status, blocker states, and artifact pointers are not visible in fix_plan
- Portfolio steering cannot assess acceptance test health without manual plan directory traversal

## Governance References

**Governed by Findings**:
- TESTING-003 (Acceptance test registry maintenance)
- RUNTIME-001 (Runtime execution guardrails)
- DIAGNOSTICS-001 (Diagnostic artifact expectations)
- MASKING-001 (Mask handling contracts)

**Normative SPEC**:
- `docs/spec-db-conformance.md` — Acceptance test definitions (DB-AT-XXX)
- `docs/development/testing_strategy.md` §2 — Acceptance test philosophy
- `docs/TESTING_GUIDE.md` — Canonical selectors and environment flags

**Architecture**:
- `docs/architecture/tests_mapping.md` — Selector → module coverage map
- `docs/development/TEST_SUITE_INDEX.md` — DB-AT selector status table

## Member Plan Inventory

### Existing Plan Directories
```
plans/active/DB-AT-002/     # Determinism Acceptance Harness
plans/active/DB-AT-010/     # Gradcheck Acceptance Harness
plans/active/DB-AT-020/     # Data Ingestion
plans/active/DB-AT-021/     # Mask Application
plans/active/DB-AT-022/     # Background Subtraction
plans/active/DB-AT-023/     # Structure Factor Loading
plans/active/DB-AT-024/     # Mapping Smoke (integrated)
```

### Initial Status Assessment (from brief audit)

**DB-AT-002** (Determinism):
- implementation.md exists with 3-phase structure (A/B/C)
- All phases unchecked (pending)
- Depends on: FORWARD-EQUIV-002 (golden data fixtures)
- Test file: `tests/dbex/test_forward_determinism.py` (planned, not yet created)

**DB-AT-010** (Gradcheck):
- Need to audit implementation.md
- Likely depends on: canonical Stage APIs, differentiable physics helpers

**DB-AT-020—023** (Data pipeline):
- Need to audit implementation.md files for each
- Likely cover: ingestion, masking, background, structure factors
- These may already have partial test coverage in existing test modules

**DB-AT-024** (Mapping smoke):
- **Already integrated**: `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_024_mapping_smoke`
- Status likely: done or in_progress (needs confirmation via test run)

## Phase A Scope: Roll-up Implementation Plan Authoring

### Goals
1. Create canonical implementation.md for DB-AT-SUITE-CARE-001 roll-up
2. Audit all 7 member plan implementation.md files for:
   - Current phase completion status
   - Dependencies (blocked vs unblocked)
   - Test file existence (authored vs planned)
   - Recent artifacts/reports (evidence of progress)
3. Define exit criteria for roll-up initiative
4. Establish dependency chain priority ordering

### Non-Goals
- Implementing any tests (deferred to member plan phases)
- Running test suites (evidence-only loop, no execution)
- Modifying SPEC or ARCH docs (registry sync deferred to member plan Phase C tasks)

### Deliverables (Phase A)

#### A1: Member Plan Status Audit
**Artifact**: `member_plan_status_audit.md`

For each of 7 member plans (DB-AT-002, 010, 020-024):
- Read implementation.md phase checklist
- Count phases: total / checked / unchecked
- Note dependencies (from "Depends on" section)
- Check for recent reports/ directories (evidence of work)
- Identify test file status: exists / planned / location
- Classify status: pending / in_progress / blocked / done

**Output Schema**:
```markdown
| Plan ID | Title | Phases (done/total) | Dependencies | Test File Status | Classified Status | Blocker |
|---------|-------|---------------------|--------------|------------------|-------------------|---------|
| DB-AT-002 | Determinism | 0/3 (A/B/C) | FORWARD-EQUIV-002 | Planned (test_forward_determinism.py) | blocked (missing fixtures) | FORWARD-EQUIV-002 |
| ... | ... | ... | ... | ... | ... | ... |
```

#### A2: Dependency Chain Analysis
**Artifact**: `dependency_chain.md`

- Map inter-initiative dependencies (e.g., DB-AT-002 → FORWARD-EQUIV-002)
- Identify critical path (which DB-AT can unblock others)
- Note external dependencies (golden data, environment setup)
- Recommend priority ordering for member plan execution

**Output**: Mermaid-style dependency graph + priority list

#### A3: Roll-up Exit Criteria Definition
**Artifact**: `exit_criteria.md`

Define completion criteria for DB-AT-SUITE-CARE-001:
1. All 7 member plans have ledger coverage in fix_plan.md
2. Test registry (TEST_SUITE_INDEX.md) reflects current member plan status
3. Blocked member plans documented with blocker cross-references
4. Artifact pointers for completed member plans in fix_plan Attempts History

#### A4: Implementation Plan Template
**Artifact**: `plans/active/DB-AT-SUITE-CARE-001/implementation.md`

Create roll-up implementation.md with:
- **Purpose**: Maintain acceptance test suite health via member plan coordination
- **References**: SPEC, ARCH, findings cross-refs
- **Exit Criteria**: (from A3)
- **Member Plan Status**: Table linking to A1 audit
- **Phase Breakdown**:
  - Phase A: Scoping (this loop)
  - Phase B: Ledger integration (update fix_plan.md with member plan Attempts History entries)
  - Phase C: Registry sync (update TEST_SUITE_INDEX.md with current status)
  - Phase D: Blocker resolution coordination (track progress on FORWARD-EQUIV-002, etc.)
- **Artifacts Index**: Standard structure

## Next Loop Scope (Phase B Preview)

**Focus**: Ledger Integration

**Tasks**:
1. Update fix_plan.md with 7 member plan subsections under DB-AT-SUITE-CARE-001 Attempts History
2. For each member plan, write 1-paragraph status entry with:
   - Current phase completion count
   - Blocker state (if any)
   - Recent artifact pointer
   - Next action
3. Validate fix_plan.md formatting (no broken Markdown)
4. Commit Phase B with ledger coverage improvements

**Mapped Tests**: None (docs-only loop)

## Risks and Mitigations

### Risk 1: Member plan implementation.md files may be stale
**Mitigation**: Phase A audit will identify inconsistencies; mark stale plans for refresh in Phase D

### Risk 2: Some DB-AT tests may already exist but not documented
**Mitigation**: Grep for `test_db_at_` and `DB_AT_` in tests/ directory; cross-reference with TEST_SUITE_INDEX.md

### Risk 3: Dependency blockers (e.g., FORWARD-EQUIV-002) may delay multiple member plans
**Mitigation**: Phase A dependency chain analysis will identify critical path; consider elevating blocker initiatives to higher priority

## SPEC/ARCH Alignment

### SPEC Contracts
- `docs/spec-db-conformance.md` defines normative acceptance criteria for each DB-AT-XXX selector
- Roll-up initiative must ensure member plans align with SPEC gates

### ARCH Constraints
- `docs/architecture/tests_mapping.md` maps selectors to modules
- Acceptance tests must exercise canonical owner APIs (not test-specific mocks where avoidable)

### Initiative Type Discipline
- **Type**: harness (test infrastructure, not production feature/bugfix/architecture)
- **Acceptable work**: Test authoring, fixture curation, registry updates, blocker coordination
- **Out of scope**: Production code changes (those belong in feature/bugfix/architecture initiatives)

## Evidence Parameter Sourcing

**Mode**: Exploratory (audit existing plans, define roll-up structure)

**Parameter Sources**:
- Member plan implementation.md files (ground truth for phase status)
- TEST_SUITE_INDEX.md (current registry state)
- tests/ directory (actual test file existence)
- SPEC citations (normative acceptance criteria)

**Validation**: Cross-reference member plan "Depends on" sections with fix_plan.md status to confirm blockers are real

## Artifacts Path

**This Loop (Phase A)**:
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/`
  - planning_notes.md (this file)
  - member_plan_status_audit.md (A1)
  - dependency_chain.md (A2)
  - exit_criteria.md (A3)
  - summary.md (end-of-loop summary)

**Implementation Plan**:
- `plans/active/DB-AT-SUITE-CARE-001/implementation.md` (A4, created this loop)

## Do Now Preview (for input.md)

**Summary**: DB-AT-SUITE-CARE-001 Phase A — Acceptance suite roll-up scoping

**Mode**: Docs

**ActionType**: planning

**DecisionStatus**: exploring (audit member plan status, define roll-up exit criteria)

**InitiativeType**: harness

**Focus**: DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep (DB-AT-002/010/020—024)

**Branch**: integration

**Mapped tests**: none (docs-only planning loop)

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/`

**Findings Applied**: TESTING-003 (acceptance test registry), RUNTIME-001 (execution guardrails)

**ARCH Contracts**: N/A (harness initiative, no production code contracts)

**Do Now**:
1. Read all 7 member plan implementation.md files (DB-AT-002, 010, 020-024)
2. Audit phase completion status, dependencies, test file existence
3. Produce member_plan_status_audit.md (table format)
4. Analyze dependency chain, create dependency_chain.md with priority ordering
5. Define roll-up exit criteria in exit_criteria.md
6. Author canonical implementation.md for DB-AT-SUITE-CARE-001 with Phase A-D structure
7. Write summary.md with Phase A completion evidence
8. No tests to run (planning loop)

**Forbidden This Loop**:
- No test execution (evidence-only)
- No production code changes (harness scoping only)
- No test authoring (deferred to member plan phases)

---

**Author**: Galph (supervisor)
**Date**: 2025-12-07T024500Z
**Loop**: i=131
**Next Actor**: Ralph (engineer, will execute Phase A deliverables)
