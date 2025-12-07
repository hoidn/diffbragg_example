# ARCH-IMPL-CONFORMANCE-001 Phase A.2 Summary

## Date: 2026-01-13T230000Z

## Executive Summary

Phase A.2 cold-path enforcement test implemented and executed. **Outcome: FAIL (expected)**. Test validates ARCH-CONTRACT-001 for the **cold-path reconstruction** scenario (stage_a_ctx=None), exposing **64.7% relative error** (2.83x scale factor) between Stage A warm-cache and reconstruction cold-path outputs.

**Key Finding**: Cold-path reconstruction missing or incorrectly applying sqrt(spot_scale_override) scaling, confirming duplicated scaling logic hypothesis. Phase B canonical API implementation is required to eliminate duplicates and restore parity.

## Test Implementation

### Test Specification
- **Module**: `tests/architecture/test_scale_contracts.py` (extended to 293 lines)
- **Function**: `test_stage_a_vs_reconstruction_scale_cold_path` (new, lines 160-293)
- **Fixture**: `refgeom_dataload` (refGeom_small)
- **Tolerance**: 1e-6 relative error (per docs/spec-db-core.md:60-140)

### Test Execution Path
1. Build Stage A warm-cache context via `build_mapping_stage_a_context`
2. Extract `bragg_stage_a` from `stage_a_ctx.bragg_zero_iter`
3. Compute `masked_mean_stage_a` over trusted pixels
4. Call `build_final_bragg_from_stage_a_telemetry` with:
   - `param_state="initial"` (zero deltas)
   - **`stage_a_ctx=None`** (cold-path mode, bypass cache)
5. Compute `masked_mean_reconstruction_cold` over same trusted pixels
6. Assert `rel_error <= 1e-6`

### Actual Outcome
- **Status**: FAILED (expected baseline drift detection)
- **Metrics**:
  - `masked_mean_stage_a = 2.159070e+00`
  - `masked_mean_reconstruction_cold = 7.626188e-01`
  - `rel_error = 6.467836e-01` (64.7%)
  - `ratio = 2.831126` (Stage A outputs 2.83x higher than cold path)

### Root Cause Analysis

**Hypothesis**: Cold-path reconstruction (lines 88-223) missing or incorrectly applying sqrt(spot_scale_override) scaling.

**Evidence from test output**:
```
[ARCH-SIM-CONSTRUCTION-001 Phase C.7] log_scale_effective not found in telemetry; falling back to legacy computation
  sqrt_spot_scale: 1.0
  spot_scale_override: None
```

**Key observation**: `spot_scale_override: None` in cold path, indicating calibration_metadata not threaded correctly.

**Stage A behavior** (from Phase A.1 test):
- `spot_scale_override` derived from calibration_metadata
- `sqrt_spot_scale = sqrt(spot_scale_override)` applied post-simulation (stage_a.py:442-443)

**Reconstruction cold-path behavior**:
- `spot_scale_override = None` (calibration_metadata not available or not extracted)
- `sqrt_spot_scale = 1.0` (no scaling applied)

**Result**: Stage A applies ~2.83x scaling factor that cold path doesn't apply, causing exact 2.83x ratio mismatch.

## Contract Satisfaction Assessment

### ARCH-CONTRACT-001 (Stage A vs Reconstruction Scaling Parity)
**Status**: **PARTIALLY SATISFIED** (warm-cache only)

**Satisfied scenarios**:
- ✅ Reconstruction with `stage_a_ctx` + `param_state="initial"` (cache hit, Phase A.1 test passed)

**Violated scenarios** (confirmed):
- ❌ Reconstruction with `stage_a_ctx=None` (cold path, Phase A.2 test failed)
- ❌ 64.7% relative error (tolerance 1e-6)
- ❌ 2.83x scale factor mismatch

**Next step**: Phase B canonical API implementation required to restore parity.

### ARCH-CONTRACT-002 (Post-Run Scaling Pattern)
**Status**: **NOT SATISFIED** (duplicated logic confirmed)

**Duplicates identified**:
- `dbex/refinement/stage_a.py:442-443` (original, applies sqrt(spot_scale_override))
- `dbex/refinement/reconstruction.py:203-208` (cold path duplicate, missing or incorrect application)

**Canonical owner**: Not yet implemented (proposed `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`)

**Next step**: Phase B.1-B.4 implementation to create canonical API and route both paths through it.

## Implications for Phase B

### Phase B Scope Confirmation

**Original Phase B plan** (from 2026-01-13T150000Z/summary.md):
- B.1: Create `dbex.refinement.scaling_utils` with canonical scaling helpers
- B.2: Enhance factory to accept `calibration_metadata` and thread beam fields internally
- B.3: Refactor Stage A to use canonical API
- B.4: Refactor reconstruction to use canonical API
- B.5: Add enforcement tests
- B.6: Update docs and findings

**Revised assessment** (after Phase A.2 baseline detection):
- **B.1 CRITICAL** — Canonical API required to unify sqrt(spot_scale_override) pattern
- **B.2 CRITICAL** — Must ensure calibration_metadata threading to reconstruction cold path
- **B.3 MEDIUM** — Stage A warm-cache already works, but canonical API improves maintainability
- **B.4 CRITICAL** — Reconstruction cold path must apply sqrt(spot_scale_override) matching Stage A
- **B.5 COMPLETE** — Both Phase A.1 (warm-cache) and A.2 (cold-path) enforcement tests now exist
- **B.6 REQUIRED** — Update SCALE-008/009 findings to reflect cold-path drift magnitude

### Recommended Path Forward

**Phase B Implementation (next 2-3 loops)**:

**Loop i=111 (B.1-B.2): Canonical API + calibration_metadata threading**
- Create `dbex/refinement/scaling_utils.py` with `apply_sqrt_spot_scale` canonical helper
- Enhance `build_final_bragg_from_stage_a_telemetry` signature to accept `calibration_metadata` explicitly
- Thread `calibration_metadata` from config or stage_a_ctx to cold-path logic
- Add unit test for `apply_sqrt_spot_scale` helper

**Loop i=112 (B.3-B.4): Refactor duplicates to use canonical API**
- Refactor stage_a.py:442-443 to call `apply_sqrt_spot_scale`
- Refactor reconstruction.py:203-208 to call `apply_sqrt_spot_scale`
- Run both Phase A.1 (warm-cache) and A.2 (cold-path) enforcement tests
- Expect both tests to PASS after refactor

**Loop i=113 (B.6): Docs sync and findings update**
- Update SCALE-008/009 findings with cold-path drift baseline (64.7%, 2.83x)
- Update docs/TESTING_GUIDE.md §2 with cold-path enforcement test selector
- Update docs/development/TEST_SUITE_INDEX.md with Phase A.2 test entry
- Update implementation.md to mark Phase B complete

## Ledger Updates

### docs/fix_plan.md Attempts History
Add entry:
```
- 2026-01-13T230000Z: Phase A.2 cold-path enforcement test implemented. Test FAILED (expected) with 64.7% relative error (2.83x scale factor), confirming duplicated sqrt(spot_scale_override) scaling logic drift in reconstruction cold path. Root cause: calibration_metadata not threaded to cold path (spot_scale_override=None). Phase B canonical API implementation required to restore parity. Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/. Tests: test_stage_a_vs_reconstruction_scale_cold_path (FAIL). [architecture, TDD, baseline_detection]
```

### plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md
- [x] A0: Nucleus test designed (2026-01-13T200000Z)
- [x] A1: Nucleus test implemented, **PASSED** (warm-cache parity validated) (2026-01-13T210000Z)
- [x] A2: **Cold-path enforcement test** implemented, **FAILED** (cold-path drift confirmed, 64.7%, 2.83x) (2026-01-13T230000Z)
- [ ] B: **Canonical API implementation** — Next phase (loops i=111-113)

Update Status Note:
```markdown
## Status: in_progress
- Phase A.0 complete: nucleus test designed (2026-01-13T200000Z)
- Phase A.1 complete: nucleus test implemented, PASSED (warm-cache parity confirmed) (2026-01-13T210000Z)
- Phase A.1 analysis complete: cold-path scenario identified as unvalidated (2026-01-13T220000Z)
- Phase A.2 complete: cold-path enforcement test implemented, FAILED (drift confirmed: 64.7%, 2.83x) (2026-01-13T230000Z)
- Next: Phase B — canonical API implementation (B.1-B.2: canonical utils + calibration threading)
```

## Next Loop Recommendation

**Mode**: TDD (implement canonical API, expect enforcement tests to PASS)

**ActionType**: implementation_ready (Phase B.1-B.2)

**DecisionStatus**: patch_ready (canonical API design known from findings)

**Focus**: [ARCH-IMPL-CONFORMANCE-001] Phase B.1-B.2 — Canonical Scaling API + Calibration Threading

**Do Now**:
1. Create `dbex/refinement/scaling_utils.py` with `apply_sqrt_spot_scale` canonical helper
2. Enhance `build_final_bragg_from_stage_a_telemetry` to accept `calibration_metadata` parameter
3. Thread `calibration_metadata` to cold-path logic (lines 203-208)
4. Add unit test for `apply_sqrt_spot_scale`
5. Run Phase A.2 cold-path test (expect still FAIL until B.3-B.4 refactor complete)

**Mapped Tests**:
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (baseline)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (warm-cache regression check)
- New: `tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale` (unit test for canonical helper)

**Artifacts**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/pytest_phase_b1.log`

**Findings Applied**: SCALE-008, SCALE-009, ARCH-FACTORY-001

**ARCH Contracts**: ARCH-CONTRACT-001 (cold-path violation confirmed), ARCH-CONTRACT-002 (duplicates confirmed)

## Cross-References

- **Phase A.2 test implementation**: `tests/architecture/test_scale_contracts.py:160-293`
- **Phase A.1 outcome analysis**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/phase_a1_outcome_analysis.md`
- **Phase A.1 nucleus test**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/`
- **Phase A.0 nucleus design**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md`
- **Phase A kickoff planning**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`
- **Code references**:
  - `dbex/refinement/reconstruction.py:83-86` (cache fast-path, bypassed in A.2 test)
  - `dbex/refinement/reconstruction.py:88-223` (cold-path duplicated logic, drift confirmed)
  - `dbex/refinement/reconstruction.py:203-208` (missing sqrt scaling application)
  - `dbex/refinement/stage_a.py:442-443` (original sqrt scaling pattern)

---

**Phase A.2 complete. Cold-path drift confirmed (64.7%, 2.83x). Phase B canonical API implementation ready to proceed.**

### Turn Summary
Phase A.2 cold-path enforcement test implemented and executed (FAIL, expected). Test exposes 64.7% relative error (2.83x scale factor) between Stage A and reconstruction cold path, confirming duplicated sqrt(spot_scale_override) scaling logic drift. Root cause: calibration_metadata not threaded to cold path. Phase B canonical API implementation required to restore parity. Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/pytest_cold_path_baseline.log, cold_path_metrics.json
