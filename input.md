# Input for Ralph (Loop i=131)

## Summary
DB-AT-SUITE-CARE-001 Phase A — Acceptance suite roll-up scoping and implementation plan authoring.

## Mode
Docs

## ActionType
planning

## DecisionStatus
exploring

## InitiativeType
harness

## Focus
**DB-AT-SUITE-CARE-001** — Acceptance Suite Upkeep (DB-AT-002/010/020—024)

**Context**: Tier 1 initiative selected after MAP-SCALE-SYNC-001 closure (5/5 member plans complete). Seven DB-AT acceptance test initiatives exist with individual implementation.md files but lack ledger coverage in fix_plan.md. This Phase A loop will audit member plan status, analyze dependencies, define roll-up exit criteria, and create the canonical DB-AT-SUITE-CARE-001 implementation.md to enable portfolio steering visibility.

## Branch
integration

## Mapped tests
None (planning loop, docs-only deliverables)

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/`

## Findings Applied (Mandatory)
- **TESTING-003** (Acceptance test registry maintenance) — Normative requirement for TEST_SUITE_INDEX.md updates when acceptance tests change status; this roll-up initiative coordinates member plan registry sync tasks.
  - Code: `docs/development/TEST_SUITE_INDEX.md` (status table rows for DB-AT-XXX selectors)
  - Adherence: Phase A audit will identify registry drift; Phase C (future loop) will execute sync.

- **RUNTIME-001** (Runtime execution guardrails) — Acceptance tests must respect determinism flags (CUDA_VISIBLE_DEVICES, TORCHDYNAMO_DISABLE, NANOBRAGG_DISABLE_COMPILE) per spec-db-runtime.md.
  - Code: `docs/TESTING_GUIDE.md` (canonical environment flags)
  - Adherence: Member plan Phase B implementations must follow TESTING_GUIDE.md selector patterns; Phase A audit will note deviations.

- **DIAGNOSTICS-001** (Diagnostic artifact expectations) — Acceptance tests must emit structured artifacts (metrics JSON, env snapshots, command logs) to initiative reports/ directories.
  - Code: `tests/dbex/test_stage_a_smoke_parity.py` (artifact writer patterns)
  - Adherence: Member plan Phase C tasks include artifact emission; Phase A audit will verify artifact policy compliance.

- **MASKING-001** (Mask handling contracts) — Acceptance tests touching ROI/mask logic must use canonical mask precedence (trusted_mask ∩ ROI ∩ background >= 0) per spec-db-core.md:47.
  - Code: `dbex/data_load.py`, `dbex/refinement/inputs.py` (loss_mask construction)
  - Adherence: DB-AT-021 (Mask Application) member plan must validate canonical mask precedence; Phase A audit will cross-reference.

## Pointers

### SPEC
- **docs/spec-db-conformance.md** — Normative acceptance criteria for DB-AT-XXX selectors
- **docs/development/testing_strategy.md** §2 — Acceptance test philosophy

### ARCH
- **docs/architecture/tests_mapping.md** — Selector → module coverage map
- **docs/development/TEST_SUITE_INDEX.md** — Current DB-AT selector status table

### Testing Docs
- **docs/TESTING_GUIDE.md** — Canonical selector patterns, environment flags, artifact expectations

### Member Plan Directories
- **plans/active/DB-AT-002/implementation.md** — Determinism Acceptance Harness
- **plans/active/DB-AT-010/implementation.md** — Gradcheck Acceptance Harness
- **plans/active/DB-AT-020/implementation.md** — Data Ingestion
- **plans/active/DB-AT-021/implementation.md** — Mask Application
- **plans/active/DB-AT-022/implementation.md** — Background Subtraction
- **plans/active/DB-AT-023/implementation.md** — Structure Factor Loading
- **plans/active/DB-AT-024/implementation.md** — Mapping Smoke

## ARCH Contracts (mandatory)
**N/A** — DB-AT-SUITE-CARE-001 is a harness roll-up initiative coordinating member plan test authoring. No production code ARCH-CONTRACTs are modified this loop.

**Failure Classification**: Implementation alignment (harness initiative ensuring acceptance tests align with SPEC/ARCH, not a conformance failure).

## Do Now (hard validity contract)

**Implement**:
- **Docs-only**: Audit 7 member plan implementation.md files and author DB-AT-SUITE-CARE-001 roll-up implementation.md

**Validating pytest selector(s)**:
None (planning loop, no test execution)

**Artifacts path**:
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/`

**Initiative type consistency**:
✅ harness (test infrastructure maintenance via roll-up coordination)

### Detailed Tasks

#### Task 1: Member Plan Status Audit
**File to create**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/member_plan_status_audit.md`

For each of 7 member plans:
1. Read `plans/active/DB-AT-{ID}/implementation.md`
2. Extract phase checklist status, dependencies, test file location
3. Check for recent reports/ directory evidence
4. Classify status: pending / in_progress / blocked / done

**Output format**: Table with columns: Plan ID, Title, Phases (done/total), Dependencies, Test File Status, Status, Blocker

#### Task 2: Dependency Chain Analysis
**File to create**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/dependency_chain.md`

1. Map inter-initiative dependencies
2. Identify critical path
3. Note external dependencies
4. Recommend priority ordering

#### Task 3: Exit Criteria Definition
**File to create**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/exit_criteria.md`

Define 4-5 completion criteria for roll-up initiative.

#### Task 4: Create Roll-up Implementation Plan
**File to create**: `plans/active/DB-AT-SUITE-CARE-001/implementation.md`

Author canonical implementation.md with Phases A/B/C/D structure.

#### Task 5: Loop Summary
**File to create**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/summary.md`

Write concise summary of Phase A deliverables.

## Forbidden This Loop
- **No test execution** (planning loop, docs-only)
- **No production code changes**
- **No test authoring** (deferred to member plan phases)
- **No fix_plan.md edits yet** (Phase B task)

## Pitfalls To Avoid

1. **Type discipline**: This is a `harness` initiative (test infrastructure). Do not author production code changes.
2. **No stacking on assumptions**: If member plan files appear stale, note it but don't assume status.
3. **Evidence→Action contract**: Phase A output is implementation.md + audit artifacts.
4. **Findings paydown**: TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001 applied.

## If Blocked

If member plan implementation.md files are missing:
1. Note the gap in audit with status "missing_plan"
2. Recommend creating stub implementation.md in Phase B
3. Phase A completion not blocked

---

**Galph's Notes**:
- Tier 1 harness initiative selected after MAP-SCALE-SYNC-001 closure
- Phase A is pure scoping (audit + planning docs)
- Deliverables: 4 report artifacts + 1 implementation.md file
- Next loop (Phase B) will integrate member plan status into fix_plan.md

**Validation**: File existence checks (no pytest required)
