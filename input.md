# Input for Ralph (Loop i=175)

## Summary
Execute ARCH-TELEMETRY-002 Phase C — Cleanup & Closure sweep to complete the initiative.

## BindingForRalph
- **ActionType:** review_or_housekeeping
- **DecisionStatus:** validated
- **InitiativeType:** architecture

## SupervisorMode
Docs (closure documentation + validation sweep)

## Focus
ARCH-TELEMETRY-002 — Telemetry & Probe Simplification — Phase C (Cleanup & Closure)

## Branch
integration

## Mapped Tests
- `pytest -v tests/architecture/test_telemetry_surfaces.py` (must PASS — validation of Phase B)
- `pytest -v tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis` (must PASS — no regression)
- `pytest -v tests/architecture/test_gradient_contracts.py` (must PASS — architecture suite sanity)

## Artifacts
`plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (Plan-local probe policy): No new probes; Phase C is closure only
  - Adherence: No scripts created; validation of existing enforcement
- **ARCH-STAGE-CTX-001/002** (Stage context ownership): Telemetry dict guardrails validated
  - Adherence: Exit criterion 4 already satisfied via Phase B
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Closure artifacts follow established patterns
  - Adherence: Artifacts routed to `reports/2025-12-08T000000Z/`

## Pointers
- Implementation plan: `plans/active/ARCH-TELEMETRY-002/implementation.md` (Phase C checklist)
- Telemetry charter: `docs/architecture/telemetry.md`
- Telemetry inventory: `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/telemetry_inventory.md`
- Phase B summary: `plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T220000Z/summary.md`
- Fix plan entry: `docs/fix_plan.md` lines 230-250
- Findings ledger: `docs/findings.md`

---

## ARCH Contracts (mandatory)
- **ARCH-STAGE-CTX-001/002** (Stage Context Ownership): Already validated in Phase B
  - Owner: `dbex/refinement/telemetry_collectors.py`, `dbex/refinement/interfaces.py`
  - Classification: Closure — no new enforcement needed
- **PROBE-FREEZE-001** (Probe Policy): Already validated in Phase B
  - Owner: `prompts/supervisor.md::diagnostic_script_policy`, `tests/architecture/test_probe_contracts.py`
  - Classification: Closure — no new enforcement needed

---

## Do Now

**Focus:** ARCH-TELEMETRY-002 Phase C — Cleanup & Closure

### Background
- Phase A complete (i=173, commit 744cea60): Charter, inventory, manifest section authored
- Phase B complete (i=174, commit 4d8943a6): Enforcement test, supervisor policy, probe contracts cross-ref

**Exit Criteria Status:**
1. ✅ Charter exists + linked in docs/index.md
2. ✅ Inventory exists (manifest + reports)
3. ✅ Enforcement test exists + passes (3 tests)
4. ✅ Supervisor policy + probe contracts updated
5. ⏳ Partial — tests pass, but `docs/findings.md` guardrail update pending

### Phase C Tasks

#### C1 — Review Telemetry Inventory for Unused Fields

Using the Phase A inventory (`plans/active/ARCH-TELEMETRY-002/reports/2025-12-07T215000Z/telemetry_inventory.md`), identify any telemetry fields that:
- Are NOT referenced in Spec-DB (`docs/spec-db-*.md`)
- Are NOT consumed by active tests
- Are NOT documented in `docs/data_dependency_manifest.md`
- Are NOT used by active plan artifacts

**Expected outcome:** Either:
- (a) Find at least one unused field and document it as deprecated (per Exit Criterion 2), OR
- (b) Confirm all fields are in use with evidence (grep/references)

If all fields are in active use, document this finding and mark Exit Criterion 2 as "all fields in use — no deprecation needed."

**Output:** `reports/2025-12-08T000000Z/field_audit.md`

#### C2 — Update docs/findings.md with Guardrail Entry

Add a new finding entry for ARCH-TELEMETRY-002 guardrails:

```markdown
### TELEMETRY-GUARD-001: Telemetry Ownership Enforcement (Active)
**Added:** 2025-12-08 (ARCH-TELEMETRY-002 Phase C)
**Status:** Active
**Consumers:** [ARCH-TELEMETRY-002], test selectors `tests/architecture/test_telemetry_surfaces.py`

**Description:** Telemetry surfaces in `dbex/` are governed by the ownership charter at `docs/architecture/telemetry.md`. Primary owners (interfaces.py, telemetry_collectors.py, writer.py) define production telemetry; secondary owners (telemetry_baseline.py, artifacts.py, mapping.py) define diagnostics. New telemetry fields must follow expansion rules (§5) and be validated by `test_telemetry_surfaces.py`.

**Code References:**
- Enforcement test: `tests/architecture/test_telemetry_surfaces.py`
- Charter: `docs/architecture/telemetry.md`
- Supervisor policy: `prompts/supervisor.md::telemetry_charter_compliance`

**Remediation:** Before adding telemetry fields:
1. Check charter §2-3 for owner module
2. Follow expansion rules in §5
3. Run `pytest -v tests/architecture/test_telemetry_surfaces.py`
```

**Output:** Edit `docs/findings.md`

#### C3 — Run Architecture Test Slice

Run the full architecture test slice to validate no regressions:

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/architecture/test_telemetry_surfaces.py \
       tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis \
       tests/architecture/test_gradient_contracts.py \
       --tb=short | tee $ARTIFACT_DIR/architecture_test_slice.log
```

**Expected:** All tests PASS

**Output:** `reports/2025-12-08T000000Z/architecture_test_slice.log`

#### C4 — Update fix_plan.md Status

Update ARCH-TELEMETRY-002 status from `in_progress` to `done`:
- Line 97 (Execution Roadmap): Update status
- Line 232: Update Status field

Add final Attempts History entry:
```
* 2025-12-08T000000Z (Loop i=175, Ralph) — **Phase C complete** (closure): C1 field audit (all fields in use OR 1+ deprecated), C2 findings.md TELEMETRY-GUARD-001 added, C3 architecture test slice PASSED (X tests), C4 status updated to done. **ALL EXIT CRITERIA MET**: Charter ✅, Inventory ✅, Enforcement test ✅, Policy updated ✅, Tests pass + findings updated ✅. Initiative ready for archive. Artifacts: `plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/`.
```

**Output:** Edit `docs/fix_plan.md`

#### C5 — Author Summary

Create `reports/2025-12-08T000000Z/summary.md` with:
1. Phase C task completion status
2. Exit criteria validation (all 5)
3. Test results
4. Archive readiness assessment

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ARTIFACT_DIR=plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z

# C1: Audit telemetry inventory
# Read inventory at reports/2025-12-07T215000Z/telemetry_inventory.md
# Search for each field in spec-db, tests, manifest
# Write findings to $ARTIFACT_DIR/field_audit.md

# C2: Add findings.md entry
# Use Edit tool to add TELEMETRY-GUARD-001 entry

# C3: Run architecture test slice
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
pytest -v tests/architecture/test_telemetry_surfaces.py \
       tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis \
       tests/architecture/test_gradient_contracts.py \
       --tb=short 2>&1 | tee $ARTIFACT_DIR/architecture_test_slice.log

# C4: Update fix_plan.md
# Use Edit tool to update status and add Attempts History

# C5: Write summary
# Use Write tool to create summary.md
```

---

## Forbidden This Loop
- **No telemetry schema changes** — Closure only; do not modify production telemetry
- **No new probes** — Phase C is validation/closure
- **No implementation code changes** — Docs and tests only

## Pitfalls To Avoid
1. **Don't invent deprecations** — Only mark fields as deprecated if grep shows no consumers
2. **Don't skip findings.md update** — Exit criterion 5 requires this
3. **Keep audit evidence concrete** — Document grep commands and results
4. **Run full test slice** — Don't shortcut with single test

## If Blocked
If field audit is inconclusive:
1. Document the ambiguity in `field_audit.md`
2. Mark Exit Criterion 2 as "all fields appear in use — no deprecation candidates identified"
3. Proceed with C2-C5 regardless
4. Note in summary that future audit may identify deprecation candidates

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| EC1 | Charter linked in docs/index.md | Already satisfied (Phase B) |
| EC2 | At least one field deprecated OR all in use documented | C1 field_audit.md |
| EC3 | Enforcement test passes | C3 test_slice.log |
| EC4 | Supervisor policy + probe contracts updated | Already satisfied (Phase B) |
| EC5 | Tests pass + findings.md updated | C2 + C3 |

---

## Output Artifacts Expected

1. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/field_audit.md`
2. `docs/findings.md` (edited — TELEMETRY-GUARD-001 added)
3. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/architecture_test_slice.log`
4. `docs/fix_plan.md` (edited — status updated to done)
5. `plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/summary.md`

---

## Implement Target
`docs/findings.md::TELEMETRY-GUARD-001` + `docs/fix_plan.md` status update

## Validating Pytest Selectors
```bash
pytest -v tests/architecture/test_telemetry_surfaces.py tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis tests/architecture/test_gradient_contracts.py
```
