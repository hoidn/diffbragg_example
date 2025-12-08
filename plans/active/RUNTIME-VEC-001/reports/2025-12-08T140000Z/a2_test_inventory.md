# A2: Source-Weight Test Inventory

## Summary

**Location:** `/home/ollie/Documents/nanoBragg/tests/test_cli_scaling.py`
**Total Source-Weight Tests:** 9 tests across 2 classes
**DBEX Test File:** `tests/dbex/test_runtime_vectorization.py` (1 test already exists)

---

## TestSourceWeights Class (6 tests)

Located at `/home/ollie/Documents/nanoBragg/tests/test_cli_scaling.py:252-580`

### 1. `test_source_weights_ignored_per_spec` (lines 255-367)
**Purpose:** TC-Spec-1 — Verify source weights are ignored per specs/spec-a-core.md:151
**Strategy:**
- Run PyTorch with varied weights [1.0, 0.2] vs equal weights [1.0, 1.0]
- Assert outputs are identical (within 0.3% tolerance for float32 precision)

**Assertions:**
- `correlation >= 0.999`
- `|sum_ratio - 1.0| <= 3e-3` (0.3%)

**DBEX Mapping:** Direct port candidate → `tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec` (ALREADY EXISTS)

---

### 2. `test_cli_lambda_overrides_sourcefile` (lines 368-473)
**Purpose:** TC-Spec-2 — CLI `-lambda` parameter overrides sourcefile wavelengths
**Strategy:**
- Create sourcefile with lambda=1.0Å, run with CLI lambda=0.5Å
- Verify `UserWarning` emitted with spec reference
- Compare against reference run with matching CLI lambda

**Assertions:**
- `UserWarning` raised with "Sourcefile wavelength column differs"
- Warning contains "spec-a-core.md" reference
- `|sum_ratio - 1.0| <= 3e-3`

**DBEX Mapping:** Port candidate (secondary priority)

---

### 3. `test_uniform_weights_ignored` (lines 475-492)
**Purpose:** TC-B — Three sources with uniform weights [1.0, 1.0, 1.0]
**Strategy:** Unit test of BeamConfig accepting uniform weights

**Assertions:**
- `beam_config.source_weights is not None`
- `len(beam_config.source_weights) == 3`

**DBEX Mapping:** Unit test, not integration — defer

---

### 4. `test_edge_case_zero_sum_accepted` (lines 494-517)
**Purpose:** TC-D — Zero-sum weights accepted since ignored
**Strategy:** Unit test of BeamConfig accepting all-zero and mixed-sign weights

**Assertions:**
- BeamConfig accepts `[0.0, 0.0]`
- BeamConfig accepts `[1.0, -1.0]`

**DBEX Mapping:** Unit test, not integration — defer

---

### 5. `test_edge_case_negative_weights_accepted` (lines 519-533)
**Purpose:** TC-D — Negative weights accepted since ignored
**Strategy:** Unit test of BeamConfig accepting negative weights

**Assertions:**
- BeamConfig accepts `[1.0, -0.2]`

**DBEX Mapping:** Unit test, not integration — defer

---

### 6. `test_single_source_fallback` (lines 535-579)
**Purpose:** TC-C — Single source fallback (source_weights=None)
**Strategy:** Create minimal simulation with no source_weights, verify execution

**Assertions:**
- `result.shape == (64, 64)`
- `result.sum().item() > 0`

**DBEX Mapping:** Port candidate (secondary priority)

---

## TestSourceWeightsDivergence Class (3 tests)

Located at `/home/ollie/Documents/nanoBragg/tests/test_cli_scaling.py:582-770`

### 7. `test_c_divergence_reference` (lines 585-695)
**Purpose:** Phase H — C vs PyTorch parity validation on weighted sources
**Condition:** Requires `NB_RUN_PARALLEL=1` environment variable and C binary
**Strategy:**
- Run C and PyTorch with same weighted sourcefile
- Compare outputs

**Assertions:**
- `correlation >= 0.999`
- `|sum_ratio - 1.0| <= 5e-3`

**DBEX Mapping:** Requires C binary — not portable to DBEX without infrastructure

---

### 8. `test_sourcefile_divergence_warning` (lines 697-770)
**Purpose:** TC-D2 — UserWarning when sourcefile + divergence parameters both present
**Strategy:** Run with `-sourcefile` + `-hdivrange`, verify warning

**Assertions:**
- `UserWarning` raised with "Divergence/dispersion parameters ignored"
- Warning contains "spec-a-core.md:151-162"

**DBEX Mapping:** Port candidate (secondary priority)

---

### 9. `TestHKLDevice` tests (lines 773-870)
**Note:** Not source-weight related; covers HKL tensor device placement

---

## DBEX Existing Test

**File:** `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/tests/dbex/test_runtime_vectorization.py`

### `TestRuntimeVectorization::test_source_weights_ignored_per_spec` (lines 25-192)
**Status:** ALREADY EXISTS
**Condition:** Requires `RUNTIME_VEC_ARTIFACT_DIR` environment variable
**Strategy:** Same as nanoBragg test — weighted vs equal-weight comparison
**Thresholds:** `correlation >= 0.999`, `|sum_ratio−1| <= 5e-3`

---

## Mapping Summary for DBEX

| nanoBragg Test | DBEX Status | Priority |
|----------------|-------------|----------|
| `test_source_weights_ignored_per_spec` | EXISTS | N/A |
| `test_cli_lambda_overrides_sourcefile` | Not ported | Medium |
| `test_single_source_fallback` | Not ported | Low |
| `test_sourcefile_divergence_warning` | Not ported | Low |
| `test_c_divergence_reference` | Not portable | N/A (requires C) |
| Unit tests (TC-B, TC-D) | Not needed | N/A (unit) |

---

## Required Fixtures/Artifacts

For the existing DBEX test:
1. **Environment Variable:** `RUNTIME_VEC_ARTIFACT_DIR` — must be set to artifact output path
2. **Environment Variable:** `KMP_DUPLICATE_LIB_OK=TRUE` — required
3. **Environment Variable:** `NANOBRAGG_DISABLE_COMPILE=1` — recommended for stability

For potential ports:
- `A.mat` file (for CLI tests using MOSFLM matrix)
- `scaled.hkl` file (for HKL device tests)
- Source fixture files can be generated inline (no external files needed)

---

## Conclusion

The DBEX environment already has the primary source-weight test ported (`test_source_weights_ignored_per_spec`). Phase B should focus on:
1. Validating the existing DBEX test runs successfully
2. Documenting the environment variable requirements
3. Potentially porting `test_cli_lambda_overrides_sourcefile` for broader coverage
