# Ralph Input — Loop i=109

## Summary
Implement Phase A.1 nucleus test for ARCH-IMPL-CONFORMANCE-001 to establish baseline detection of Stage A vs reconstruction scaling mismatch.

## Mode
TDD

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment

## Branch
integration

## Mapped tests
```bash
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale
```

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/`

## Findings Applied (Mandatory)
- **SCALE-008** (docs/findings.md:42 line 322-339): Stage A warm-cache baseline authority — Nucleus test will validate this contract by comparing Stage A warm-cache forward vs reconstruction cold-path masked means.
- **SCALE-009** (docs/findings.md:43 line 341-358): Reconstruction scaling provenance — Test will expose whether reconstruction duplicates vs reuses Stage A scaling logic.
- **ARCH-FACTORY-001** (docs/findings.md:90 line 360-377): Unified simulator factory responsibilities — Test uses existing factory/helpers without modification to establish baseline behavior.
- **PROBE-FREEZE-001** (docs/findings.md:93 line 393-410): Probe freeze policy — Test is architecture enforcement (tests/architecture/), not plan-local probe, so no growth cap applies.

## Pointers
- **Spec:** docs/spec-db-core.md:60-140 (simulator construction, calibration threading, 1e-6 tolerance)
- **Arch:** docs/architecture/calibration_scaling.md (spot_scale_override sqrt pattern)
- **Testing:** docs/TESTING_GUIDE.md:255-320 (architecture test execution workflow)
- **Design:** plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md (full test specification)
- **Implementation Plan:** plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/phase_a1_implementation_plan.md

## ARCH Contracts (mandatory)
- **ARCH-CONTRACT-001** (proposed, to be enforced): Stage A vs Reconstruction Scaling Parity
  - **Owner**: dbex/refinement/stage_a.py:442-443 (Stage A sqrt scaling pattern)
  - **Duplicates**: dbex/refinement/reconstruction.py:167-223 (reconstruction cold path duplicates Stage A pattern)
  - **Failure Classification**: Implementation bug within architecture (duplicated logic instead of shared owner API)

- **ARCH-CONTRACT-002** (proposed, to be enforced): Calibration Metadata Threading
  - **Owner**: dbex/refinement/stage_a_utils.py:267 (beam calibration threading)
  - **Duplicates**: Multiple paths in reconstruction.py, nanobrag_bridge.py threading calibration separately
  - **Failure Classification**: Architecture conformance failure (duplicated semantics exist, no canonical API)

- **ARCH-CONTRACT-003** (proposed, to be enforced): Masked-Mean Computation Consistency
  - **Owner**: dbex/refinement/stage_a_impl.py:1336-1365 (Stage A trusted-mask intersection pattern)
  - **Duplicates**: Reconstruction helpers may apply masks differently
  - **Failure Classification**: Architecture conformance failure (no shared mask normalization API)

## Do Now (hard validity contract)

**Focus**: [ARCH-IMPL-CONFORMANCE-001] Phase A.1

**Implement**: `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale`

**Validating pytest selector**:
```bash
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale --tb=short
```

**Artifacts path**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/`

**Initiative type**: architecture (ARCH-CONTRACT enforcement)

### Detailed Implementation Steps

1. **Create new test module**: `tests/architecture/test_scale_contracts.py`

2. **Implement `test_stage_a_vs_reconstruction_scale` function** following nucleus_test_design.md:

   a. **Fixture Setup**:
   - Use `refgeom_dataload` fixture (tests/conftest.py:90-163) to load `refGeom_small`
   - Extract geometry, calibration_metadata, trusted_mask from DataLoad
   - Ensure param_state="initial" (zero refinement deltas)

   b. **Stage A Path (Warm-Cache)**:
   - Import: `from dbex.vis.mapping import build_mapping_stage_a_context`
   - Call `build_mapping_stage_a_context(DL, ...)` to get Stage A artifacts
   - Extract `bragg_stage_a` (post-sqrt-scaling Bragg tensor)
   - Compute `masked_mean_stage_a = mean(bragg_stage_a[trusted_mask])`

   c. **Reconstruction Path (Cold)**:
   - Import: `from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry`
   - Call reconstruction helper with Stage A telemetry, param_state="initial", same calibration_metadata
   - Extract `bragg_reconstruction` from reconstruction outputs
   - Compute `masked_mean_reconstruction = mean(bragg_reconstruction[trusted_mask])`

   d. **Assertion Logic**:
   ```python
   rel_error = abs(masked_mean_stage_a - masked_mean_reconstruction) / masked_mean_stage_a
   assert rel_error <= 1e-6, (
       f"Stage A vs reconstruction masked mean mismatch: "
       f"stage_a={masked_mean_stage_a:.6e}, "
       f"reconstruction={masked_mean_reconstruction:.6e}, "
       f"rel_error={rel_error:.6e} (tolerance=1e-6)"
   )
   ```

3. **Run test and capture baseline failure**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale --tb=short \
   > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/pytest_nucleus_baseline.log 2>&1
   ```

4. **Capture metrics on failure**:
   - Extract `masked_mean_stage_a`, `masked_mean_reconstruction`, `rel_error` from pytest output
   - Compute ratio `masked_mean_stage_a / masked_mean_reconstruction`
   - Write metrics to `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/nucleus_baseline_metrics.json`

5. **Update implementation.md**:
   - Mark A0 [x] complete
   - Add A1 loop record with timestamp, artifacts, outcome (PASS/FAIL + metrics)

## Forbidden This Loop
- no new probes in `plans/active/ARCH-IMPL-CONFORMANCE-001/bin/` (test goes in `tests/architecture/` per ARCH-CONTRACT enforcement pattern)
- do not modify Stage A or reconstruction production code (baseline test must expose current mismatch)
- do not touch dbex/refinement/stage_a.py, dbex/refinement/reconstruction.py, dbex/nanobrag_bridge.py (Phase B scope)

## How-To Map

### Environment
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
KMP_DUPLICATE_LIB_OK=TRUE
NANOBRAGG_DISABLE_COMPILE=1
```

### Test Execution
```bash
# Run nucleus test (expect FAIL showing current mismatch)
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale --tb=short \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/pytest_nucleus_baseline.log 2>&1

# Verify test collection
pytest --collect-only tests/architecture/test_scale_contracts.py \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/pytest_collection.log 2>&1
```

### Artifact Destinations
- Test module: `tests/architecture/test_scale_contracts.py` (new file)
- Pytest baseline log: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/pytest_nucleus_baseline.log`
- Collection log: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/pytest_collection.log`
- Baseline metrics: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/nucleus_baseline_metrics.json`
- Summary: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/summary.md`

## Pitfalls To Avoid

1. **Type discipline**: This is architecture type, not bugfix/perf — test must enforce ARCH-CONTRACT, not fix production code this loop
2. **No stacking**: Baseline test must run against current implementation (do not attempt to fix Stage A/reconstruction before establishing baseline)
3. **Parity-first**: Test establishes current divergence magnitude before attempting alignment (Phase B will fix)
4. **Shadow-pipeline guard**: Test goes in tests/architecture/, uses existing fixtures/helpers, no new plan-local scripts
5. **Spec alignment**: 1e-6 tolerance matches docs/spec-db-core.md:60-140 (do not invent new tolerance)
6. **Fixture selection**: Use refgeom_dataload fixture (conftest.py:90-163), not direct file loading (maintains test isolation)
7. **Import paths**:
   - `from dbex.vis.mapping import build_mapping_stage_a_context` (Stage A context builder)
   - `from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry` (reconstruction helper)
8. **Masked-mean computation**: Apply same trusted_mask to both Stage A and reconstruction outputs before computing means (mask from DataLoad fixture)
9. **Param state**: Ensure param_state="initial" for reconstruction (zero deltas) to match Stage A zero-point
10. **Telemetry threading**: Reconstruction helper requires Stage A telemetry — extract from Stage A artifacts returned by build_mapping_stage_a_context

## If Blocked

If any blocker occurs:
1. Document blocker in `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/blocker.md`
2. Mark initiative status `blocked_pending_<reason>` in implementation.md
3. Potential blockers:
   - Missing fixture access (refGeom_small unavailable) → try alternative fixture
   - API signature changed (build_mapping_stage_a_context) → review code, adapt test design
   - Environment failure (pytest collection fails) → escalate to supervisor
4. Do NOT proceed with test implementation if blocked — document and escalate

## Doc Sync Plan (Conditional)

**Triggered**: Yes (new test authored)

After test implementation:
1. Run collection-only to verify selector is discoverable:
   ```bash
   pytest --collect-only tests/architecture/test_scale_contracts.py \
     > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/pytest_collection.log 2>&1
   ```
2. Update test registries (after code passes):
   - Add `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` to docs/TESTING_GUIDE.md §Architecture Tests
   - Add row to docs/development/TEST_SUITE_INDEX.md with Status=Active, Purpose="ARCH-CONTRACT-001 enforcement (Stage A vs reconstruction scaling parity)"
3. Cross-reference in findings:
   - Update SCALE-008, SCALE-009 findings to reference the new enforcement test
   - Note: enforcement test currently FAILS (baseline), will PASS after Phase B canonical API implementation

## Expected Outcome

**Test Status**: FAIL (baseline detector)

**Metrics**:
- `masked_mean_stage_a` ≠ `masked_mean_reconstruction` (mismatch exposed)
- `rel_error > 1e-6` (outside tolerance)
- Ratio `masked_mean_stage_a / masked_mean_reconstruction` ≠ 1.0 (quantifies divergence)

**Artifacts**:
- pytest log showing AssertionError with metrics
- nucleus_baseline_metrics.json capturing divergence magnitude
- summary.md documenting Phase A.1 completion and readiness for Phase B

**Next Loop**: Phase B canonical API implementation to eliminate duplicated scaling logic and make test PASS
