# Input — Loop i=192 (Ralph)

## Summary
Execute DB-AT-SUITE-CARE-001 Phase D.2 exploratory scoping: inventory any proposed future DB-AT selectors and assess onboarding readiness.

## Focus
DB-AT-SUITE-CARE-001 — Phase D.2 Future DB-AT Onboarding (Scoping)

## Branch
integration

## Mapped Tests
- `none` — Phase D.2 is scoping/planning, no test execution required

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T112000Z/`

---

## Do Now

**Focus:** DB-AT-SUITE-CARE-001 — Phase D.2 Scoping

**Implement:** `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T112000Z/future_db_at_inventory.md`

**Validating selector:** `none` — evidence-only loop

**Artifacts path:** `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T112000Z/`

### Background

DB-AT-SUITE-CARE-001 Phase D is ongoing maintenance. D1 (regression monitoring cadence) is complete. D2 tasks scope future DB-AT selector onboarding. Per implementation.md:
> **D2 — Future DB-AT onboarding**: When new DB-AT selectors are proposed (e.g., DB-AT-025 HKL interpolation halo, DB-AT-030 sigma precedence, DB-AT-031+ Stage B/C profiles), create member plan implementation.md under `plans/active/DB-AT-<NNN>/`, add to portfolio progress dashboard, and coordinate Phase A/B/C execution.

This loop inventories any proposed/documented future DB-AT selectors and assesses which (if any) have specification support ready for implementation.

### Tasks

| ID | Task | Deliverable |
|----|------|-------------|
| D2.1 | Search docs/spec-db-conformance.md for DB-AT selectors beyond 024 | List of proposed selectors with spec status |
| D2.2 | Check docs/findings.md for any findings referencing new DB-AT selectors | Findings→selector mapping |
| D2.3 | Check problems.md for any entries requesting new acceptance tests | Problems→selector mapping |
| D2.4 | Assess onboarding readiness (spec exists, test scaffold possible) | Readiness matrix |
| D2.5 | Author future_db_at_inventory.md | Inventory document |
| D2.6 | Author summary.md | Turn Summary block |

---

## How-To Map

### D2.1: Search spec-db-conformance.md
```bash
grep -n "DB-AT-0[2-9][5-9]\|DB-AT-03" docs/spec-db-conformance.md 2>/dev/null || echo "No matches"
```

### D2.2: Search findings.md
```bash
grep -n "DB-AT-0[2-9][5-9]\|DB-AT-03" docs/findings.md 2>/dev/null || echo "No matches"
```

### D2.3: Check problems.md
```bash
grep -n "acceptance\|DB-AT" docs/problems.md 2>/dev/null || echo "No matches"
```

### D2.4-D2.6: Author artifacts
Create `future_db_at_inventory.md` with:
- Selector ID, Proposed Purpose, Spec Status (documented/draft/none), Test Status (exists/scaffold/none), Readiness (ready/needs_spec/blocked)
- Recommendation: which selectors to prioritize if any

---

## Pitfalls To Avoid

1. **DO NOT** create new DB-AT plan directories — this loop is scoping only
2. **DO NOT** author tests — inventory only
3. **DO** check multiple sources (spec, findings, problems, existing comments in tests)
4. **DO** note any selectors mentioned in code comments (e.g., `# TODO: DB-AT-025`)
5. **Environment Freeze:** No package installs, no production code changes

---

## If Blocked

1. If no future DB-AT selectors are documented: Report "No proposed selectors found" in inventory.md and recommend Phase D.2 as complete (no onboarding needed)
2. If selectors are documented but lack specs: Note as "needs_spec" and recommend spec authoring as prerequisite

---

## Findings Applied

- **TESTING-003**: Use canonical selector patterns when assessing new DB-AT proposals
- **PROBE-FREEZE-001**: No new probe scripts — inventory existing documentation only

---

## Pointers

- DB-AT-SUITE-CARE-001 implementation.md: `plans/active/DB-AT-SUITE-CARE-001/implementation.md:86-91` (Phase D tasks)
- spec-db-conformance.md: `docs/spec-db-conformance.md` (DB-AT acceptance criteria)
- TEST_SUITE_INDEX.md: `docs/development/TEST_SUITE_INDEX.md` (existing selector status)

---

## Next Up (optional)

If inventory shows no actionable selectors:
1. Mark D2 as "scoped — no immediate onboarding needed" in implementation.md
2. Consider D4 (TEST_SUITE_INDEX.md hygiene audit) as alternative maintenance task
