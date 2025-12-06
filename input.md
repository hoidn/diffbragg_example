# Input for Ralph (Loop i=110)

## Summary
Implement Phase A.2 cold-path enforcement test to validate ARCH-CONTRACT-001 (Stage A vs reconstruction scaling parity) for reconstruction cold path (no cache).

## Mode
TDD (test-first, expect FAIL baseline)

## ActionType
implementation_ready

## DecisionStatus
exploring (baseline drift detection for cold path)

## InitiativeType
architecture

## Focus
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment (Phase A.2: Cold-Path Enforcement Test)

## Branch
integration

## Mapped Tests
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (new, expected FAIL)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/` (or next timestamp)

## Findings Applied (Mandatory)
- **SCALE-008** (docs/findings.md): Stage A warm-cache baseline authority and masked-intensity alignment
- **SCALE-009** (docs/findings.md): Reconstruction scaling provenance (multi-factor parity issue: mask, N_cells, baseline, cache optimization)
- **ARCH-FACTORY-001** (docs/findings.md): Unified simulator factory responsibilities and calibration threading limits
- **PROBE-FREEZE-001** (docs/findings.md): Enforcement test policy and probe freeze governance

**Adherence notes**:
- SCALE-008/009: Cold-path test validates reconstruction honors same sqrt(spot_scale_override) scaling pattern as Stage A when cache unavailable
- ARCH-FACTORY-001: Test will expose whether factory calibration threading is duplicated in reconstruction cold path
- PROBE-FREEZE-001: Architecture enforcement test under `tests/architecture/` is preferred mechanism (not plan-local probe)

## Pointers
- **Spec**: docs/spec-db-core.md:60-140 (simulator construction, calibration threading, 1e-6 tolerance for Stage A parity)
- **Arch**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/phase_a1_outcome_analysis.md (cold-path analysis and test design)
- **Arch**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md (original nucleus test design, adapt for cold path)
- **Testing**: docs/TESTING_GUIDE.md:255-320 (architecture test execution workflow)
- **Code**: dbex/refinement/reconstruction.py:83-86 (cache fast-path, MUST bypass in cold-path test)
- **Code**: dbex/refinement/reconstruction.py:88-223 (cold-path logic with duplicated scaling, target of this test)
- **Code**: tests/architecture/test_scale_contracts.py:24-158 (Phase A.1 nucleus test, use as template)

## ARCH Contracts (Mandatory)
### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Parity
- **Owner**: dbex.refinement.stage_a (warm-cache), dbex.refinement.reconstruction (cold-path)
- **Contract**: Given identical geometry, calibration metadata, and param_state="initial", Stage A and reconstruction must produce masked_mean outputs within 1e-6 relative tolerance
- **Current status**:
  - Warm-cache path (stage_a_ctx provided): **SATISFIED** (Phase A.1 test passed via cache optimization)
  - Cold-path (stage_a_ctx=None): **UNVALIDATED** (Phase A.2 test to establish baseline)
- **Failure classification**: **Architecture conformance failure** (duplicated scaling logic in reconstruction cold path lines 88-223)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner**: Proposed `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (canonical API, Phase B deliverable)
- **Current duplicates**:
  - dbex/refinement/stage_a.py:442-443
  - dbex/refinement/reconstruction.py:~195-217 (cold path)
- **Contract**: All paths applying sqrt(spot_scale_override) must use canonical API
- **Failure classification**: **Implementation bug within architecture** (duplicates exist but warm-cache bypass masks the issue)

### ARCH-CONTRACT-003: Mapping → Stage A Baseline Override
- **Owner**: dbex.vis.mapping.build_mapping_stage_a_context (producer), dbex.refinement.stage_a (consumer)
- **Contract**: Stage A must defer to mapping-adjusted baseline when log_scale_baseline_source="mapping_masked_mean_adjustment"
- **Current status**: Not validated by Phase A.1 or A.2 tests (deferred to future work)

## Do Now

### Pre-Implementation Context
1. **Read Phase A.1 outcome analysis**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/phase_a1_outcome_analysis.md`
   - Understand why Phase A.1 test passed (cache optimization)
   - Identify cold-path scenario that needs enforcement (stage_a_ctx=None)
2. **Read existing nucleus test**: `tests/architecture/test_scale_contracts.py:24-158`
   - Use as template for cold-path test
   - Note fixture usage, masked_mean computation pattern, assertion structure
3. **Review reconstruction cold-path logic**: `dbex/refinement/reconstruction.py:88-223`
   - Understand what happens when cache unavailable
   - Confirm duplicated scaling logic exists

### Implementation Steps
1. **Add new test function** to `tests/architecture/test_scale_contracts.py`:
   - Name: `test_stage_a_vs_reconstruction_scale_cold_path`
   - Fixture: `refgeom_dataload` (reuse from Phase A.1)
   - Difference from A.1: Call `build_final_bragg_from_stage_a_telemetry` with **`stage_a_ctx=None`** to force cold-path reconstruction (bypass cache)

2. **Test structure**:
   ```python
   def test_stage_a_vs_reconstruction_scale_cold_path(refgeom_dataload):
       """Enforce ARCH-CONTRACT-001 for reconstruction cold path (no cache).

       This test validates that reconstruction cold path (stage_a_ctx=None)
       produces masked_mean outputs matching Stage A warm-cache path when
       given identical geometry, calibration metadata, and param_state="initial".

       Expected outcome (Phase A.2): FAIL - exposes duplicated scaling logic drift
       Success criteria (Phase B): PASS - after canonical scaling_utils refactor
       """
       # Setup: Build Stage A warm-cache context (same as A.1)
       stage_a_ctx = build_mapping_stage_a_context(dataload, ...)
       masked_mean_stage_a = compute_masked_mean(stage_a_ctx.bragg_zero_iter, trusted_mask)

       # Cold-path reconstruction: force stage_a_ctx=None to bypass cache
       bragg_reconstruction_cold = build_final_bragg_from_stage_a_telemetry(
           telemetry_a=<construct minimal zero-delta telemetry>,
           stage_a_ctx=None,  # CRITICAL: bypass cache
           param_state="initial",
           # ... other args matching Stage A geometry/calibration
       )
       masked_mean_reconstruction_cold = compute_masked_mean(bragg_reconstruction_cold, trusted_mask)

       # Assert 1e-6 tolerance (expect FAIL showing drift)
       rel_error = abs(masked_mean_stage_a - masked_mean_reconstruction_cold) / masked_mean_stage_a
       assert rel_error <= 1e-6, f"Cold-path drift: stage_a={masked_mean_stage_a:.6e}, reconstruction_cold={masked_mean_reconstruction_cold:.6e}, rel_error={rel_error:.6e}"
   ```

3. **Key implementation notes**:
   - **Telemetry construction**: Cannot reuse `stage_a_ctx.telemetry` because we're testing cold path from scratch. Construct minimal telemetry with zero deltas for param_state="initial" (see Phase A.1 test lines 90-102 for pattern).
   - **HKL grid**: Must construct HKL grid manually (see Phase A.1 test lines 105-113).
   - **Config**: Create minimal RefinementConfig (see Phase A.1 test lines 116-117).
   - **Critical assertion**: Set `stage_a_ctx=None` to force reconstruction cold path (line 130 in Phase A.1 test had `stage_a_ctx=stage_a_ctx`, change to `None`).

4. **Run test and capture baseline**:
   ```bash
   PYTEST_ADDOPTS='' pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path 2>&1 | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/pytest_cold_path_baseline.log
   ```

5. **Expected outcome**: **FAIL** with metrics showing:
   - `masked_mean_stage_a` (from warm-cache)
   - `masked_mean_reconstruction_cold` (from cold path, likely different)
   - `rel_error` (likely > 1e-6, exposing drift)
   - `ratio` (scale factor)

6. **If test PASSES** (no drift):
   - Document finding: cold path already aligned (Phase B.4 may be unnecessary)
   - Store artifacts with PASS metrics
   - Escalate to Galph for Phase B scope re-assessment

7. **If test FAILS** (drift confirmed):
   - Store artifacts with FAIL metrics
   - Proceed to Phase B canonical API implementation next loop
   - Cold-path test becomes enforcement gate for Phase B exit criteria

8. **Validation artifacts**:
   - `pytest_cold_path_baseline.log` (full pytest output with metrics)
   - `cold_path_metrics.json` (optional, structured metrics for analysis)
   - `pytest_collection.log` (pytest --collect-only showing 2 tests now in test_scale_contracts.py)
   - `summary.md` (loop summary)

## Forbidden This Loop
- No new plan-local probes or diagnostic scripts (PROBE-FREEZE-001)
- Do not modify production code in dbex/refinement/reconstruction.py or stage_a.py (test-only loop)
- Do not extend Phase A.1 warm-cache test (create separate cold-path test)
- Do not implement canonical scaling_utils.py (reserved for Phase B)

## DMI Section
Not applicable (not a Deterministic Mismatch Incident, this is architecture enforcement test implementation)

## ARCH Conformance Remediation
Not this loop (Phase A.2 is baseline detection, Phase B will implement remediation):

**Planned Phase B remediation** (after A.2 baseline established):
- Canonical owner API: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- Duplicates to route: stage_a.py:442-443, reconstruction.py:~195-217
- Enforcement test: Both Phase A.1 (warm-cache) and Phase A.2 (cold-path) tests must pass

## SYNC Closure
Not applicable (no SYNC mid-air events)

## How-To Map

### Test Implementation
```bash
# 1. Read context documents
cat plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/phase_a1_outcome_analysis.md
cat tests/architecture/test_scale_contracts.py  # Review Phase A.1 template

# 2. Implement cold-path test
# Edit tests/architecture/test_scale_contracts.py
# Add test_stage_a_vs_reconstruction_scale_cold_path function after existing test

# 3. Run test
PYTEST_ADDOPTS='' pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path 2>&1 | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/pytest_cold_path_baseline.log

# 4. Run collection check
pytest --collect-only tests/architecture/test_scale_contracts.py 2>&1 | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/pytest_collection.log

# 5. Store metrics (if useful)
# Create cold_path_metrics.json with masked_mean values, rel_error, ratio, outcome

# 6. Update ledgers
# - implementation.md: mark A2 complete
# - fix_plan.md: add Attempts History entry for 2026-01-13T230000Z
# - galph_memory.md: will be updated by Galph next loop

# 7. Git commit
# Commit test implementation with artifacts
```

### Environment
```bash
# No special environment variables required (same as Phase A.1)
# Default fixture behavior is sufficient
```

## Pitfalls To Avoid
1. **Reusing warm-cache path**: Do NOT pass `stage_a_ctx` to reconstruction in cold-path test (must be `None`)
2. **Assuming test will FAIL**: If test PASSES, document it properly and escalate (don't force a failure)
3. **Telemetry construction errors**: Use Phase A.1 lines 90-102 as template for zero-delta telemetry
4. **Missing HKL grid**: Must construct HKL grid manually (cannot reuse from stage_a_ctx if None)
5. **Hard-coding expected outcome in assertion message**: Keep assertion message neutral (works for both PASS and FAIL)
6. **Skipping collection check**: Always run pytest --collect-only to verify test is discoverable
7. **No baseline metrics**: Ensure pytest log captures actual values (masked_mean, rel_error, ratio)
8. **Modifying production code**: This is test-only loop, do not refactor dbex modules yet (Phase B)
9. **Creating plan-local probes**: Use architecture test under tests/architecture/ (PROBE-FREEZE-001)
10. **Type discipline violation**: If cold-path logic is fundamentally broken (not just drift), mark initiative blocked and escalate (do not attempt hot-fix)

## If Blocked
- If fixture unavailable or broken: document blocker, mark initiative `blocked_pending_fixture`, escalate to Galph
- If reconstruction API changed incompatibly: document blocker, mark `blocked_pending_api_clarification`, escalate
- If test cannot be implemented due to missing dependencies: document blocker, escalate
- If test errors (not FAIL, but import/runtime error): capture traceback, mark `blocked_pending_<reason>`, escalate
- DO NOT proceed to Phase B if A.2 cannot be implemented

## Doc Sync Plan
**Conditional** (only after Phase B canonical API implementation):
- After Phase B canonical API refactor, update docs/TESTING_GUIDE.md §2 with new architecture test selectors
- Update docs/development/TEST_SUITE_INDEX.md with test_stage_a_vs_reconstruction_scale_cold_path entry
- For this loop (A.2 test implementation only), doc sync deferred until Phase B complete

## Validation Plan
1. Test runs to completion (FAIL or PASS, not error)
2. Baseline metrics captured in pytest log (masked_mean_stage_a, masked_mean_reconstruction_cold, rel_error, ratio)
3. `pytest --collect-only` shows 2 tests in test_scale_contracts.py module
4. Artifacts stored under reports/<timestamp>/
5. If FAIL: metrics show rel_error > 1e-6 (drift confirmed)
6. If PASS: metrics show rel_error <= 1e-6 (cold path already aligned, skip Phase B.4 refactor)

## Exit Criteria This Loop
- [ ] `test_stage_a_vs_reconstruction_scale_cold_path` implemented in tests/architecture/test_scale_contracts.py
- [ ] Test runs to completion (FAIL or PASS outcome documented)
- [ ] Baseline metrics captured in pytest log
- [ ] `pytest --collect-only` log captured showing 2 tests
- [ ] Artifacts stored in reports directory
- [ ] implementation.md updated (A2 marked complete)
- [ ] fix_plan.md Attempts History updated (new entry for this loop)
- [ ] Git commit with test + artifacts

## Cross-References
- **Phase A.1 outcome**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/phase_a1_outcome_analysis.md`
- **Phase A.1 nucleus test**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/`
- **Phase A.0 nucleus design**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md`
- **Phase A kickoff**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`
- **Implementation plan**: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- **ARCH-SIM-CONSTRUCTION-001 cache optimization**: `plans/active/ARCH-SIM-CONSTRUCTION-001/` (Phase C.8 context for why warm-cache test passed)

---

**Phase A.2 cold-path enforcement test implementation (TDD mode). Expected baseline FAIL showing duplicated logic drift in reconstruction cold path before Phase B canonical API refactor.**
