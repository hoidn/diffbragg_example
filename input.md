# Input for Ralph (Loop i=181)

## Summary
Complete TORCH-CLI-BRIDGE-ROLLUP-001 Phases D+E combined: sync TORCH-CLI-004 checklist (work already done) and close roll-up.

## BindingForRalph
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** roll-up closure (docs/ledger only)

## SupervisorMode
Implementation (checklist sync + closure)

## Focus
TORCH-CLI-BRIDGE-ROLLUP-001 — CLI & Bridge Infrastructure Roll-up — Phases D+E Combined

## Branch
integration

## Mapped Tests
- `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (2 tests)
- **Pre-verified:** 2/2 PASS (Galph verification this loop)

## Artifacts
`plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T100000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001**: No new persistent scripts
  - Adherence: Docs/ledger updates only
- No other findings directly applicable

## Pointers
- Roll-up implementation.md: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` (Phases D+E checklist)
- TORCH-CLI-004 implementation.md: `plans/active/TORCH-CLI-004/implementation.md`
- TORCH-CLI-004 completed work evidence: `plans/active/TORCH-CLI-004/reports/2025-11-04T222435Z/summary.md`
- Exit criteria evidence locations:
  - EC1: `docs/spec-db-interfaces.md:7-11`
  - EC2: `docs/config_crosswalk.md:5-155` (torch mapping sections)
  - EC3: `docs/architecture.md:33,141` (bridge responsibility)
  - EC4: Already satisfied (REPORT-NANOBRAG-STATUS-001 done 2025-12-08)

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs
  - Owner: CLAUDE.md
  - Classification: Docs/ledger updates only
- **Test Registry Sync**: Not needed (entries exist)
  - Owner: TESTING-003
  - Classification: Verification only

---

## Do Now

**Focus:** TORCH-CLI-BRIDGE-ROLLUP-001 Phases D+E (Combined Closure)

**Implement:** Checklist sync for TORCH-CLI-004 + roll-up closure documentation

**Validating Pytest Selector:** `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (already verified by Galph: 2/2 PASS)

### Background
- Phase C (TORCH-CLI-003 sync) completed successfully in prior loop (15/15 CLI tests pass)
- TORCH-CLI-004 work was completed November 2025 (see `reports/2025-11-04T222435Z/summary.md`)
- Tests already pass: 2/2 diagnostics tests confirmed this loop
- Only remaining work: update unchecked checklists and close roll-up

### Phase D Tasks (TORCH-CLI-004 Synchronization)

#### D1 — Verify Tests (PRE-VERIFIED)
Tests already verified by Galph:
```
tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata[cli_override-3.0] PASSED
tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata[external_lookup-5.0] PASSED
```
**ACTION:** Note verification in artifacts, no re-run needed.

#### D2 — Update TORCH-CLI-004 Implementation.md
Mark all checklist items as complete (work done Nov 2025):
- [ ] → [x] A1, A2, A3 (Phase A)
- [ ] → [x] B1, B2, B3 (Phase B)
- [ ] → [x] C1, C2, C3 (Phase C)
- Add **Completed:** 2025-11-04T222435Z
- Update Status: (none currently) → `done`

#### D3 — Update Roll-up Implementation.md Member Table
Update TORCH-CLI-004 row:
- Implementation Status: "Work complete" (already there)
- Checklist Status: "Checklist stale" → "Complete"

#### D4 — Mark Roll-up Phase D Complete
- [x] D1: Diagnostics test verified (2/2 PASS)
- [x] D2: TORCH-CLI-004 implementation.md updated
- [x] D3: Member table updated

### Phase E Tasks (Roll-up Closure)

#### E1-E4 — Verify Exit Criteria

| EC | Description | Evidence | Status |
|----|-------------|----------|--------|
| EC1 | CLI backend flag | `docs/spec-db-interfaces.md:7-11` | ✅ Verified |
| EC2 | Telemetry schema | `docs/config_crosswalk.md` torch sections | ✅ Verified |
| EC3 | Bridge responsibility | `docs/architecture.md:33,141` | ✅ Verified |
| EC4 | REPORT-NANOBRAG-STATUS-001 | Dependency done 2025-12-08 | ✅ Satisfied |

**ACTION:** Document verification in closure summary.

#### E5 — Update fix_plan.md
1. Update Execution Roadmap (line 58): `in_progress` → `done`
2. Add Attempts History entry with Phase D+E closure

#### E6 — Author Closure Summary
Create `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T100000Z/closure_summary.md`:
- Roll-up overview (3 member plans)
- Exit criteria matrix with evidence paths
- Phase completion timeline
- Final member plan status

#### E7 — Update Roll-up Implementation.md
- Mark Phase E checklist complete
- Update Status: `in_progress` → `done`
- Update artifacts index with Phase D-E paths

---

## How-To Map

```bash
# Artifacts directory
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T100000Z

# D2: Update TORCH-CLI-004 implementation.md via Edit tool
# D3: Update roll-up member table via Edit tool
# D4: Mark Phase D complete via Edit tool

# E5: Update fix_plan.md via Edit tool
# E6: Write closure_summary.md via Write tool
# E7: Update roll-up implementation.md via Edit tool
```

---

## Forbidden This Loop
- **No code changes** — Docs/ledger only
- **No package installs** — Environment Freeze
- **No new persistent scripts** — PROBE-FREEZE-001
- **No test execution** — Already verified by Galph

## Pitfalls To Avoid
1. **Don't skip TORCH-CLI-004 checklist update** — Implementation was done Nov 2025 but checklist never updated
2. **Use correct artifacts timestamp** — `2025-12-08T100000Z` (not Phase C's `090000Z`)
3. **Update BOTH implementation.md files** — TORCH-CLI-004 AND roll-up
4. **Include evidence paths in closure** — All EC must cite specific line numbers

## If Blocked
This is purely docs/ledger work. If any file access fails:
1. Document the error
2. Continue with remaining files
3. Note incomplete items in summary

---

## Exit Criteria Validation (Phases D+E)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| D1 Test verified | 2/2 PASS | Galph pre-verified |
| D2 CLI-004 updated | All [x] | implementation.md diff |
| D3 Member table updated | Complete | roll-up impl diff |
| E1-E4 EC verified | 4/4 ✅ | closure_summary.md |
| E5 fix_plan updated | done | fix_plan.md diff |
| E6 Closure authored | exists | closure_summary.md |
| E7 Roll-up done | Status=done | roll-up impl diff |

---

## Output Artifacts Expected

1. `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T100000Z/closure_summary.md`
2. Updated `plans/active/TORCH-CLI-004/implementation.md` (all phases marked complete)
3. Updated `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md` (Phases D+E complete, Status=done)
4. Updated `docs/fix_plan.md` (roll-up status → done)

---

## Next Up (optional)
If Phases D+E complete successfully, the roll-up is fully closed. Next focus candidates:
- DB-AT-SUITE-CARE-001 Phase D.2+ (regression monitoring)
- PERF-WARM-SIM-001 (if upstream Stage C path resolves)
- ARCH-STAGE-CONTEXT-CONSOLIDATION (Tier 2)
