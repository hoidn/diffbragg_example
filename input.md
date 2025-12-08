# Input for Ralph (Loop i=169)

## Summary
Execute Execution Roadmap synchronization — fix stale status entries in fix_plan.md Execution Roadmap section to match detailed section statuses.

## BindingForRalph
- **ActionType:** review_or_housekeeping
- **DecisionStatus:** N/A (housekeeping)
- **InitiativeType:** harness (ledger maintenance)

## SupervisorMode
Docs (documentation-only housekeeping loop)

## Focus
PORTFOLIO-STATUS — Execution Roadmap Synchronization (ledger hygiene)

## Branch
integration

## Mapped Tests
- None (docs-only loop)

## Artifacts
`plans/active/PORTFOLIO-STATUS/reports/2025-12-08T210000Z/`

## Findings Applied (Mandatory)
- No findings apply (docs-only housekeeping)

## Pointers
- Fix plan: `docs/fix_plan.md`
- Execution Roadmap: lines 16-105
- Detailed sections: lines 109-700+

---

## Do Now

**Focus:** Execution Roadmap Synchronization

### Background
The Execution Roadmap summary (lines 16-105) contains status entries that are inconsistent with the detailed initiative sections below. This creates confusion for portfolio steering and violates the single-source-of-truth principle.

### Inconsistencies to Fix

| Line | Initiative | Current Roadmap Status | Correct Status (from detailed section) |
|------|-----------|------------------------|----------------------------------------|
| 40 | DB-AT-SUITE-CARE-001 | `**pending**` | `**in_progress**` (Phase C complete, DB-AT-010 blocked) |
| 46 | PHYSICS-LOSS-001 | `**pending**` | `**done_with_environment_caveat**` |
| 52 | TORCH-GEOMETRY-SYNC-001 | `**pending**` | `**done**` |

### Execute Tasks

#### Task 1: Fix DB-AT-SUITE-CARE-001 (line 40)
1. **Locate** line 40 in `docs/fix_plan.md`
2. **Change** `— **pending**.` to `— **in_progress** (Phase C complete; Workflow Integration cluster certified; DB-AT-010 blocked_pending_environment escalated to ARCH-GRADIENT-FLOW-001).`
3. The text should become:
   ```
   - [DB-AT-SUITE-CARE-001] (Acceptance suite upkeep for DB-AT-002/010/020/021/022/023/024) — **in_progress** (Phase C complete; Workflow Integration cluster certified; DB-AT-010 blocked_pending_environment escalated to ARCH-GRADIENT-FLOW-001).
   ```

#### Task 2: Fix PHYSICS-LOSS-001 (line 46)
1. **Locate** line 46 in `docs/fix_plan.md`
2. **Change** `— **pending**.` to `— **done_with_environment_caveat** (all phases A-I complete; exit criteria satisfied; see detailed section line 343).`
3. The text should become:
   ```
   - [PHYSICS-LOSS-001] (Variance-weighted loss parity and telemetry fixes) — **done_with_environment_caveat** (all phases A-I complete; exit criteria satisfied; see detailed section line 343).
   ```

#### Task 3: Fix TORCH-GEOMETRY-SYNC-001 (line 52)
1. **Locate** line 52 in `docs/fix_plan.md`
2. **Change** `— **pending**.` to `— **done** (2025-12-08T200000Z: Roll-up complete; see detailed section line 357).`
3. The text should become:
   ```
   - [TORCH-GEOMETRY-SYNC-001] (Geometry convergence/parity/UB realign initiatives) — **done** (2025-12-08T200000Z: Roll-up complete; see detailed section line 357).
   ```

#### Task 4: Create summary.md
1. **Write** `plans/active/PORTFOLIO-STATUS/reports/2025-12-08T210000Z/summary.md` with:
   - Turn summary
   - List of fixes applied (3 Execution Roadmap status corrections)
   - Verification steps taken

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example

# Task 1-3: Use Edit tool on docs/fix_plan.md for each line
# Target lines: 40, 46, 52

# Task 4: Write summary.md
# Target: plans/active/PORTFOLIO-STATUS/reports/2025-12-08T210000Z/summary.md

# Verify no production code changes
git status
```

## Pitfalls To Avoid
1. **Do not modify production code** — this is docs-only housekeeping
2. **Do not change detailed section content** — only sync Execution Roadmap to match detailed sections
3. **Preserve surrounding context** — use exact Edit tool matches
4. **Do not delete any content** — only update status strings

## Forbidden This Loop
- No production code changes
- No new plan-local scripts
- No test execution
- Do not modify detailed initiative sections (only Execution Roadmap summary)

## If Blocked
If any line cannot be located or has unexpected format:
- Document the issue in summary.md
- Update what you can
- Note the gap for follow-up

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Line 40 updated | Status includes "in_progress" | Grep for pattern |
| Line 46 updated | Status includes "done_with_environment_caveat" | Grep for pattern |
| Line 52 updated | Status includes "done" | Grep for pattern |
| summary.md exists | File in artifacts dir | Glob check |
| No production code changed | git status clean | Verify no staged src/ changes |

---

## Output Artifacts Expected

1. `docs/fix_plan.md` — 3 Execution Roadmap status corrections
2. `plans/active/PORTFOLIO-STATUS/reports/2025-12-08T210000Z/summary.md`
