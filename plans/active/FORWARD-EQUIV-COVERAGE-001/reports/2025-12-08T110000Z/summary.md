# FORWARD-EQUIV-COVERAGE-001 Phase A — Reality Check Summary

**Date**: 2025-12-08T110000Z
**Initiative**: FORWARD-EQUIV-COVERAGE-001 — Forward Equivalence & Parity Harness Roll-up
**Phase**: A (Member Plan Reality Check)

---

## 1. Member Plan Status Matrix (Verified)

| Plan ID | Claimed Status | Reality Check | Evidence |
|---------|----------------|---------------|----------|
| FORWARD-EQUIV-001 | A-C complete, D1-D3 optional | **VERIFIED** | `tests/dbex/test_forward_equivalence_complete.py` exists (8003 bytes); fixtures in `test_db_at_001_parity.py`; golden data at `tests/fixtures/golden_data/simple_cubic/` |
| FORWARD-EQUIV-002 | All phases complete | **VERIFIED** | `tests/dbex/test_db_at_001_parity.py` exists (33986 bytes); canonical loaders (`load_golden_data`, `GoldenData`) implemented in `tests/fixtures/parity_loader.py` |
| PARITY-HARNESS-002 | A-D complete, E pending | **VERIFIED** | E1-E3 unchecked in implementation.md; closure validation not yet performed |

---

## 2. Test Results Summary

**Command**: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001 --smoke-detector-size=full`

### Results

| Metric | Value |
|--------|-------|
| Tests collected | 15 |
| Tests passed | 12 (80%) |
| Tests failed | 3 (20%) |
| Runtime | 0.94s |

### Passed Tests (12)
- `TestManifestIntegrity::test_manifest_integrity`
- `TestManifestIntegrity::test_golden_data_sanity`
- `TestManifestIntegrity::test_pixel_pitch_guard`
- `TestParityMetrics::test_perfect_match`
- `TestParityMetrics::test_correlation_computation`
- `TestParityMetrics::test_error_metrics`
- `TestParityMetrics::test_sum_ratio`
- `TestParityMetrics::test_localization_metric`
- `TestParityMetrics::test_mask_application`
- `TestParityMetrics::test_edge_cases`
- `TestParityMetrics::test_to_dict_serialization`
- `TestArtifactEmission::test_artifact_emission_minimal`

### Failed Tests (3) — All Share Same Root Cause
- `TestArtifactEmission::test_artifact_emission`
- `TestDB_AT_001_Parity::test_db_at_001_parity_smoke`
- `TestForwardEquiv::test_DB_AT_001_forward_equiv`

**Root Cause**: `TypeError: compute_z_scores() missing 1 required positional argument: 'variance'`

**Location**: `tests/fixtures/parity_loader.py:604`

**Details**: The `write_parity_artifacts()` function calls `compute_z_scores(target, predicted)` but the function signature in `dbex/vis/residuals.py:13` requires three positional arguments: `data`, `model`, `variance`. The call is missing the `variance` argument.

---

## 3. DB-AT-001 Threshold Verification

Per `docs/spec-db-conformance.md:42-44`:
- **Correlation threshold**: >= 0.2 (median ROI)
- **Localization threshold**: >= 90% ROIs with local intensity max in central half-box

### Test Implementation Verification
- `test_db_at_001_parity.py:812-828`: Enforces thresholds via xfail policy for synthetic data
- `test_forward_equivalence_complete.py:201-206`: Hard asserts `correlation >= 0.2` and `localization >= 0.9`

### Golden Data Verification
- Location: `tests/fixtures/golden_data/simple_cubic/`
- Manifest: `manifest.json` with SHA256 checksums
- Dataset: `simple_cubic_canonical` (generated 2025-11-04T17:19:02Z)
- Files verified present:
  - `bragg_diffbragg.npy` (24.9 MB)
  - `bragg_torch.npy` (24.9 MB)
  - `target_panel_0.npy` (24.9 MB)
  - `loss_mask_panel_0.npy` (6.2 MB)
  - `manifest.json` with integrity checksum

---

## 4. Gap Analysis

### GAP-1: `compute_z_scores()` Signature Mismatch (Critical)
- **Impact**: 3 tests failing, prevents closure validation
- **Root cause**: `parity_loader.py:604` calls `compute_z_scores(target, predicted)` without required `variance` argument
- **Fix required**: Update call site to provide variance tensor (e.g., `variance = predicted + sigma_readout**2` per spec-db-core.md)
- **Blocking**: PARITY-HARNESS-002 Phase E closure

### GAP-2: PARITY-HARNESS-002 Phase E Not Complete
- **Impact**: Roll-up cannot close until E1-E3 validated
- **E1**: Exit criteria audit — blocked by GAP-1
- **E2**: Ledger closure — depends on E1
- **E3**: Archive readiness — depends on E1, E2

### No Other Gaps Identified
- Member plan checklists accurate
- Test files exist as claimed
- Golden data present with valid manifest
- Thresholds properly documented and enforced (where tests can reach assertion)

---

## 5. Exit Criteria Assessment (Phase A)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| A1: Tests run | **DONE** | `pytest_db_at_001.log`: 12 passed, 3 failed |
| A2: Checklists verified | **DONE** | 3/3 member plans verified |
| A3: Gaps identified | **DONE** | GAP-1 (critical bug), GAP-2 (pending Phase E) |
| A4: Summary authored | **DONE** | This document |

---

## 6. Recommendation

**Status**: NOT READY for Phase B closure

**Action Required**:
1. Fix GAP-1 (`compute_z_scores()` call in `parity_loader.py:604`) — requires code change
2. Re-run tests to confirm 15/15 passing
3. Then proceed to Phase B (PARITY-HARNESS-002 E1-E3 closure)

**Fix Approach for GAP-1**:
```python
# Current (broken):
z_scores = compute_z_scores(target, predicted)

# Required (fix):
# Per spec-db-core.md: variance = model + sigma_readout^2
# where sigma_readout = 5 ADU (standard value)
sigma_readout = 5.0
variance = predicted + sigma_readout ** 2
z_scores = compute_z_scores(target, predicted, variance)
```

---

## 7. Artifacts Index

- `pytest_db_at_001.log` — Test execution output (12 passed, 3 failed)
- `collect_db_at_001.log` — Test collection evidence (15 tests)
- `summary.md` — This document

---

### Turn Summary
Validated FORWARD-EQUIV-COVERAGE-001 Phase A with test execution and member plan verification.
Found critical GAP-1: `compute_z_scores()` signature mismatch in parity_loader.py causing 3 test failures.
Next: Fix GAP-1 code defect before proceeding to Phase B closure.
Artifacts: plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T110000Z/ (pytest_db_at_001.log, collect_db_at_001.log)

---

### Prior Turn Summary (Galph i=182)
Switched focus from completed TORCH-CLI-BRIDGE-ROLLUP-001 to FORWARD-EQUIV-COVERAGE-001, a Tier 1 roll-up whose dependency (NANOBRAG-GOLDEN-001) is satisfied.
Analyzed 3 member plans: FORWARD-EQUIV-001/002 appear complete, PARITY-HARNESS-002 has Phase E closure pending. Roll-up likely ready for closure validation.
Next: Ralph executes Phase A reality check — run DB_AT_001 tests, verify checklists, identify gaps, author summary.
Artifacts: plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T110000Z/
