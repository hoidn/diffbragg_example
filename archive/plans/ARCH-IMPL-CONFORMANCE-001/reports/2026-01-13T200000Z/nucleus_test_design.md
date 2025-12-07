# ARCH-IMPL-CONFORMANCE-001 — Nucleus Test Design (Phase A.1)

## Date: 2026-01-13T200000Z

## Purpose

Design a minimal architecture enforcement test to expose the current Stage A vs reconstruction scaling/calibration mismatch identified in ARCH-SIM-CONSTRUCTION-001 (Phases C.1-C.39) and SCALE-008/009 findings.

This nucleus test serves as:
1. **Baseline detector** — Validates that the current implementation exhibits the documented mismatch
2. **Enforcement gate** — After Phase B canonical API implementation, test must pass (mismatch eliminated)
3. **Regression brake** — Prevents future drift between Stage A and reconstruction paths

## Test Specification

### Test Module
`tests/architecture/test_scale_contracts.py` (new file)

### Test Function
`test_stage_a_vs_reconstruction_scale` (minimal reproducer)

### Test Rationale

**Problem**: Stage A warm-cache forward path and reconstruction helper cold path both apply `sqrt(spot_scale_override)` scaling, but they:
- Duplicate the scaling logic instead of sharing a canonical API
- May apply it at different points in the pipeline
- May use different calibration metadata threading paths
- May produce divergent masked-mean outputs even with identical inputs

**Evidence sources**:
- SCALE-008 (docs/findings.md:322-339): Stage A vs mapping baseline drift
- SCALE-009 (docs/findings.md:341-358): Reconstruction scaling parity (multi-factor issue)
- ARCH-SIM-CONSTRUCTION-001 Phase C evidence: masked_mean ratio divergence between Stage A and reconstruction paths

**Contract to enforce**:
Given identical geometry, identical calibration metadata, and param_state="initial" (zero refinement deltas):
- Stage A warm-cache forward → `bragg_stage_a`
- Reconstruction helper cold path → `bragg_reconstruction`
- `masked_mean(bragg_stage_a) ≈ masked_mean(bragg_reconstruction)` within ≤1e-6 relative tolerance

### Fixture Selection

**Fixture**: `refGeom_small` (existing fixture from DB-AT-027/028/029)

**Rationale**:
- Small enough for fast execution (~200 ROIs, minimal runtime overhead)
- Already used in DB-AT-027/028/029 acceptance tests (consistency with existing test portfolio)
- Contains calibration_metadata with `spot_scale_override`, `beam_flux`, `beam_exposure`, `beamsize_mm`
- Trusted masks available for masked-mean computation

**Data requirements**:
- Geometry (detector, crystal from dxtbx Experiments)
- Calibration metadata dict with:
  - `spot_scale_override` (non-unity value to exercise sqrt scaling)
  - Beam calibration fields (`beam_flux`, `beam_exposure`, `beamsize_mm`)
- Trusted mask (DIALS convention, per-panel flex.bool arrays)

### Test Implementation Strategy

#### Setup Phase
1. Load `refGeom_small` fixture via `DataLoad` helper
2. Extract geometry and calibration metadata
3. Ensure `param_state="initial"` (zero refinement deltas — U(0)=U₀, B(0)=B₀, no scale/background refinement)

#### Stage A Path (Warm-Cache)
1. Call `build_mapping_stage_a_context` with loaded geometry + calibration metadata
   - This builds the warm-cache Stage A context (pre-initialized simulator instances)
2. Extract `bragg_stage_a` from Stage A artifacts (post-sqrt-scaling)
3. Compute `masked_mean_stage_a = mean(bragg_stage_a[trusted_mask])`

#### Reconstruction Path (Cold)
1. Call `build_final_bragg_from_stage_a_telemetry` with:
   - Stage A telemetry (from previous step)
   - `param_state="initial"` (forces zero-delta reconstruction)
   - Same calibration metadata
2. Extract `bragg_reconstruction` from reconstruction outputs (post-sqrt-scaling)
3. Compute `masked_mean_reconstruction = mean(bragg_reconstruction[trusted_mask])`

#### Assertion Logic
```python
rel_error = abs(masked_mean_stage_a - masked_mean_reconstruction) / masked_mean_stage_a
assert rel_error <= 1e-6, (
    f"Stage A vs reconstruction masked mean mismatch: "
    f"stage_a={masked_mean_stage_a:.6e}, "
    f"reconstruction={masked_mean_reconstruction:.6e}, "
    f"rel_error={rel_error:.6e} (tolerance=1e-6)"
)
```

**Tolerance justification**: docs/spec-db-core.md §60-140 uses 1e-6 relative tolerance for Stage A parity checks; reuse same threshold for architectural contract enforcement.

### Expected Initial Outcome

**FAIL** (exposes current mismatch)

**Why**: ARCH-SIM-CONSTRUCTION-001 Phase C evidence shows masked_mean ratio divergence between Stage A and reconstruction paths. Current duplicated scaling logic may apply sqrt scaling at different points or with different calibration threading, producing measurable drift.

**Metrics to capture on failure**:
- `masked_mean_stage_a` (actual value)
- `masked_mean_reconstruction` (actual value)
- `rel_error` (how far outside tolerance)
- Ratio `masked_mean_stage_a / masked_mean_reconstruction` (scale factor)

### Success Criteria (Phase B Exit)

**PASS** (mismatch eliminated)

**After Phase B canonical API implementation**:
- Both Stage A and reconstruction call shared `scaling_utils.apply_sqrt_spot_scale`
- Both use same calibration metadata threading via enhanced factory
- Duplicate scaling logic removed
- Test passes with `rel_error < 1e-6`

## Test Isolation and Stability

### No Random Seeds
Test uses deterministic forward simulation with fixed geometry + fixed calibration metadata. No RNG-dependent behavior.

### No Heavy Refinement
Test runs zero-iteration forward only (param_state="initial"). No LBFGS, no multi-iteration refinement. Fast execution (<5 seconds expected).

### No External Dependencies
Test uses existing fixtures (`refGeom_small`), existing helpers (`build_mapping_stage_a_context`, `build_final_bragg_from_stage_a_telemetry`). No new data files required.

## Enforcement Test Lifecycle

### Phase A.1 (Next Loop)
Implement `test_stage_a_vs_reconstruction_scale` per this design.

**Validation**:
- Run `pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale`
- Capture pytest log showing FAIL with metrics
- Store log in `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/pytest_nucleus_baseline.log`

### Phase B (Canonical API Implementation)
Refactor Stage A and reconstruction to use shared scaling utilities.

**Validation**:
- Same test now PASSES
- Capture pytest log showing PASS
- Store log in `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/pytest_enforcement_pass.log`

### Ongoing Enforcement
Test remains in `tests/architecture/` as permanent regression brake.

**CI integration**: Include in architecture test suite (run on every commit to integration/main).

## Cross-References

### Findings
- **SCALE-008** (docs/findings.md:322-339): Stage A warm-cache baseline authority
- **SCALE-009** (docs/findings.md:341-358): Reconstruction scaling provenance (multi-factor parity issue)
- **ARCH-FACTORY-001** (docs/findings.md:360-377): Unified simulator factory responsibilities

### ARCH-SIM-CONSTRUCTION-001 Evidence
- Phase C.1-C.39 reports: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T*` through `2025-12-18T*`
- Key metrics: masked_mean ratios, scale_ratio divergence, baseline alignment issues

### Spec/Arch Docs
- **docs/spec-db-core.md:60-140**: Simulator construction, calibration threading, acceptance tolerances
- **docs/architecture/calibration_scaling.md**: Current implementation of spot_scale_override sqrt pattern
- **docs/TESTING_GUIDE.md:255-320**: Architecture test execution workflow

### Code References
- `dbex/refinement/stage_a.py:442-443` (Stage A sqrt scaling pattern)
- `dbex/refinement/reconstruction.py:167-223` (reconstruction cold path, duplicates Stage A pattern)
- `dbex/refinement/stage_a_utils.py:267` (beam calibration threading)

## Blocked Conditions

If nucleus test cannot be implemented next loop, document blocker and mark initiative `blocked_pending_<reason>`:

### Potential Blockers
1. **Missing fixture access**: `refGeom_small` unavailable or broken
   - **Mitigation**: Use alternative small fixture (e.g., DB-AT-027 data directly)

2. **Missing Stage A telemetry**: `build_mapping_stage_a_context` API changed
   - **Mitigation**: Review Stage A API via code search, update test design if needed

3. **Missing reconstruction helper**: `build_final_bragg_from_stage_a_telemetry` unavailable
   - **Mitigation**: Review reconstruction.py API, adapt to current interface

4. **Environment failure**: pytest cannot collect test
   - **Mitigation**: Document environment blocker, escalate to supervisor for environment investigation

If any blocker occurs, do NOT proceed with Phase A.1 implementation. Document blocker in this file and mark initiative status accordingly.

## Next Actions (Phase A.1 Loop)

1. **Implement test** in `tests/architecture/test_scale_contracts.py`
2. **Run test** with `pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale`
3. **Capture baseline failure** metrics and pytest log
4. **Store artifacts** in `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/`
5. **Update implementation.md** — mark A0 complete, A1 in_progress

---

**Design complete. Ready for Phase A.1 implementation next loop.**
