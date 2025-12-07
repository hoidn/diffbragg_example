# Input for Loop i=118 (Ralph) — ARCH-IMPL-CONFORMANCE-001 Phase B.8

## Summary
Fix test mask contract mismatch: update test_scale_contracts.py to use `inputs.loss_mask` (ROI pixels) instead of `trusted_mask` (all trusted pixels) for masked mean computation, aligning test contract with mapping.py:287-288 semantics.

## Mode
**harness** (test contract alignment, no production code changes)

## ActionType
**implementation_ready** (patch_ready: exact lines identified, confidence=0.98, harness fix)

## DecisionStatus
**patch_ready** (test fix to align with spec-db-core.md:55 loss_mask definition)

## InitiativeType
**architecture** (ARCH-IMPL-CONFORMANCE-001: enforce ARCH-CONTRACT-002 via test fix)

## Focus
**[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment (Phase B.8: Test Mask Contract Fix)**

## Branch
**integration**

## Mapped Tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
                                                     ::test_stage_a_vs_reconstruction_scale_cold_path
```

**Expected outcomes**:
- Phase A.1 (warm-cache): PASS with rel_error ≈ 0.0 (unchanged)
- Phase A.2 (cold-path): PASS with rel_error < 1e-6 (fixed from 2.5% error)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/`

## Findings Applied (Mandatory)
- **SCALE-002**: sqrt(spot_scale_override) applied post-simulation (correctly implemented in Phase B.6)
- **SCALE-008**: Stage A masked-intensity baseline authority (warm-cache optimization validated Phase A.1)
- **SCALE-009**: Reconstruction scaling provenance (Phases B.5-B.7 corrected double-sqrt, added masked_mean_ratio fallback)
- **ARCH-CONTRACT-002**: Stage A ↔ reconstruction scale alignment (Phase B.8 fixes test to match mapping contract: `inputs.loss_mask` domain per spec-db-core.md:55)

**Adherence notes**:
- Phase B.5: Identified double-sqrt bug (reconstruction applied sqrt twice when log_scale_baseline present)
- Phase B.6: Fixed by making apply_sqrt_spot_scale conditional on log_scale_baseline absence
- Phase B.7: Added masked_mean_ratio fallback from calibration_metadata when telemetry lacks model_mean_masked
- Phase B.8 (this loop): Test contract fix - use inputs.loss_mask (ROI pixels only) instead of trusted_mask (all trusted pixels) to match mapping.py:287-288 semantics

## Pointers

### Primary Spec/Arch Docs
- **spec-db-core.md:55** — Loss mask definition: `(background >= 0) & trusted_mask` (ROI pixels only)
- **spec-db-core.md:45** — Background = -1 outside ROIs per DIALS convention
- **docs/findings.md::SCALE-009** — Reconstruction scaling provenance (to be updated Phase B.9 with complete B.5-B.8 history)
- **docs/findings.md::ARCH-CONTRACT-002** — Stage A ↔ reconstruction scale alignment (enforcement via test_scale_contracts.py)

### Key Code Locations
- **dbex/refinement/inputs.py:230** — `loss_mask = (background_image >= 0) & mask_array` (defines ROI-only domain)
- **dbex/vis/mapping.py:287-288** — `masked_mean_ratio` computed from `inputs.loss_mask` (ROI pixels)
- **tests/architecture/test_scale_contracts.py:77-80, 141-143, 218-220, 284-286** — Test mask usage (to be fixed this loop)

### Context Docs
- **plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md** — Phase B checklist (B.1-B.7 complete, B.8 in progress)
- **plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/phase_b7_root_cause_analysis.md** — Detailed root cause analysis (mask contract mismatch)
- **plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/phase_b7_planning.md** — Phase B.7 planning (masked_mean_ratio fallback)

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-002: Stage A ↔ Reconstruction Scale Alignment
**Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (Phase B.1-B.2 complete)

**Contract**: Given identical calibration metadata, geometry, and param_state="initial":
1. Stage A warm-cache forward and reconstruction cold-path must agree on sqrt(spot_scale_override) application
2. Both must apply masked_mean_ratio baseline alignment when present in calibration_metadata
3. **Measurement domain**: Masked means computed over `inputs.loss_mask` (ROI pixels only per spec-db-core.md:55), NOT over all trusted pixels

**Current violation**: Test measures over `trusted_mask` (all trusted pixels) while mapping computes ratio from `inputs.loss_mask` (ROI pixels). This violates contract clause 3.

**Remediation (Phase B.8)**:
- Update test_scale_contracts.py lines 77-80, 141-143, 218-220, 284-286 to use `inputs.loss_mask`
- No production code changes required (reconstruction.py:454-484 already correct per Phase B.7)

**Enforcement test**: `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path`
- **Before Phase B.8**: FAIL with rel_error = 2.5% (mask mismatch)
- **After Phase B.8**: PASS with rel_error < 1e-6 (correct mask domain)

**What it checks**:
- Runtime parity: masked mean over `inputs.loss_mask` matches between Stage A and reconstruction within 1e-6 tolerance
- Structural prohibition: N/A (this is a runtime parity test, not structural)

## Do Now (hard validity contract)

### Focus
**[ARCH-IMPL-CONFORMANCE-001] Phase B.8** — Fix test mask contract to use `inputs.loss_mask` instead of `trusted_mask`

### Implement
Update **tests/architecture/test_scale_contracts.py** at 4 locations:

**1. Lines 77-80** (test_stage_a_vs_reconstruction_scale, Stage A measurement):
```python
# OLD: uses trusted_mask
masked_sum_stage_a = (bragg_stage_a[trusted_mask]).sum()
masked_count_stage_a = trusted_mask.sum()

# NEW: use inputs.loss_mask per mapping contract (spec-db-core.md:55)
loss_mask = inputs.loss_mask
masked_sum_stage_a = (bragg_stage_a[loss_mask]).sum()
masked_count_stage_a = loss_mask.sum()
```

**2. Lines 141-143** (test_stage_a_vs_reconstruction_scale, reconstruction measurement):
```python
# OLD: uses trusted_mask
masked_sum_reconstruction = (bragg_reconstruction[trusted_mask]).sum()
masked_count_reconstruction = trusted_mask.sum()

# NEW: use inputs.loss_mask (same mask as Stage A measurement)
masked_sum_reconstruction = (bragg_reconstruction[loss_mask]).sum()
masked_count_reconstruction = loss_mask.sum()
```

**3. Lines 218-220** (test_stage_a_vs_reconstruction_scale_cold_path, Stage A measurement):
```python
# OLD: uses trusted_mask
masked_sum_stage_a = (bragg_stage_a[trusted_mask]).sum()
masked_count_stage_a = trusted_mask.sum()

# NEW: use inputs.loss_mask per mapping contract
loss_mask = inputs.loss_mask
masked_sum_stage_a = (bragg_stage_a[loss_mask]).sum()
masked_count_stage_a = loss_mask.sum()
```

**4. Lines 284-286** (test_stage_a_vs_reconstruction_scale_cold_path, reconstruction cold-path measurement):
```python
# OLD: uses trusted_mask
masked_sum_reconstruction_cold = (bragg_reconstruction_cold[trusted_mask]).sum()
masked_count_reconstruction_cold = trusted_mask.sum()

# NEW: use inputs.loss_mask (same mask as Stage A measurement)
masked_sum_reconstruction_cold = (bragg_reconstruction_cold[loss_mask]).sum()
masked_count_reconstruction_cold = loss_mask.sum()
```

**Implementation notes**:
- Extract `loss_mask = inputs.loss_mask` once per test function (after inputs extraction)
- Update both Stage A and reconstruction measurements to use same mask
- Add comment citing spec-db-core.md:55 and ARCH-IMPL-CONFORMANCE-001 Phase B.8

### Validating Tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
                                                     ::test_stage_a_vs_reconstruction_scale_cold_path
```

**Exit criteria**:
- Both tests PASS
- Phase A.1 rel_error ≈ 0.0 (warm-cache parity, unchanged)
- Phase A.2 rel_error < 1e-6 (cold-path parity, fixed from 2.5%)

### Artifacts
Write to: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/`
- `pytest_phase_b8_fix.log` (full pytest output with metrics)
- `summary.md` (concise turn summary with progression: B.5 3420% → B.6 738% → B.7 2.5% → B.8 <0.0001%)

## Forbidden This Loop
- **No production code changes** (harness fix only)
- **No new probes** (DecisionStatus=patch_ready)
- **No environment modifications** (test file only)

## How-To Map

### Environment Setup
```bash
cd /home/ollie/Documents/diffbragg_example
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
```

### Edit Test File
Update `tests/architecture/test_scale_contracts.py` at lines 77-80, 141-143, 218-220, 284-286 per Do Now specification.

### Run Tests
```bash
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
                                                     ::test_stage_a_vs_reconstruction_scale_cold_path \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/pytest_phase_b8_fix.log 2>&1
```

### Verify Metrics
Extract from pytest log:
- Phase A.1: `rel_error` and `ratio` (expect ≈0.0, ≈1.0)
- Phase A.2: `rel_error` and `ratio` (expect <1e-6, ≈1.0)
- Mask coverage: `masked_count` should be LESS than `trusted_mask.sum()` (proving ROI-only domain)

### Write Summary
Create `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T050658Z/summary.md` with:
- Turn summary (test fix, both tests PASS)
- Metrics progression table (B.5 → B.6 → B.7 → B.8)
- Evidence that loss_mask ≠ trusted_mask (pixel counts)

## Pitfalls To Avoid

1. **Type discipline**: This is a harness fix (InitiativeType=architecture, Mode=harness), do NOT change production code in dbex/
2. **No stacking**: Phase B.7 implementation was correct (masked_mean_ratio fallback working), test contract was wrong
3. **Parity-first**: N/A (this is a test fix to align contract, not a production parity issue)
4. **Shadow-pipeline guard**: N/A (test file only)
5. **Evidence→Action**: 2.5% residual error → test mask mismatch → exact fix at 4 line ranges
6. **Dominant-hypothesis lock**: confidence=0.98, patch_ready → no additional probes/analysis
7. **Findings paydown**: ARCH-CONTRACT-002 clause 3 (measurement domain) corrected by this fix
8. **ARCH conformance**: Aligns test with spec-db-core.md:55 loss_mask definition
9. **Enforcement tests mapped**: Both Phase A.1 and A.2 are the enforcement tests
10. **No environment changes**: Test file edit only, no package installs

## If Blocked

**Scenario 1**: Test still fails after mask fix with different error
- **Action**: Capture new rel_error and ratio in summary.md, mark Phase B.8 blocked, switch focus per lifecycle rules
- **Hypothesis**: May indicate deeper semantic issue beyond mask contract

**Scenario 2**: `inputs.loss_mask` not available in test context
- **Action**: Verify `inputs = stage_a_ctx.inputs` extraction succeeded, add defensive assertion
- **Likelihood**: Very Low (inputs is always present from build_mapping_stage_a_context)

**Scenario 3**: Test passes but with suspiciously high rel_error (e.g., 1e-4 instead of 1e-8)
- **Action**: Document in summary.md, check if tolerance 1e-6 needs adjustment, consult spec-db-core.md:60-140 for parity requirements
- **Decision**: If rel_error < 1e-6, mark PASS; if 1e-6 ≤ rel_error < 1e-3, investigate; if ≥ 1e-3, mark FAIL

## Doc Sync Plan (Conditional)
**Not required this loop** (no new tests added, existing test contract corrected).

Phase B.9 will update:
- docs/findings.md::SCALE-009 (complete B.5-B.8 history)
- docs/TESTING_GUIDE.md (if test selector descriptions need clarification)
- docs/development/TEST_SUITE_INDEX.md (if status changes)
