# Input for Ralph (Loop i=168)

## Summary
Execute TORCH-GEOMETRY-SYNC-001 Phase B (Closure) — finalize roll-up by updating status fields and creating closure documentation.

## BindingForRalph
- **ActionType:** review_or_housekeeping
- **DecisionStatus:** validated
- **InitiativeType:** architecture

## SupervisorMode
Docs (documentation-only closure loop)

## Focus
TORCH-GEOMETRY-SYNC-001 — Geometry Convergence & Parity Alignment (Phase B: Closure)

## Branch
integration

## Mapped Tests
- `pytest --collect-only tests -k "geometry or ub_param or DB_AT_026"` (verification only — no test execution this loop)

## Artifacts
`plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** — No new plan-local scripts; documentation-only closure
- **GEOMETRY-004** — UB parameterization validated (cited in closure)
- **CONVERGENCE-001** — Quaternion convergence fixed (cited in closure)

## Pointers
- Phase A artifacts: `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/` (member_plan_inventory.md, rollup_strategy.md)
- Roll-up Plan: `plans/active/TORCH-GEOMETRY-SYNC-001/implementation.md`
- Member Plans (to update Status fields):
  - `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Status: pending → done
  - `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` — Status: pending → done
  - `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md` — Status: pending → superseded
  - `plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md` — Status: pending → superseded
- Fix-plan row: `docs/fix_plan.md` Tier 1 — [TORCH-GEOMETRY-SYNC-001] (line ~357)

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-UB-001**: UB matrix / A* consistency
   - Owner: `dbex/geometry/crystallography.py`
   - Classification: implementation validation complete (UB-REALIGN-001)
2. **ARCH-CONTRACT-GEOMETRY-001**: Crystal geometry transformation chain
   - Owner: `dbex/refinement/stage_a.py`
   - Classification: implementation validation complete (CONVERGENCE-001)

---

## Do Now

**Focus:** TORCH-GEOMETRY-SYNC-001 Phase B (Closure)

### Execute Phase B tasks:

#### B1: Update fix_plan.md
1. **Locate** the TORCH-GEOMETRY-SYNC-001 entry in `docs/fix_plan.md` (Tier 1, line ~357)
2. **Change status** from `pending` to `done`
3. **Add closure note**: `(2025-12-08T200000Z: Roll-up complete. 2/4 member plans done (CONVERGENCE-001, UB-REALIGN-001 with 5/5 exit criteria each), 2/4 superseded (PARITY-002, PARITY-003 absorbed by incremental UB approach). Artifacts: plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/)`
4. **Add Attempts History entry**:
   ```
   * 2025-12-08T200000Z (Loop i=168, Ralph) — Phase B closure: Marked roll-up done. Updated 4 member plan status fields. Created closure_summary.md. Artifacts: plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/.
   ```

#### B2: Update PARITY-002/003 as Superseded
1. **Edit** `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md`:
   - Add supersession notice at top:
     ```markdown
     **Status:** superseded (by TORCH-GEOMETRY-UB-REALIGN-001)
     **Reason:** The incremental UB parameterization approach achieved parity goals without requiring det(U)=1 enforcement or hybrid parameterization.
     **Date:** 2025-12-08
     ```
2. **Edit** `plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md`:
   - Add supersession notice at top:
     ```markdown
     **Status:** superseded (by TORCH-GEOMETRY-UB-REALIGN-001)
     **Reason:** The det(U)≠1 issue discovered in PARITY-002 was bypassed by the incremental UB approach using dxtbx U₀/B₀ as baseline with quaternion ΔR increments.
     **Date:** 2025-12-08
     ```

#### B3: Update CONVERGENCE-001/UB-REALIGN-001 Status Fields
1. **Edit** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:
   - Find `Status: pending` line and change to `Status: done`
   - Ensure Phase C completion is documented
2. **Edit** `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md`:
   - Find `Status: pending` line and change to `Status: done`
   - Ensure Phase C completion is documented

#### B4: Create Closure Summary
1. **Create directory**: `mkdir -p plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/`
2. **Write** `closure_summary.md` with:
   - Executive summary (roll-up objective achieved)
   - Member plan status table (4 entries with status and exit criteria)
   - Key accomplishments:
     - CONVERGENCE-001: Diagnosed quaternion catastrophic failure as diagnostic script bug; bypass fix achieves stable chi² drift +0.0083%
     - UB-REALIGN-001: Implemented spec-compliant incremental UB parameterization (DB-AT-026 4/4 tests PASS)
   - Test coverage summary (6 geometry tests available)
   - Lessons learned (incremental parameterization approach vs det(U)=1 investigation)

#### B5: Write summary.md
1. **Write** `summary.md` in artifacts directory with turn summary

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example

# B1: Update fix_plan.md (use Edit tool)
# Target: docs/fix_plan.md, line ~357 (TORCH-GEOMETRY-SYNC-001)

# B2: Update superseded plans (use Edit tool)
# - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md
# - plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md

# B3: Update done plans (use Edit tool)
# - plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md
# - plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md

# B4: Create artifacts directory
mkdir -p plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/

# Verify no production code changes
git status
```

## Pitfalls To Avoid
1. **Do not modify production code** — Phase B is documentation-only
2. **Do not create new probe scripts** — PROBE-FREEZE-001 applies
3. **Do not run tests** — verification only (collect-only if needed)
4. **Preserve existing content** — add supersession notices at TOP of files, don't delete existing content
5. **Use exact timestamps** — 2025-12-08T200000Z for consistency
6. **Update all 4 member plans** — don't miss any status field updates

## Forbidden This Loop
- No production code changes (docs-only closure loop)
- No new plan-local scripts (per PROBE-FREEZE-001)
- No test execution (verification only)
- Do not delete existing plan content (add supersession notices only)

## If Blocked
If any member plan file is missing or has unexpected format:
- Document the issue in summary.md
- Update what you can
- Note the gap for follow-up
- Do NOT attempt production code changes to resolve

---

## Exit Criteria Validation (for Phase B)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| fix_plan.md updated | Status: done | Grep for status change |
| PARITY-002 superseded | Notice at top | Read file header |
| PARITY-003 superseded | Notice at top | Read file header |
| CONVERGENCE-001 Status: done | Field updated | Read file |
| UB-REALIGN-001 Status: done | Field updated | Read file |
| closure_summary.md exists | File in artifacts dir | Glob check |
| summary.md exists | File in artifacts dir | Glob check |
| No production code changed | git status clean | Verify no staged src/ changes |

---

## Output Artifacts Expected

1. `docs/fix_plan.md` — updated status + Attempts History
2. `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md` — supersession notice
3. `plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md` — supersession notice
4. `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Status: done
5. `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` — Status: done
6. `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/closure_summary.md`
7. `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/summary.md`
