# Input — Loop i=188 (Ralph)

## Summary
Execute TORCH-REFINE-CLEANUP-001 Phase C: run smoke tests, archive artifacts, mark roll-up done.

## Focus
TORCH-REFINE-CLEANUP-001 — Stage A/B/C Refinement Probes Consolidation Roll-up

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py` (6 tests: Stage A expansion, Stage B modifiers, Stage C microslip)

## Artifacts
`plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T091543Z/`

---

## Do Now

**Focus:** TORCH-REFINE-CLEANUP-001 — Phase C closure

**Implement:** `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md::Phase_C` (C1-C3 checkboxes)

**Validating selector:** `tests/dbex/test_torch_refine_smoke.py` (expect 6/6 PASS or 6/6 collected with minimal skip)

**Artifacts path:** `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T091543Z/`

### Tasks

| ID | Task | Deliverable |
|----|------|-------------|
| C1 | Run Stage A/B smoke tests | `pytest_refine_smoke.log` with PASS/FAIL status |
| C2 | Archive Phase C artifacts | Log + summary files in reports directory |
| C3 | Mark roll-up done | Update fix_plan.md (Execution Roadmap line 55 + detailed section status) |
| C4 | Update implementation.md | Mark Phase C checkboxes complete |
| C5 | Author summary.md | Turn Summary block for this loop |

---

## How-To Map

### C1: Run smoke tests
```bash
KMP_DUPLICATE_LIB_OK=TRUE \
  DBEX_SMOKE_DETECTOR_SIZE=small \
  pytest -v tests/dbex/test_torch_refine_smoke.py \
  2>&1 | tee plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T091543Z/pytest_refine_smoke.log
```

Expected: 6/6 PASS (or 6 collected with minimal skips due to environment). The archive operation (moving TORCH-REFINE-004) should not affect test execution since tests import from `dbex/` and `tests/`, not from `plans/active/`.

### C3: fix_plan.md updates
1. Execution Roadmap line ~55: Change status from `in_progress` to `done`
2. Detailed section (~line 388): Update status from `in_progress (Phase B complete)` to `done (Phase C complete)`
3. Add Attempts History entry for this loop

### C4: implementation.md updates
Mark checkboxes:
- [x] C1: Run relevant test selectors (Stage A/B smoke)
- [x] C2: Archive artifacts under reports directory
- [x] C3: Mark roll-up done if no actionable work remains

---

## Pitfalls To Avoid

1. **DO** use `DBEX_SMOKE_DETECTOR_SIZE=small` for quick smoke validation (full-detector is not required for regression check)
2. **DO** capture pytest output to log file in artifacts directory
3. **DO NOT** modify test files or production code — this is docs/ledger closure only
4. **DO NOT** run gradcheck tests — only smoke selectors needed
5. **DO** verify 6 tests collected before concluding
6. **DO** update BOTH Execution Roadmap AND detailed section in fix_plan.md
7. **Environment Freeze:** No package installs. If tests fail due to import errors, document the failure and mark as regression to investigate.

---

## If Blocked

1. If smoke tests fail with regressions, capture the failure log and do NOT mark as done
2. Document the regression in summary.md and update fix_plan.md with blocked status
3. Create a follow-on item in the Revive Priority Queue if needed

---

## Findings Applied

- **TESTING-003**: Use canonical pytest selectors from TESTING_GUIDE.md
- **PROBE-FREEZE-001**: No new probe scripts — use existing test infrastructure
- **REFINE-001/002**: Stage A nucleus telemetry and baseline gates are in scope for smoke validation

---

## Pointers

- implementation.md: `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md:59-63` (Phase C checklist)
- fix_plan.md Execution Roadmap: `docs/fix_plan.md:55` (TORCH-REFINE-CLEANUP-001 status)
- fix_plan.md detailed section: `docs/fix_plan.md:386-408`
- Phase B summary: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T200000Z/summary.md`
- Member plan audit: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/member_plan_status_audit.md`

---

## Next Up (optional)

If Phase C completes successfully and time permits:
1. **TORCH-REFINE-002D** (HIGH priority revive): P2.1 xfail removal work
2. **DB-AT-SUITE-CARE-001** Phase D.2: Next regression cadence check
