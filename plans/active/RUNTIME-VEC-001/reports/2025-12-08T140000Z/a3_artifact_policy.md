# A3: Artifact Policy and Pytest Selectors

## Artifact Policy

### 1. Artifact Directory Structure

```
$RUNTIME_VEC_ARTIFACT_DIR/
├── mapping_metrics.json       # Test metrics output (correlation, sum_ratio)
├── source_weight_test_summary.txt  # Human-readable summary
└── blocker_log.txt           # Error logs if CLI fails (on failure only)
```

### 2. Environment Variable

| Variable | Purpose | Required |
|----------|---------|----------|
| `RUNTIME_VEC_ARTIFACT_DIR` | Base path for test artifacts | YES — test skips if not set |

**Rationale:** The test requires artifact routing to persist metrics for:
- Debugging failed runs
- Evidence collection for compliance
- Reproducibility documentation

### 3. Metrics JSON Schema

```json
{
  "correlation": 0.9999,        // float: Pearson correlation between weighted and equal-weight outputs
  "sum_weighted": 1.234e6,      // float: Total intensity sum (weighted run)
  "sum_equal": 1.234e6,         // float: Total intensity sum (equal-weight run)
  "sum_ratio": 1.0,             // float: sum_weighted / sum_equal
  "sum_ratio_delta": 0.0001,    // float: abs(sum_ratio - 1.0)
  "threshold_correlation": 0.999,     // float: Pass threshold
  "threshold_sum_ratio_delta": 0.005, // float: Pass threshold (5e-3)
  "pass": true                  // boolean: Overall pass/fail
}
```

---

## Pytest Selectors

### Primary Test (DBEX)

**File:** `tests/dbex/test_runtime_vectorization.py`

**Selector:**
```bash
pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec
```

**Full Command with Environment:**
```bash
RUNTIME_VEC_ARTIFACT_DIR=plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z/artifacts \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec
```

### Collect-Only Command

```bash
pytest --collect-only tests/dbex/test_runtime_vectorization.py
```

**Expected Output:**
```
<Module test_runtime_vectorization.py>
  <Class TestRuntimeVectorization>
    <Function test_source_weights_ignored_per_spec>

========================== 1 test collected ==========================
```

---

## Environment Flags Summary

| Flag | Value | Source | Purpose |
|------|-------|--------|---------|
| `RUNTIME_VEC_ARTIFACT_DIR` | (user-defined path) | Test requirement | Artifact routing |
| `KMP_DUPLICATE_LIB_OK` | `TRUE` | `docs/pytorch_runtime_checklist.md:41` | Prevent duplicate library conflicts |
| `NANOBRAGG_DISABLE_COMPILE` | `1` | `docs/pytorch_runtime_checklist.md:31` | Disable torch.compile for stability |

---

## Phase B Planned Selectors

When Phase B adds additional tests, the following selectors are proposed:

1. **test_source_weights_ignored_per_spec** (exists)
   ```bash
   pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_ignored_per_spec
   ```

2. **test_source_weights_divergence_parity** (planned)
   ```bash
   pytest -v tests/dbex/test_runtime_vectorization.py::TestRuntimeVectorization::test_source_weights_divergence_parity
   ```

---

## Test Registry Update Path

After Phase B test implementation:
1. Update `docs/TESTING_GUIDE.md` §2 to include RUNTIME-VEC-001 selectors
2. Update `docs/development/TEST_SUITE_INDEX.md` to list the new test file
3. Run `pytest --collect-only` to verify registration

---

## Conclusion

The artifact policy is defined with:
- Single environment variable for artifact routing (`RUNTIME_VEC_ARTIFACT_DIR`)
- Structured JSON metrics output
- Clear pytest selectors for the existing test
- Environment flags documented per runtime checklist
