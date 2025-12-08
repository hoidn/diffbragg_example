# Input for Ralph (Loop i=167)

## Summary
Execute TORCH-GEOMETRY-SYNC-001 Phase A (Reality Check) — assess status of 4 member plans and determine roll-up completion path.

## BindingForRalph
- **ActionType:** evidence_collection
- **DecisionStatus:** exploring
- **InitiativeType:** architecture

## SupervisorMode
none (evidence collection / reality check)

## Focus
TORCH-GEOMETRY-SYNC-001 — Geometry Convergence & Parity Alignment (Phase A: Member Plan Reality Check)

## Branch
integration

## Mapped Tests
- `pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_*` (Stage A geometry tests)
- `pytest --collect-only tests -k geometry` (geometry-related test inventory)

## Artifacts
`plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** — No new plan-local scripts; evidence collection only via file reads
- **GEOMETRY-001, GEOMETRY-002** — Geometry convergence and parity findings (reference)
- **HKL-ORIENT-001** — HKL orientation alignment (reference)
- **CONVERGENCE-001** — Convergence stability requirements (reference)

## Pointers
- Roll-up Plan: `plans/active/TORCH-GEOMETRY-SYNC-001/implementation.md` (stub — needs population)
- Member Plans:
  - `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Quaternion U-Matrix convergence
  - `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md` — Geometry parity analysis
  - `plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md` — Additional parity work
  - `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` — UB matrix realignment
- Fix-plan row: `docs/fix_plan.md` Tier 1 — [TORCH-GEOMETRY-SYNC-001] (line ~356-373)
- Spec refs:
  - `docs/spec-db-core.md` §Baseline Crystal State
  - `docs/spec-db-workflow.md` §Stage A

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-UB-001**: UB matrix / A* consistency
   - Owner: `dbex/geometry/crystallography.py`
   - Classification: implementation validation (geometry alignment)
2. **ARCH-CONTRACT-GEOMETRY-001**: Crystal geometry transformation chain
   - Owner: `dbex/refinement/stage_a.py`
   - Classification: implementation validation (convergence)

---

## Do Now

**Focus:** TORCH-GEOMETRY-SYNC-001 Phase A (Member Plan Reality Check)

### Execute Phase A tasks:

#### A1: Inventory Member Plans
1. **Read each member plan implementation.md**:
   - `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` (38KB — substantial)
   - `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md` (18KB)
   - `plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md` (13KB)
   - `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` (9KB)
2. **For each plan, document**:
   - Current status (pending/in_progress/blocked/done)
   - Phases completed (with artifact references)
   - Phases remaining (with blockers if any)
   - Exit criteria satisfaction level (X/Y satisfied)
3. **Output**: `member_plan_inventory.md`

#### A2: Identify Dependencies and Blockers
1. **Cross-reference member plan dependencies**:
   - Does CONVERGENCE-001 block UB-REALIGN-001?
   - Do PARITY-002/003 depend on CONVERGENCE-001 findings?
2. **Check for Tier 0 blockers**:
   - Any dependence on ARCH-REFACTOR-001 (blocked)?
   - Any dependence on ARCH-GRADIENT-FLOW-001 (partial)?
3. **Output**: `dependency_analysis.md`

#### A3: Assess Roll-up Completion Path
1. **Determine if member plans are**:
   - Mostly complete (ready for closure consolidation)
   - Substantially incomplete (need active work)
   - Blocked (need upstream resolution)
2. **Propose roll-up strategy**:
   - Option A: Close roll-up if member plans effectively done
   - Option B: Prioritize specific member plan for active work
   - Option C: Mark roll-up blocked if upstream dependencies unresolved
3. **Output**: `rollup_strategy.md`

#### A4: Update Roll-up Implementation Plan
1. **Populate `plans/active/TORCH-GEOMETRY-SYNC-001/implementation.md`** with:
   - Member plan status summary
   - Dependencies
   - Exit criteria tied to member plan completions
   - Phase breakdown (if active work needed)
2. **Output**: Updated `implementation.md`

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example

# A1: Read member plans (use Read tool)
# - plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md
# - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md
# - plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md
# - plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md

# Check latest reports for each
ls -la plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/ | tail -5
ls -la plans/active/TORCH-GEOMETRY-PARITY-002/reports/ | tail -5
ls -la plans/active/TORCH-GEOMETRY-PARITY-003/reports/ | tail -5
ls -la plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/ | tail -5

# A2: Check test inventory
pytest --collect-only tests/dbex/test_torch_refine_smoke.py 2>&1 | head -40

# Create artifacts directory
mkdir -p plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/
```

## Pitfalls To Avoid
1. **Do not modify production code** — Phase A is evidence collection only
2. **Do not create new probe scripts** — PROBE-FREEZE-001 applies
3. **Do not run full test suite** — collect-only for inventory
4. **Use Read tool for file examination** — for precise analysis
5. **Cite file:line** — all code references must include line numbers
6. **Do not start implementing member plan work** — this loop is scoping only

## Forbidden This Loop
- No production code changes (evidence-only loop)
- No new plan-local scripts (per PROBE-FREEZE-001)
- No test execution beyond collect-only (Phase A is research)
- Do not begin active work on member plans (scoping only)

## If Blocked
If member plans have unclear status or missing artifacts:
- Document the gap in `member_plan_inventory.md`
- Note which member plan needs investigation
- Recommend next loop focus (specific member plan Phase X)
- Do NOT attempt to resolve unclear status in this loop

---

## Exit Criteria Validation (for Phase A)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Member plan inventory complete | `member_plan_inventory.md` exists | File in artifacts dir |
| Dependency analysis complete | `dependency_analysis.md` exists | File in artifacts dir |
| Roll-up strategy proposed | `rollup_strategy.md` exists | File in artifacts dir |
| Roll-up implementation.md updated | Non-stub content | File updated |
| Summary authored | `summary.md` exists | File in artifacts dir |
| No production code changed | git status clean | Verify no staged changes |

---

## Output Artifacts Expected

1. `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/member_plan_inventory.md`
2. `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/dependency_analysis.md`
3. `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/rollup_strategy.md`
4. `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/summary.md`
5. `plans/active/TORCH-GEOMETRY-SYNC-001/implementation.md` (updated from stub)
