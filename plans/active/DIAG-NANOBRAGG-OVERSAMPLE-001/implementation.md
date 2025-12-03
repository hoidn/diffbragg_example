# [DIAG-NANOBRAGG-OVERSAMPLE-001] nanobrag_torch Oversample Parameter Investigation

## Metadata
- **ID**: DIAG-NANOBRAGG-OVERSAMPLE-001
- **Title**: Investigate why nanobrag_torch `oversample` parameter not honored
- **Owner**: Galph ↔ Ralph
- **Status**: in_progress
- **Type**: diagnostics
- **Tier**: 0 (unblocks ARCH-SIM-CONSTRUCTION-001)
- **Created**: 2025-12-02T194500Z
- **Depends on**: None
- **Blocks**: ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)

## Problem Statement

ARCH-SIM-CONSTRUCTION-001 stuck after 4 implementation loops due to suspected environment issue: explicit `DetectorConfig(oversample=3)` setting does not prevent auto-selection code path in `nanobrag_torch.Simulator.run()`. Test logs show "auto-selected 3-fold oversampling" printed 209 times despite explicit parameter, causing ~23,317× magnitude discrepancy in reconstruction helpers (bragg_after=1.025e-05 vs expected ~0.24, chi²=1.084e+05 vs ≤1e2 spec).

**Suspected causes:**
1. `DetectorConfig.oversample` field not preserved by dataclass
2. Explicit `oversample=-1` passed to `simulator.run()` somewhere, overriding config
3. Auto-selection logic bug in simulator.py

Environment freeze blocks investigation without using exception clause for targeted bugfixes to locally available source.

## Spec Alignment

**Normative references:**
- docs/spec-db-core.md §§20-40 (detector configuration, oversampling semantics)
- docs/spec-db-workflow.md §§53-61 (reconstruction helpers correctness requirements)
- ARCH-SIM-CONSTRUCTION-001 exit criteria: "Reconstruction simulator raw output magnitude matches Stage A simulator raw output (within 1% for same parameters)"

**Acceptance tests:**
- DB-AT-028: `chi²/pixel initial ≤ 1e2`
- DB-AT-029: `median ROI correlation before ≥ 0.2`

## Goals

1. **Confirm root cause** of oversample parameter handling issue in nanobrag_torch
2. **Document diagnostic process** per Environment Freeze exception requirements
3. **Provide evidence** to support targeted fix or maintainer escalation

## Non-Goals

- Fixing the issue (Phase 2, conditional on Phase 1 findings)
- Changing acceptance criteria or specs
- Modifying DBEX production code (issue is in nanobrag_torch)

## Exit Criteria

1. Debug instrumentation added to `nanobrag_torch/simulator.py` to log oversample parameter flow
2. Patch file saved to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
3. nanobrag_torch rebuilt successfully with debug instrumentation
4. DB-AT-028 rerun with debug output captured in artifacts
5. Root cause identified from debug logs (Case A, B, or C per problems_ledger_service.md)
6. Findings documented in `docs/findings.md` with DIAG-NANOBRAGG-OVERSAMPLE-001 tag
7. Environment state tagged (e.g., "nanobragg-debug-oversample-2025-12-03")

## Phases

### Phase A: Debug Instrumentation

**Objective**: Add minimal debug prints to confirm oversample parameter handling without changing logic

**Tasks:**
- [ ] A.1: Add debug prints to `src/nanobrag-torch/src/nanobrag_torch/simulator.py:769-780`:
  ```python
  def run(self, oversample=None, ...):
      print(f"[DIAG-OVERSAMPLE] simulator.run() called with oversample={oversample}")
      print(f"[DIAG-OVERSAMPLE] self.detector.config.oversample={self.detector.config.oversample}")
      if oversample is None:
          oversample = self.detector.config.oversample
          print(f"[DIAG-OVERSAMPLE] oversample after config read: {oversample}")
      if oversample == -1:
          # auto-selection logic
          print(f"[DIAG-OVERSAMPLE] Entering auto-selection branch")
  ```
- [ ] A.2: Save patch file to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
- [ ] A.3: Document rebuild process in artifacts
- [ ] A.4: Rebuild nanobrag_torch
- [ ] A.5: Rerun DB-AT-028 with `-s` flag to capture debug output
- [ ] A.6: Analyze debug logs to identify case (A/B/C)
- [ ] A.7: Document findings in `docs/findings.md`

**Validation:**
- Debug logs show full oversample parameter flow from DetectorConfig construction through simulator.run()
- Root cause case identified (A/B/C)

**Artifacts:**
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/nanobragg_build.log`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/pytest_db_at_028_debug.log`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/root_cause_analysis.md`
- Update to `docs/findings.md` (new finding: DIAG-OVERSAMPLE-001)

### Phase B: Targeted Fix (Conditional)

**Objective**: Apply minimal fix based on Phase A diagnosis

**Conditional execution:**
- Only proceed if Phase A confirms fixable bug (Case A or C)
- If Case B (caller issue), return to ARCH-SIM-CONSTRUCTION-001 to fix caller
- If unfixable without upstream changes, escalate to maintainers

**Tasks (TBD based on Phase A findings):**
- Case A: Add oversample field to DetectorConfig dataclass
- Case C: Fix auto-selection logic bug

**Validation:**
- DB-AT-028/029 PASS with fixed nanobrag_torch
- ARCH-SIM-CONSTRUCTION-001 unblocked

## Abort/Escalation Triggers

**Abort conditions:**
- nanobrag_torch build fails with unknown dependencies → escalate to user
- Debug logs don't reveal root cause → request maintainer investigation
- Fix requires extensive nanobrag_torch changes (>50 lines) → escalate to user

**Escalation path:**
- Create problems.md entry with "[ESCALATE TO USER]" tag
- Document investigation findings and blocker
- Recommend maintainer engagement or environment upgrade

## Environment Freeze Exception Compliance

Per CLAUDE.md Environment Freeze exception clause:

✓ **Scope**: Patches to locally available source (`src/nanobrag-torch/`)
✓ **Requirement 1**: Save patch file → `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/*.patch`
✓ **Requirement 2**: Document rebuild commands → captured in artifacts/build.log
✓ **Requirement 3**: Test fix resolves blocking issue → DB-AT-028/029 validation
✓ **Requirement 4**: Update docs/findings.md → DIAG-OVERSAMPLE-001 finding
✓ **Requirement 5**: Tag environment state → "nanobragg-debug-oversample-2025-12-03"

**Rationale**: ARCH-SIM-CONSTRUCTION-001 is Tier 0 blocker affecting reconstruction correctness (critical path). Investigation requires source-level debugging not achievable via configuration/API changes.

## Dependencies

**Upstream:**
- None (can proceed immediately)

**Downstream (blocks these until complete):**
- ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)
- ARCH-REFACTOR-001 Phase D.3 (reconstruction baseline logic, blocked by ARCH-SIM-CONSTRUCTION-001)

## Risk Assessment

**Low risk**:
- Phase A is read-only diagnostic (only adds prints, no logic changes)
- Patch file provides rollback path
- nanobrag_torch is local source, not production dependency

**Medium risk**:
- Build system complexity unknown (may require complex dependencies)
- Rebuild may expose other latent issues

**Mitigation**:
- Incremental approach (diagnose before fixing)
- Document all steps for reproducibility
- Tag environment state before/after changes

## Success Metrics

- Root cause identified from debug logs
- Zero test regressions (all existing tests continue to PASS/SKIP as before)
- ARCH-SIM-CONSTRUCTION-001 unblocked (if fix applied in Phase B)
- Documentation complete per Environment Freeze exception requirements
