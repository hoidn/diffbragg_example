### Turn Summary

Completed MAP-SCALE-005 Phase A (CLI refined telemetry enforcement reality check): discovered enforcement already implemented at dbex/refine_one.py:382-389, fully compliant with spec-db-workflow.md:47. CLI fails fast when --refined-mtz load fails (no silent fallback), telemetry correctly records hkl_source="raw" when flag omitted. Phase B scope revised from "implement enforcement" to "validate and document existing enforcement" (Option A: add regression test + update ARCH-CONTRACT-CALIBRATION-001, OR Option B: close as already satisfied). Artifacts: plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/ (fallback_reproduction.md, spec_citations.md, guard_design.md, summary.md).

---

# MAP-SCALE-005 Phase A Summary: CLI Refined Telemetry Enforcement Reality Check

## Executive Summary

**Phase A Goal:** Reproduce current CLI fallback behavior when refined MTZ is missing, gather spec citations, and design guard for fail-fast enforcement.

**Key Finding:** **The enforcement is already implemented.** The CLI fails fast when `--refined-mtz` is provided but cannot be loaded, fully complying with spec-db-workflow.md:47 normative requirements. This discovery fundamentally changes Phase B scope from "implement enforcement" to "validate and document existing enforcement."

## Phase A Tasks Completed

### A1: Reality Check ✅

**Objective:** Reproduce CLI behavior when `--refined-mtz` points to a missing file.

**Outcome:**
- **Missing refined MTZ:** CLI raises `RuntimeError` immediately; no simulation, no HDF5 output, no silent fallback
- **No refined MTZ flag:** CLI uses raw MTZ from `-z` flag; telemetry correctly records `hkl_source="raw"`
- **Error message quality:** Clear, actionable, normative ("MUST be consumed")

**Evidence:** `fallback_reproduction.md` (stdout logs, HDF5 telemetry inspection)

**Implication:** The spec_change initiative assumption (silent fallback exists) is **incorrect**. Enforcement is already present.

### A2: Spec Citations ✅

**Objective:** Extract normative spec language supporting fail-fast policy.

**Outcome:**
- **Primary citation:** spec-db-workflow.md:47 — "fail if refined requested but missing"
- **Supporting citation:** spec-db-workflow.md:34 — "refined MTZ, when requested, SHALL be consumed or the run SHALL fail fast (no silent fallback to raw)"
- **Enforcement pattern precedent:** spec-db-workflow.md:46 (sigma_readout fail-fast)

**Compliance Status:** ✅ **FULLY COMPLIANT**
- Current implementation at `dbex/refine_one.py:382-389` matches normative requirements exactly

**Evidence:** `spec_citations.md` (extracted citations, compliance matrix)

**Implication:** No spec gap exists. The spec already requires the behavior that is already implemented.

### A3: Guard Design ✅

**Objective:** Define failure surfaces and assess error message quality.

**Outcome:**
- **Guard location:** `dbex/refine_one.py:375-393` (optimal placement: after sigma, before simulation)
- **Failure surfaces identified:** 6 surfaces (file not found, parse failure, column missing, empty data, iotbx import, telemetry downgrade)
- **Telemetry downgrade:** **Prevented by design** (exception raised before telemetry write)
- **Error message assessment:** ✅ Production-quality (context + diagnostic + policy + guidance)

**Evidence:** `guard_design.md` (failure taxonomy, exception flow, message analysis)

**Implication:** Guard design is robust, well-positioned, and spec-aligned. No architectural changes needed.

### A4: Planning Summary (This Document)

**Objective:** Consolidate findings and outline Phase B scope.

**Status:** ✅ Complete

## Critical Discovery: Enforcement Already Implemented

### Original Initiative Assumption

The MAP-SCALE-005 initiative was predicated on:

1. **Assumed behavior:** CLI silently falls back to raw MTZ when `--refined-mtz` load fails
2. **Assumed gap:** No enforcement of SCALE-007 telemetry integrity at CLI layer
3. **Assumed work:** Implement fail-fast guard to prevent telemetry downgrade

### Reality (Discovered in Phase A)

1. **Actual behavior:** CLI fails fast with clear error when `--refined-mtz` load fails
2. **Actual enforcement:** Guard implemented at `dbex/refine_one.py:382-389` since (unknown commit)
3. **Actual gap:** Documentation drift in ARCH-CONTRACT-CALIBRATION-001 (states "falls back silently")

### Hypothesis for Drift

**Possible explanations:**

1. **Initiative authored before enforcement implemented:** Guard may have been added during SCALE-007 / TORCH-API-ALIGN-001 work
2. **ARCH-CONTRACT not updated after implementation:** Documentation lag
3. **Test harness focus vs CLI focus:** SCALE-007 finding focused on test harness enforcement; CLI enforcement may have been implemented proactively but not surfaced in findings

**Next action:** Review git history for `dbex/refine_one.py:382-389` to determine when guard was added and whether it was documented.

## Revised Phase B Scope Options

### Option A: Minimal Validation & Documentation (Recommended)

**Rationale:** Enforcement exists and is spec-compliant; focus on ensuring it stays that way.

**Scope:**

1. **Regression test addition** (`tests/dbex/test_cli_enforcement.py`):
   - Test: `test_refined_mtz_missing_file_fails_fast`
   - Verify `RuntimeError` raised with expected message
   - Verify no HDF5 output written
   - Verify telemetry reports `hkl_source="raw"` when flag omitted

2. **ARCH-CONTRACT update** (`docs/architecture_contracts.md` or inline in code):
   - **ARCH-CONTRACT-CALIBRATION-001:** Revise description from "falls back silently" to "fails fast per spec-db-workflow.md:47"
   - Add reference to guard implementation (`dbex/refine_one.py:382-389`)

3. **Findings documentation** (`docs/findings.md`):
   - Add finding: "CLI refined MTZ enforcement already complies with SCALE-007 intent; fail-fast guard at refine_one.py:382-389 prevents telemetry downgrade"
   - Link to this Phase A summary

4. **Test SCALE-007 compliance claim:**
   - Confirm that existing guard satisfies SCALE-007 finding intent
   - If yes, mark SCALE-007 as "satisfied by CLI guard" and test harness enforcement
   - If no, identify delta and add to findings

**Deliverables:**
- 1 new test module (~50 lines)
- 2-3 doc updates (ARCH-CONTRACT, findings.md)
- Validation report (confirm SCALE-007 compliance)

**Estimated effort:** 1-2 engineer loops (low complexity, docs-focused)

**Risk:** Low (no production code changes; pure validation/documentation)

### Option B: Close Initiative as Already Satisfied (Alternative)

**Rationale:** Phase A confirmed all normative requirements are met; remaining work is standard test/doc hygiene.

**Scope:**
- Close MAP-SCALE-005 as "already satisfied by existing implementation"
- Transfer remaining work to:
  - **DB-AT-SUITE-CARE-001** (regression test addition)
  - **ARCH-DOC-SYNC-001** (ARCH-CONTRACT update, if such an initiative exists)
  - **Findings consolidation** (ad-hoc docs update)

**Deliverables:**
- Closure report referencing this Phase A summary
- Backlog items for test/doc hygiene

**Estimated effort:** 0 engineer loops for MAP-SCALE-005 (close immediately)

**Risk:** Low (work gets done via other initiatives)

### Option C: Full Implementation Loop (NOT Recommended)

**Rationale:** Treat Phase A as exploratory; proceed with original plan to "implement enforcement."

**Problems:**
- **Duplicates existing code:** Guard already exists at `refine_one.py:382-389`
- **Violates pragmatism principle:** No value in replacing working, spec-compliant code
- **Breaks incremental progress:** Rework introduces regression risk for zero benefit

**Recommendation:** ❌ **DO NOT pursue Option C**

## Risks & Mitigations

### Risk 1: Guard Removal in Future Refactor

**Scenario:** Future developer removes try-except block, thinking it's "defensive programming clutter."

**Mitigation:**
- Add regression test (Option A, task 1)
- Document guard rationale in comments with spec citation
- Add ARCH-CONTRACT enforcement test under `tests/architecture/` if Option A pursued

**Likelihood:** Low (guard has clear SCALE-007 comment)

**Impact:** High (silent telemetry downgrade breaks parity tests)

**Priority:** Medium (test addition strongly recommended)

### Risk 2: Documentation Drift Persists

**Scenario:** ARCH-CONTRACT-CALIBRATION-001 continues to claim "silent fallback" despite guard existence.

**Mitigation:**
- Update ARCH-CONTRACT in Phase B (Option A, task 2)
- Add cross-reference from code to ARCH-CONTRACT

**Likelihood:** High (already drifted)

**Impact:** Medium (misleading docs, but no functional issue)

**Priority:** High (docs update required)

### Risk 3: SCALE-007 Intent Misalignment

**Scenario:** SCALE-007 intended telemetry-level enforcement (test harness), not CLI-level prevention.

**Mitigation:**
- Review SCALE-007 finding intent with stakeholders
- Confirm that CLI fail-fast is **stronger** than test harness detection and satisfies the intent
- Document finding extension in `docs/findings.md`

**Likelihood:** Low (fail-fast is strictly better than post-hoc detection)

**Impact:** Low (no functional gap; clarification needed)

**Priority:** Medium (validation step in Option A, task 4)

## Environment Freeze Compliance

**Phase A Compliance:** ✅ **FULL COMPLIANCE**
- No packages installed or upgraded
- All reproduction used existing fixtures and CLI
- Only planning artifacts written (markdown docs)

**Phase B Compliance (Option A):**
- No production code changes required (guard already exists)
- Test addition uses existing pytest framework
- Doc updates are text-only

**Phase B Compliance (Option C, if pursued):**
- Would require production edit to replace existing guard
- ⚠️ **Risk:** Regression if new guard diverges from current implementation
- ❌ **Not recommended**

## Backward Compatibility

**Current Behavior (Preserved):**
- `--refined-mtz /valid/path.mtz`: Loads refined MTZ, sets `hkl_source="refined"`
- `--refined-mtz /missing/path.mtz`: Fails fast with `RuntimeError`
- No `--refined-mtz` flag: Uses raw MTZ from `-z`, sets `hkl_source="raw"`

**Phase B Impact (Option A):**
- No behavior changes
- Regression test codifies current behavior
- ✅ **Fully backward compatible**

**Phase B Impact (Option C, if pursued):**
- Replacing guard could introduce subtle error message changes
- Risk of breaking existing error-handling scripts (if any)
- ⚠️ **Potential compatibility break**

## Phase B Readiness Checklist

### For Option A (Recommended)

- [ ] Git history review: Determine when guard was added (`git log -p dbex/refine_one.py` for lines 382-389)
- [ ] Stakeholder confirmation: Verify Option A scope aligns with initiative goals
- [ ] Test design: Draft pytest selector for `test_refined_mtz_missing_file_fails_fast`
- [ ] ARCH-CONTRACT text: Draft revised description for CALIBRATION-001
- [ ] SCALE-007 validation: Confirm CLI guard satisfies finding intent

### For Option B (Alternative)

- [ ] Stakeholder sign-off: Confirm closure acceptable
- [ ] Backlog creation: Transfer test/doc tasks to other initiatives
- [ ] Closure report: Publish Phase A summary as final deliverable

### Blockers (None Identified)

All required information gathered in Phase A. No dependencies on external work or environment changes.

## Recommendations

### Primary Recommendation: Pursue Option A

**Rationale:**
1. **Low effort, high value:** 1-2 loops to add regression coverage and fix doc drift
2. **Completes initiative cleanly:** Validates spec compliance, documents existing enforcement
3. **Prevents regression:** Test coverage guards against future guard removal
4. **Aligns with initiative type:** spec_change initiatives should validate compliance and document deviations

### Secondary Recommendation: If Option A Out of Scope, Pursue Option B

**Rationale:**
1. **Zero engineering cost:** Close immediately, transfer hygiene tasks
2. **Acknowledges reality:** Enforcement exists; no spec gap
3. **Frees initiative slot:** Allows focus on initiatives with actual implementation work

### Anti-Recommendation: Do NOT Pursue Option C

**Rationale:**
1. **Duplicates working code:** No benefit to reimplementing existing guard
2. **Regression risk:** Replacing working code introduces defect potential
3. **Violates YAGNI:** No user-facing improvement; pure churn

## Artifacts Produced in Phase A

All artifacts located at: `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`

1. **fallback_reproduction.md**: CLI behavior reproduction, telemetry inspection
2. **spec_citations.md**: Normative citations, compliance matrix
3. **guard_design.md**: Failure surface taxonomy, error message analysis
4. **summary.md**: This document (consolidation, Phase B roadmap)
5. **cli_fallback_stdout.log**: Stdout from missing refined MTZ test
6. **cli_no_refined_mtz_stdout.log**: Stdout from baseline test (no --refined-mtz)

## Next Steps

### Immediate (Before Phase B Kickoff)

1. **Stakeholder review:** Share this Phase A summary with initiative sponsor
2. **Scope decision:** Choose Option A (validate) or Option B (close)
3. **Git history audit:** Determine when guard was added (helps explain doc drift)

### Phase B (If Option A Chosen)

1. **Regression test implementation** (primary deliverable)
2. **ARCH-CONTRACT update** (documentation sync)
3. **SCALE-007 validation** (confirm CLI guard satisfies finding)
4. **Findings update** (document enforcement existence)

### Phase B (If Option B Chosen)

1. **Closure report publication** (link to this summary)
2. **Backlog ticket creation** (test/doc hygiene tasks)
3. **Initiative archive** (move to `plans/archive/MAP-SCALE-005/`)

## Conclusion

Phase A successfully completed all assigned tasks and made a critical discovery: **the enforcement mechanism assumed to be missing is already implemented and spec-compliant.** This finding transforms the initiative from "implement new enforcement" to "validate and document existing enforcement," significantly reducing scope and risk.

The existing guard at `dbex/refine_one.py:382-389` demonstrates high-quality design:
- Optimal positioning (after sigma, before simulation)
- Comprehensive failure surface coverage (6 identified surfaces)
- Clear, actionable error messages
- Telemetry consistency guaranteed by fail-fast architecture

The primary gap is **documentation drift** (ARCH-CONTRACT-CALIBRATION-001 claims "silent fallback" despite guard existence) and **regression test coverage** (no automated validation of guard behavior).

**Recommended path forward:** Option A (minimal validation & documentation) — 1-2 engineer loops to add regression coverage and sync documentation, ensuring the existing enforcement remains robust and discoverable.

---

**Phase A Status:** ✅ **COMPLETE**

**Phase B Readiness:** ✅ **READY** (pending scope decision)

**Initiative Risk:** 🟢 **LOW** (enforcement exists; remaining work is validation/docs)
