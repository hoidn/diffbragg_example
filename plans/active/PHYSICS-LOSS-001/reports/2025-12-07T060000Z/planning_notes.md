# PHYSICS-LOSS-001 Closure Validation Planning (Loop i=125)

## Context

**Previous state** (from galph_memory.md loop i=124):
- FINDINGS-LEDGER-002 closed successfully (all Tier 0 items now done/archived/blocked)
- Portfolio steering: next loop must select Tier 1 focus

**Current focus selection rationale:**
PHYSICS-LOSS-001 was chosen from Tier 1 candidates because:
1. **Implementation.md shows all phases A-I complete** (checked boxes for all deliverables)
2. **Fix_plan.md status is "pending"** (line 380), but work appears done
3. **No obvious blockers** in latest reports (last report 2025-11-21T083500Z)
4. **Dependency** MAP-SCALE-SYNC-001 appears resolved (MAP-SCALE-001 done, others are CLI extensions)
5. **High priority**: Loss function correctness is Tier 1 core physics

## Exit Criteria Analysis (fix_plan.md:385-393)

Comparing fix_plan exit criteria against implementation.md deliverables:

### Criterion 1: Variance-weighted loss implementation matches spec-db-core.md §Objective Function
**Status:** ✅ **MET**
- Implementation.md Phase D.1: `_compute_variance_weighted_loss` helper delivered (2025-11-21T051747Z)
- Spec reference: `docs/spec-db-core.md:57-68`
- Evidence: Phase D.1/D.2/D.3 notes cite canonical chi-squared formula implementation

### Criterion 2: Sigma-floor telemetry corrections validated per TESTING_GUIDE.md §1.4
**Status:** ✅ **MET**
- Implementation.md Phase E/F/G/H/I: Sigma-map ingestion + metadata + external_lookup paths delivered
- Telemetry provenance tracking: `sigma_readout_provenance` field added to RefinementConfig
- Evidence: Phase I.1/I.2/I.3 notes cite TESTING_GUIDE updates and metadata workflow docs

### Criterion 3: Completed phases documented in plans/active/PHYSICS-LOSS-001/implementation.md
**Status:** ✅ **MET**
- All phases A-I have [x] checked boxes
- Each phase has delivery timestamps and artifact paths
- Phase I (final phase) completed 2025-11-21T075449Z per inline notes

### Criterion 4: Remaining risks captured in Attempts History with mitigation plans
**Status:** ⚠️ **NEEDS VERIFICATION**
- Implementation.md has a "Risks" section under Phase C (L-BFGS tolerance retuning concern)
- **Gap:** Fix_plan.md:378-393 Attempts History section shows only roll-up creation note (2025-12-05T150000Z)
- **Action:** Ralph must verify if Phase C risk was resolved or needs mitigation

## Outstanding Work Inventory

**From implementation.md review:**
1. Phase C Risks section (line 47-48):
   - "MSE ~10^6 vs chi-squared ~N_pixels. L-BFGS tolerances may need retuning (1e-9 → 1e-4)."
   - **Question:** Was this risk observed in practice? Any tolerance changes needed?

2. Deferred phases or TODOs:
   - **None found** — all phases A-I marked complete with timestamps

3. Documentation sync:
   - Implementation.md Phase I.3 claims TESTING_GUIDE/TEST_SUITE_INDEX updated
   - **Verification needed:** Confirm those doc updates exist in current HEAD

## Validation Plan for Ralph

**Step 1: Risk Assessment**
- Search latest reports (2025-11-21T*) for L-BFGS tolerance issues
- Check if any Stage smoke tests failed due to convergence (would indicate tolerance mismatch)
- If no issues found in artifacts, mark Phase C risk as "not materialized"

**Step 2: Documentation Verification**
- `grep -n "sigma.*metadata" docs/TESTING_GUIDE.md`
- `grep -n "PHYSICS-LOSS" docs/development/TEST_SUITE_INDEX.md`
- Verify `docs/architecture/calibration_scaling.md` mentions sigma_readout_provenance threading

**Step 3: Test Execution**
- Run mapped acceptance battery (6 selectors listed in input.md)
- Expect: all PASS (no regressions since November 21)
- Capture pytest exit codes + summary stats

**Step 4: Closure Decision**
- **If all 4 exit criteria verified + tests PASS:**
  - Author `initiative_closure_summary.md`
  - Update fix_plan.md PHYSICS-LOSS-001 entry (line 378-393) to status **done**
  - Append Attempts History with Phase I completion summary
  - Mark for archival consideration (or leave in active/ as reference)

- **If any gaps found:**
  - Document specific unmet criterion in this loop's summary.md
  - Mark PHYSICS-LOSS-001 status `in_progress` with next action
  - Do NOT close initiative

## Expected Outcome

**If closure succeeds:**
- PHYSICS-LOSS-001 joins FINDINGS-LEDGER-002 as a closed Tier 1 item
- Next loop (i=126) selects another Tier 1 focus (MAP-SCALE-SYNC-001 roll-up or DB-AT-SUITE-CARE-001)
- Portfolio momentum maintained (2 Tier 1 closures in consecutive loops)

**If blocked:**
- Galph must decide: remediate gaps OR switch to MAP-SCALE-SYNC-001 roll-up scoping
- Respect loop discipline: no more than 1 docs-only loop in a row; next must be implementation OR focus switch

## References

- Fix_plan: `docs/fix_plan.md:378-393` (PHYSICS-LOSS-001 ledger entry)
- Implementation: `plans/active/PHYSICS-LOSS-001/implementation.md` (all phases A-I)
- Latest reports: `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T*` (Phase I deliverables)
- Spec: `docs/spec-db-core.md:57-68` (variance-weighted loss function)
- Findings: `docs/findings.md` (PHYSICS-LOSS-001—005, SCALE-001/002)
