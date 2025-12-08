# Input for Ralph (Loop i=172)

## Summary
Execute DB-AT-SUITE-CARE-001 Phase D.1 — Establish regression monitoring cadence for acceptance test suite.

## BindingForRalph
- **ActionType:** review_or_housekeeping
- **DecisionStatus:** N/A (maintenance task)
- **InitiativeType:** harness

## SupervisorMode
Docs (maintenance workflow documentation)

## Focus
DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep — Phase D.1 (Regression Monitoring)

## Branch
integration

## Mapped Tests
- `pytest -v tests -k "DB_AT_002 or DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024"` (Workflow Integration + Determinism profiles)
- Note: DB-AT-010 skipped (blocked_pending_upstream via ARCH-GRADIENT-FLOW-001)

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z/`

## Findings Applied (Mandatory)
- **TESTING-003** (Acceptance test registry maintenance): All DB-AT selector changes must sync with TEST_SUITE_INDEX.md
  - Adherence: Regression sweep will validate registry accuracy
- **RUNTIME-001** (Runtime execution guardrails): Pytest commands must use canonical environment flags
  - Adherence: Documented sweep command includes `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Sweep logs must be archived
  - Adherence: Phase D.1 specifies `reports/<timestamp>/regression_sweeps/` path

## Pointers
- Implementation plan: `plans/active/DB-AT-SUITE-CARE-001/implementation.md` (Phase D section)
- Phase C closure: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T040000Z/summary.md`
- TEST_SUITE_INDEX.md: `docs/development/TEST_SUITE_INDEX.md`
- TESTING_GUIDE.md: `docs/TESTING_GUIDE.md`

---

## ARCH Contracts (mandatory)
- **TESTING-003** (Acceptance Test Registry): DB-AT selectors must be tracked in TEST_SUITE_INDEX.md
  - Owner: `docs/development/TEST_SUITE_INDEX.md`
  - Classification: N/A (maintenance task)

---

## Do Now

**Focus:** DB-AT-SUITE-CARE-001 Phase D.1 — Regression Monitoring Cadence

### Background
Phase C is complete (Workflow Integration cluster certified, 12/13 tests PASS + 1 skip). Phase D focuses on long-term maintenance:
- D1: Regression monitoring (this loop)
- D2: Future DB-AT onboarding (deferred)
- D3: Conformance profile evolution (deferred)
- D4: TEST_SUITE_INDEX.md hygiene (deferred)
- D5: Lessons learned archive (deferred)

### Phase D.1 Tasks

#### D.1.1 — Execute baseline regression sweep

Run the acceptance test suite with canonical flags and capture output:

```bash
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z
mkdir -p $ARTIFACT_DIR/regression_sweeps

# Workflow Integration + Determinism profiles (excludes blocked DB-AT-010)
pytest -v tests -k "DB_AT_002 or DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024" 2>&1 | tee $ARTIFACT_DIR/regression_sweeps/sweep_2025_12_07.log
```

**Expected:** 14/14 PASS (or 13 PASS + 1 skip if DB-AT-024 artifact dir unset)

#### D.1.2 — Document regression sweep cadence

Create `plans/active/DB-AT-SUITE-CARE-001/regression_cadence.md` with:
1. **Purpose:** Detect acceptance test regressions (gradcheck failures, bbox/mask semantic drift)
2. **Frequency:** Monthly (or on-demand after significant refactors)
3. **Scope:** DB-AT-002/020/021/022/023/024 (DB-AT-010 when unblocked)
4. **Command:** Canonical pytest command with environment flags
5. **Artifact location:** `reports/<YYYY-MM-DD>/regression_sweeps/`
6. **Pass criteria:** All tests PASS (or documented xfail/skip)
7. **Failure protocol:** Create bug report, link to relevant plan, escalate if blocker

#### D.1.3 — Update implementation.md

Mark D.1 complete in `plans/active/DB-AT-SUITE-CARE-001/implementation.md`:
- Check the D.1 task checkbox
- Add timestamp and artifact reference

#### D.1.4 — Author summary

Output: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z/summary.md`

Include:
1. Regression sweep results (pass/fail counts)
2. Cadence document location
3. Any test failures or anomalies observed
4. Next Phase D task recommendation

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z

# Create artifacts directory
mkdir -p $ARTIFACT_DIR/regression_sweeps

# D.1.1: Run regression sweep
pytest -v tests -k "DB_AT_002 or DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024" 2>&1 | tee $ARTIFACT_DIR/regression_sweeps/sweep_2025_12_07.log

# D.1.2: Create regression_cadence.md via Write tool

# D.1.3: Update implementation.md via Edit tool

# D.1.4: Write summary.md via Write tool
```

---

## Forbidden This Loop
- **No new test authoring** — This is maintenance/documentation
- **Do not run DB-AT-010** — Blocked pending ARCH-GRADIENT-FLOW-001 (upstream nanobrag_torch fix)
- **Do not modify production code** — Phase D is harness/docs only

## Pitfalls To Avoid
1. **Environment flags** — Always use `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
2. **Artifact structure** — Follow existing `reports/<timestamp>/` pattern
3. **Skip vs fail** — DB-AT-024 may skip if `DBAT024_ARTIFACT_DIR` not set; this is expected
4. **Do not over-engineer** — Simple markdown cadence doc is sufficient

## If Blocked
If regression sweep reveals unexpected failures:
1. Document the failure signature
2. Check if it's a known blocker (ARCH-GRADIENT-FLOW-001)
3. If new regression, create a problems.md entry and escalate next loop
4. Complete D.1.2-D.1.4 regardless (cadence doc is valuable even if sweep has failures)

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| D.1.1 complete | Regression sweep executed | Log exists in regression_sweeps/ |
| D.1.2 complete | Cadence doc exists | regression_cadence.md created |
| D.1.3 complete | implementation.md updated | D.1 checkbox marked |
| D.1.4 complete | summary.md exists | File in artifacts dir |

---

## Output Artifacts Expected

1. `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z/regression_sweeps/sweep_2025_12_07.log`
2. `plans/active/DB-AT-SUITE-CARE-001/regression_cadence.md`
3. `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z/summary.md`

---

## Context: Portfolio Status

### Tier 0 (Exhausted)
- ARCH-GRADIENT-FLOW-001: **blocked_pending_upstream** (Jacobian mismatch in nanobrag_torch, escalation filed)
- ARCH-SIM-CONSTRUCTION-001: **blocked_pending_environment**
- ARCH-REFACTOR-001: **blocked_pending_architecture**
- Others: done/archived

### Tier 1
- DB-AT-SUITE-CARE-001: **in_progress** (Phase C complete, Phase D.1 this loop)
- PHYSICS-LOSS-CONSISTENCY: pending (blocked by ARCH-REFACTOR-001)
- Others: pending with dependencies

### Why This Focus
With Tier 0 exhausted and no unblocked implementation items, maintenance tasks provide the best ROI:
1. Establishes regression monitoring infrastructure
2. Documents cadence for future operators
3. Validates current test suite health
4. Advances DB-AT-SUITE-CARE-001 toward closure

---

## Implement Target
N/A — This is review_or_housekeeping (docs + test execution for monitoring)

## Validating Pytest Selector
`pytest -v tests -k "DB_AT_002 or DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024"` (14 expected PASS or 13 PASS + 1 skip)
