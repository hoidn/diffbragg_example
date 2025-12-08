# Input — Loop i=194 (Ralph)

## Summary
Execute DB-AT-SUITE-CARE-001 Phase D.4: TEST_SUITE_INDEX hygiene audit for selector registry consistency.

## Focus
DB-AT-SUITE-CARE-001 — Phase D.4 TEST_SUITE_INDEX Hygiene Audit (Maintenance)

## Branch
integration

## Mapped Tests
- `none` — Phase D.4 is registry audit, no test execution required (collect-only verification)

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T140000Z/`

---

## Do Now

**Focus:** DB-AT-SUITE-CARE-001 — Phase D.4 TEST_SUITE_INDEX Hygiene

**Implement:** `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T140000Z/test_registry_audit.md`

**Validating selector:** `none` — evidence-only loop (collect-only verification)

**Artifacts path:** `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T140000Z/`

### Background

DB-AT-SUITE-CARE-001 Phase D is ongoing maintenance. D.1 (regression cadence) and D.2 (future selector scoping) are complete. D.4 tasks audit the test registry for consistency:

Per implementation.md:
> **D4 — TEST_SUITE_INDEX hygiene**: Periodic audit to ensure all Active selectors in TEST_SUITE_INDEX.md have corresponding entries in TESTING_GUIDE.md with canonical commands and vice versa.

This loop performs a cross-reference audit between:
1. `docs/development/TEST_SUITE_INDEX.md` — Test selector registry
2. `docs/TESTING_GUIDE.md` — Canonical test commands and environment

### Tasks

| ID | Task | Deliverable |
|----|------|-------------|
| D4.1 | Extract all "Active" selectors from TEST_SUITE_INDEX.md | Selector list |
| D4.2 | Cross-reference selectors with TESTING_GUIDE.md entries | Gap analysis |
| D4.3 | Run `pytest --collect-only` for each selector pattern to verify collection | Collection verification |
| D4.4 | Identify any stale/orphaned entries (selector doesn't collect, or missing from one doc) | Orphan list |
| D4.5 | Author test_registry_audit.md with findings and recommendations | Audit document |
| D4.6 | Author summary.md | Turn Summary block |

---

## How-To Map

### D4.1: Extract Active selectors from TEST_SUITE_INDEX.md
```bash
grep -E "^\| .* \| Active" docs/development/TEST_SUITE_INDEX.md | awk -F'|' '{print $2}' | sed 's/^ *//;s/ *$//'
```

### D4.2: Cross-reference with TESTING_GUIDE.md
For each selector, check if TESTING_GUIDE.md contains:
- The selector name/pattern
- A canonical pytest command
- Environment variable requirements

### D4.3: Collect-only verification
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests -k "<selector_pattern>" 2>&1 | tail -5
```

### D4.4-D4.6: Author artifacts
Create `test_registry_audit.md` with:
- Full selector inventory (ID, Selector Pattern, TEST_SUITE_INDEX Status, TESTING_GUIDE Status, Collection Count)
- Gap analysis: selectors in one doc but not the other
- Orphan analysis: selectors that don't collect
- Recommendations: entries to add/remove/update

---

## Pitfalls To Avoid

1. **DO NOT** modify test files — audit only
2. **DO NOT** modify production code — registry audit is docs-only
3. **DO** capture collect-only output for evidence
4. **DO** note any selectors that reference tests blocked by Tier 0 (e.g., DB-AT-010)
5. **Environment Freeze:** No package installs

---

## If Blocked

1. If TEST_SUITE_INDEX.md is empty or malformed: Report as anomaly, check git history
2. If collect-only fails for environment reasons: Note the selector as "blocked_environment" rather than "orphan"

---

## Findings Applied

- **TESTING-003**: Use canonical selector patterns from authoritative sources
- **PROBE-FREEZE-001**: No new scripts — document audit only

---

## Pointers

- DB-AT-SUITE-CARE-001 implementation.md: `plans/active/DB-AT-SUITE-CARE-001/implementation.md:94-97` (Phase D.4 tasks)
- TEST_SUITE_INDEX.md: `docs/development/TEST_SUITE_INDEX.md`
- TESTING_GUIDE.md: `docs/TESTING_GUIDE.md`

---

## Next Up (optional)

If audit reveals significant gaps:
1. Create follow-up task to sync registries
2. Consider D.5 (Conformance Profile maintenance) as alternative

---

## Portfolio Context (for reference)

**Tier 0 Status:**
- ARCH-GRADIENT-FLOW-001: `blocked_pending_upstream` (escalation awaiting response)
- ARCH-SIM-CONSTRUCTION-001: `blocked_pending_environment`

**Tier 1 Status:**
- DB-AT-SUITE-CARE-001: `in_progress` (Phase D maintenance)
- Other Tier 1 items: done

**If upstream response arrives:** Interrupt D.4 and switch to ARCH-GRADIENT-FLOW-001 Phase B.7+
