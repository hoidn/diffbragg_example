# Input for Ralph (Loop i=179)

## Summary
Execute TORCH-CLI-BRIDGE-ROLLUP-001 Phase B — TORCH-BRIDGE-001 Closeout (D1-D4).

## BindingForRalph
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** roll-up member closeout

## SupervisorMode
Implementation (test execution + registry sync)

## Focus
TORCH-CLI-BRIDGE-ROLLUP-001 — CLI & Bridge Infrastructure Roll-up — Phase B (TORCH-BRIDGE-001 Closeout)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_nanobrag_bridge.py` (5 tests)
- `tests/dbex/test_nanobrag_bridge_configs.py` (20 tests)
- `tests/dbex/test_nanobrag_smoke.py` (3 tests)
- **Total:** 28 tests

## Artifacts
`plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T083000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (Plan-local probe policy): No new persistent scripts
  - Adherence: Using existing tests only, no new scripts
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Artifacts follow established patterns
  - Adherence: Pytest logs + collect-only logs routed to reports directory
- **TESTING-003** (Test registry synchronization): Update TESTING_GUIDE.md and TEST_SUITE_INDEX.md after test execution
  - Adherence: D3 task updates registries after tests pass
- No other findings directly applicable

## Pointers
- Roll-up implementation.md: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` (Phase B checklist lines 79-96)
- TORCH-BRIDGE-001 implementation.md: `plans/active/TORCH-BRIDGE-001/implementation.md` (Phase D checklist lines 61-66)
- fix_plan.md TORCH-BRIDGE-001: Not currently a dedicated section (tracked via roll-up)
- Exit criteria: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` lines 22-28

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs
  - Owner: CLAUDE.md
  - Classification: Test execution + docs/ledger updates only
- **Test Registry Sync**: Required after test execution
  - Owner: TESTING-003
  - Classification: Update TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md with bridge/config/smoke entries

---

## Do Now

**Focus:** TORCH-CLI-BRIDGE-ROLLUP-001 Phase B — TORCH-BRIDGE-001 Closeout

**Implement:** `plans/active/TORCH-BRIDGE-001/implementation.md::phase_d_closeout` + ledger/registry updates

**Validating Pytest Selector:** `tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py`

### Background
TORCH-BRIDGE-001 has Phases A-C complete (scaffolding, config hydration, smoke harness). Phase D is closeout: re-run tests, update ledgers, sync registries. All 28 tests should pass (last verified ~6 weeks ago per Phase A inventory).

### Phase B Tasks (TORCH-BRIDGE-001 D1-D4)

#### D1 — Re-run Bridge + Smoke Tests
Execute all 28 bridge/config/smoke tests with fresh logs:

```bash
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T083000Z
mkdir -p "$ART"
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py 2>&1 | tee "$ART/pytest_bridge.log"
```

**Expected:** 28/28 PASS

#### D2 — Update Ledgers
1. Update `plans/active/TORCH-BRIDGE-001/implementation.md`:
   - Mark Phase D (D1-D4) checklist items as checked
   - Add **Completed:** timestamp and **Artifacts:** path
   - Update Status: `in_progress` → `done`

2. Update roll-up `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md`:
   - Update member plan table: TORCH-BRIDGE-001 → "Phases A-D complete" / "Complete"
   - Mark Phase B checklist items (B1-B5) as checked
   - Add Phase B artifacts reference

#### D3 — Update Test Registries
1. Check `docs/TESTING_GUIDE.md` §2 for bridge/config/smoke test entries
   - If missing or outdated, add/update rows
   - Format: `| TORCH-BRIDGE-001 | tests/dbex/test_nanobrag_bridge*.py, test_nanobrag_smoke.py | 28 | PASS | 2025-12-08 |`

2. Check `docs/development/TEST_SUITE_INDEX.md` for TORCH-BRIDGE-001 row
   - If missing, add row in appropriate section
   - Include test counts and status

#### D4 — Capture Collect-Only Logs
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py 2>&1 | tee "$ART/collect_bridge.log"
```

Save to artifacts directory for registry verification.

#### D5 — Author Summary
Create `$ART/summary.md` with:
- Test execution results (28/X PASS)
- Ledger updates made
- Registry sync status
- Phase B completion status

---

## How-To Map

```bash
# Environment setup
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T083000Z
mkdir -p "$ART"

# D1: Run tests
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py 2>&1 | tee "$ART/pytest_bridge.log"

# D4: Collect-only
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py 2>&1 | tee "$ART/collect_bridge.log"

# D2-D3: Use Edit tool for ledger/registry updates
# D5: Use Write tool for summary.md
```

---

## Forbidden This Loop
- **No production code changes** — Closeout is test verification + docs only
- **No package installs** — Environment Freeze
- **No new persistent scripts** — PROBE-FREEZE-001

## Pitfalls To Avoid
1. **Don't skip test execution** — Fresh verification required for closeout
2. **Don't assume tests pass** — Verify 28/28 before marking done
3. **Check registry before updating** — Avoid duplicate entries
4. **Use correct artifacts path** — `2025-12-08T083000Z` not Phase A's `2025-12-08T073000Z`
5. **Mark both implementation.md files** — TORCH-BRIDGE-001 AND roll-up

## If Blocked
If tests fail:
1. Document failure in `$ART/error.md` with test name, error message, and stack trace
2. Do NOT mark Phase D complete
3. Note regression requires separate debugging loop
4. Update summary with "BLOCKED" status

---

## Exit Criteria Validation (Phase B)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Tests pass | 28/28 PASS | pytest_bridge.log |
| TORCH-BRIDGE-001 done | Status updated | implementation.md diff |
| Roll-up Phase B done | Checklist updated | roll-up implementation.md diff |
| Registry sync | TESTING_GUIDE + INDEX updated | File diffs |
| Collect-only captured | Log saved | collect_bridge.log exists |
| Summary authored | Phase B closure | summary.md |

---

## Output Artifacts Expected

1. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T083000Z/pytest_bridge.log`
2. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T083000Z/collect_bridge.log`
3. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T083000Z/summary.md`
4. Updated `plans/active/TORCH-BRIDGE-001/implementation.md` (Phase D marked complete)
5. Updated `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` (Phase B marked complete)
6. Updated `docs/TESTING_GUIDE.md` §2 (if needed)
7. Updated `docs/development/TEST_SUITE_INDEX.md` (if needed)

---

## Implement Target
`plans/active/TORCH-BRIDGE-001/implementation.md::phase_d_closeout` + ledger/registry sync

## Validating Pytest Selectors
`tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py`

---

## Next Up (optional)
If Phase B completes successfully:
- Proceed to Phase C: TORCH-CLI-003 Synchronization (C1-C4: re-run CLI tests, update checklists)
- Can potentially combine with Phase D (TORCH-CLI-004) for efficiency
