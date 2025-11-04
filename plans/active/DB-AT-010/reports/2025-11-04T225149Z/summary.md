# DB-AT-010 Regression Recovery  Summary

**Date:** 2025-11-04T225149Z
**Focus:** DB-AT-010 gradient correctness guard (regression recovery)
**Mode:** Parity
**Status:**  Complete  All exit criteria satisfied

## Problem Statement

**SPEC Requirements (docs/spec-db-conformance.md:12-14):**
> DBAT010 Gradcheck on refined parameters (cell logs/angles, quaternion seed ’ XYZ).

**Implementation (tests/dbex/test_gradients.py:160-267):**
The DB-AT-010 gradcheck tests verify gradient flow for crystal (cell_a, cell_gamma), detector (distance_mm), and beam (wavelength_A) parameters using `torch.autograd.gradcheck` with tolerances eps=1e-6, atol=1e-5, rtol=0.05.

**Regression Issue:**
`test_db_at_010_gradcheck_crystal_cell_a` was failing with `GradcheckError: Numerical gradient for function expected to be zero` because line 202 called `.item()` on the differentiable tensor before passing it to `simulate_forward_torch`, detaching it from the autograd graph per GRADIENT-001.

## Solution Implemented

### 1. Extended `simulate_forward_torch` with Tensor Override Path (dbex/nanobrag_bridge.py:1101-1226)

**ADR/SPEC Alignment:**
- **GRADIENT-001** (docs/findings.md:31): "DB-AT-010 gradcheck harness must avoid `.item()`/`.numpy()` on differentiable tensors; use bridge helpers that accept tensor overrides to preserve autograd graphs."
- **RUNTIME-001** (docs/findings.md:7): Enforces `NANOBRAGG_DISABLE_COMPILE=1` for gradcheck.
- **SCALE-001/SCALE-002** (docs/findings.md:15-16): Structure factors remain unscaled; spot_scale applied post-simulation.

**Code Changes:**
- Added `crystal_overrides: Optional[dict] = None` parameter to function signature (line 1112).
- Implemented override application logic (lines 1199-1226) that injects tensor-valued parameters (`cell_a`, `cell_b`, `cell_c`, `cell_alpha`, `cell_beta`, `cell_gamma`) directly into `crystal_config` without `.item()` detaching.
- Updated docstring to document the new parameter and GRADIENT-001 compliance (lines 1133-1151).

### 2. Updated Gradcheck Tests to Use Override Path (tests/dbex/test_gradients.py:190-213, 278-301)

**Code Changes:**
- Replaced dxtbx Crystal rebuilding logic (lines 194-214 in original) with direct `crystal_overrides` dict injection (lines 191-213 in updated).
- Removed `.item()` calls that were breaking gradient flow.
- Applied same pattern to `test_db_at_010_gradcheck_crystal_cell_gamma`.

**Verification:**
Both tests now pass gradcheck with all four parameter tests (cell_a, cell_gamma, distance_mm, wavelength_A) succeeding.

## Test Results

### Targeted Test Execution

**Collection Validation:**
```bash
pytest --collect-only tests -k DB_AT_010
# Result: 5/72 tests collected (TestDB_AT_010_Gradcheck class)
```

**Targeted Gradcheck (crystal_cell_a):**
```bash
pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --maxfail=1
# Result: PASSED in 73.08s
```

**Comprehensive Wrapper Test:**
```bash
pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck --maxfail=1
# Result: PASSED in 291.11s (4:51)
# All 4 parameter tests passed: crystal_cell_a, crystal_cell_gamma, detector_distance_mm, beam_wavelength_A
```

### Full Test Suite

```bash
pytest -v tests/
# Result: 69 passed, 3 skipped, 0 failed in 619.69s (10:19)
```

**Metrics:**
- No new failures introduced
- DB-AT-010 gradcheck tests now passing (previously failing)
- Pre-existing skipped tests remain: test_db_at_024_mapping_smoke, test_sample_to_source_vector, test_source_weights_ignored_per_spec

## Artifacts

All logs archived under `plans/active/DB-AT-010/reports/2025-11-04T225149Z/`:
- `collect_db_at_010.log`  Pytest collection output (5 tests)
- `pytest_db_at_010_cell_a.log`  Targeted crystal_cell_a test (PASSED in 73.08s)
- `pytest_db_at_010_wrapper.log`  Comprehensive wrapper test (PASSED in 291.11s)
- `pytest_full_suite.log`  Full test suite (69 passed, 3 skipped, 0 failed)
- `gradcheck_crystal_cell_a.json`  Metrics from cell_a test
- `gradcheck_metrics.json`  Consolidated metrics from wrapper test
- `summary.md`  This document

## SPEC/ADR Compliance

| Requirement | Source | Implementation | Status |
|-------------|--------|----------------|--------|
| Gradient-preserving override path | GRADIENT-001 | `crystal_overrides` param in `simulate_forward_torch` |  |
| No `.item()` detaching in gradcheck | docs/development/testing_strategy.md:416 | Removed `.item()` calls, use tensor injection |  |
| RUNTIME-001 enforcement | docs/pytorch_runtime_checklist.md:27 | Tests set `NANOBRAGG_DISABLE_COMPILE=1` |  |
| SCALE-001/002 preservation | docs/findings.md:15-16 | Structure factors unscaled, spot_scale applied |  |
| Gradcheck tolerances | docs/development/testing_strategy.md:364 | eps=1e-6, atol=1e-5, rtol=0.05 |  |

## Exit Criteria Verification

From `plans/active/DB-AT-010/implementation.md` Phase D:
- [x] **D1:** Extend `simulate_forward_torch` to accept tensor overrides (crystal_overrides implemented)
- [x] **D2:** Update gradcheck tests to use override path (both cell_a and cell_gamma tests updated)
- [x] **D3:** Archive logs and verify documentation accurate (logs archived, documentation unchanged)

From `input.md`:
- [x] Implement tensor-preserving override in `simulate_forward_torch` (lines 1199-1226)
- [x] Update `test_db_at_010_gradcheck_crystal_cell_a` to consume it (lines 191-213)
- [x] Validate `pytest --collect-only tests -k DB_AT_010` (5 tests collected)
- [x] Validate `pytest -v test_db_at_010_gradcheck --maxfail=1` (PASSED in 291.11s)
- [x] Archive logs in artifact directory (all logs present)

## Next Actions (Optional)

Per `input.md`:
> Next Up (optional): 1) Audit detector/beam override patterns once crystal overrides land, ensuring gradients propagate for distance and wavelength parameters without custom per-test patches.

The current implementation already supports detector (distance_mm) and beam (wavelength_A) gradients successfully (tests passed in wrapper run). The detector and beam parameters currently use dxtbx object rebuilding rather than tensor overrides, which works for gradcheck. Future optimization could extend the `crystal_overrides` pattern to detector/beam parameters for consistency, but this is not blocking.
