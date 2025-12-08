# Downstream Consumers Assessment

**Phase A3 — MAP-SCALE-003**
**Date:** 2025-12-08

---

## Tests Exercising Refined MTZ Path

### 1. test_refine_one_cli.py

**File:** `tests/dbex/test_refine_one_cli.py`

| Test Function | Lines | Purpose | Refined MTZ? |
|--------------|-------|---------|--------------|
| `test_nanobrag_backend_uses_refined_mtz` | 765-906 | Validates refined MTZ loading and telemetry | **YES** |
| `test_refined_mtz_missing_file_fails_fast` | 1158-1260 | SCALE-007 fail-fast enforcement | **YES** |
| `test_refined_mtz_telemetry_provenance` | 1263-1431 | Telemetry reflects "refined" vs "raw" | **YES** |
| `test_nanobrag_backend_runs_simulator` | 199-361 | Basic nanobrag flow (raw MTZ path) | No |
| `test_nanobrag_backend_applies_calibration` | 375-536 | Calibration metadata (no refined MTZ) | No |
| `test_torch_diagnostics_metadata` | 913-1155 | Full telemetry schema validation | Indirectly |

#### Key Assertions in Refined MTZ Tests

**test_nanobrag_backend_uses_refined_mtz (lines 883-898):**
```python
# Verify load_refined_mtz was invoked with correct path
mock_load_refined.assert_called_once_with(refined_mtz_path, column="F")

# Verify build_structure_factor_grid received refined arrays
build_grid_call_kwargs = mock_build_grid.call_args[1]
np.testing.assert_array_equal(build_grid_call_kwargs['indices'], refined_indices)
np.testing.assert_array_equal(build_grid_call_kwargs['amplitudes'], refined_amplitudes)

# Verify _write_torch_outputs received telemetry marking refined source
hkl_telemetry = write_call_args[5]  # 6th positional arg
assert hkl_telemetry["hkl_source"] == "refined"
assert hkl_telemetry["hkl_n_reflections"] == len(refined_indices)
```

**test_refined_mtz_missing_file_fails_fast (lines 1247-1252):**
```python
# Verify error message is actionable and mentions the flag
error_msg = str(exc_info.value)
assert "--refined-mtz" in error_msg
assert nonexistent_refined_mtz in error_msg
assert "MUST be consumed" in error_msg
```

**test_refined_mtz_telemetry_provenance (lines 1388-1424):**
```python
# Test Case 1: No --refined-mtz (raw telemetry)
assert hkl_telemetry_raw["hkl_source"] == "raw"

# Test Case 2: With --refined-mtz (refined telemetry)
assert hkl_telemetry_refined["hkl_source"] == "refined"
assert hkl_telemetry_refined["hkl_n_reflections"] == len(refined_indices)
assert hkl_telemetry_refined["hkl_path"] == refined_mtz_path
```

---

### 2. test_mapping_consistency.py

**File:** `tests/dbex/test_mapping_consistency.py`

| Test Function | Lines | Purpose | Refined MTZ? |
|--------------|-------|---------|--------------|
| `test_db_at_024_mapping_smoke` | 188-536 | DB-AT-024 mapping acceptance | **YES** (when available) |

#### Refined MTZ Usage (lines 156-172)

```python
# Load refined structure factors if available (MAP-SCALE-001)
refined_hkl = None
if assets["refined_mtz"].exists():
    try:
        refined_indices, refined_amps = load_refined_mtz(assets["refined_mtz"])
        refined_hkl = (refined_indices, refined_amps)
    except Exception as e:
        warnings.warn(
            f"Failed to load refined MTZ from {assets['refined_mtz']}: {e}. "
            f"Falling back to raw scaled.mtz (may not meet thresholds)."
        )
```

#### Telemetry Validation (lines 494-514)

```python
# MAP-SCALE-004: Assert telemetry fields are present and correct
assert "hkl_telemetry" in diagnostics
hkl_telemetry = diagnostics["hkl_telemetry"]
assert "hkl_source" in hkl_telemetry
assert "hkl_n_reflections" in hkl_telemetry
assert "hkl_mean_amplitude" in hkl_telemetry
assert "hkl_path" in hkl_telemetry

# When canonical assets provide refined structure factors, telemetry must reflect this
if refined_hkl is not None:
    assert hkl_telemetry["hkl_source"] == "refined", (
        f"DB-AT-024 FAILED: Refined structure factors provided but telemetry reports "
        f"hkl_source='{hkl_telemetry['hkl_source']}'. Expected 'refined'."
    )
```

---

## Existing Artifact Schema Expectations

### HDF5 Schema (writer.py)

Tests expect the following structure-factor telemetry in `/torch_diagnostics`:

| Attribute | Type | Expected Values | Asserted In |
|-----------|------|-----------------|-------------|
| `hkl_source` | str | "refined" or "raw" | test_refine_one_cli.py:1056 |
| `hkl_n_reflections` | int | Positive integer | test_refine_one_cli.py:1053 |
| `hkl_mean_amplitude` | float | Positive float | test_refine_one_cli.py:1054 |
| `hkl_path` | str | File path | test_refine_one_cli.py:1055 |

**test_torch_diagnostics_metadata (lines 1051-1059):**
```python
# SCALE-003: verify HKL telemetry fields
assert 'hkl_source' in diag.attrs
assert 'hkl_n_reflections' in diag.attrs
assert 'hkl_mean_amplitude' in diag.attrs
assert 'hkl_path' in diag.attrs
assert diag.attrs['hkl_source'] == "raw"
assert diag.attrs['hkl_n_reflections'] == 100
assert diag.attrs['hkl_mean_amplitude'] == 50.0
assert diag.attrs['hkl_path'] == "/path/to/test.mtz"
```

---

## Risk Assessment: Backward Compatibility

### Schema Additions

The `hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, and `hkl_path` attributes are **already present** in the schema (added as part of SCALE-003).

### Impact Analysis

| Change | Risk | Mitigation |
|--------|------|------------|
| Adding new attrs | **NONE** | Already present |
| Changing attr types | N/A | No type changes proposed |
| Removing attrs | N/A | No removals proposed |
| Breaking existing tests | **NONE** | Tests already validate these attrs |

### Backward Compatibility Verdict

**NO BREAKING CHANGES.** The structure-factor telemetry schema is stable and all downstream consumers already expect these fields.

---

## Collect-Only Validation

### test_refine_one_cli.py

```bash
$ pytest --collect-only tests/dbex/test_refine_one_cli.py 2>&1 | head -50
```

Expected tests:
- `test_parser_has_backend_flag`
- `test_parser_rejects_invalid_backend`
- `test_parser_accepts_sigma_map_flag`
- `test_main_dispatches_to_diffbragg_backend`
- `test_main_dispatches_to_nanobrag_backend`
- `test_nanobrag_backend_runs_simulator`
- `test_nanobrag_backend_applies_calibration`
- `test_nanobrag_backend_requires_sigma_rdout`
- `test_nanobrag_backend_accepts_sigma_map`
- `test_nanobrag_backend_accepts_external_lookup_sigma_map`
- `test_nanobrag_backend_uses_refined_mtz`
- `test_torch_diagnostics_metadata[cli_override-3.0]`
- `test_torch_diagnostics_metadata[external_lookup-5.0]`
- `test_refined_mtz_missing_file_fails_fast`
- `test_refined_mtz_telemetry_provenance`

### test_mapping_consistency.py

```bash
$ pytest --collect-only tests/dbex/test_mapping_consistency.py 2>&1 | head -20
```

Expected tests:
- `TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`

---

## Summary

| Category | Finding |
|----------|---------|
| Tests exercising refined MTZ | 3 dedicated tests + 1 acceptance test |
| Schema expectations | 4 HKL telemetry attrs validated |
| Backward compatibility risk | **NONE** (schema already stable) |
| Missing coverage | **NONE** |

---

## Recommendations

1. **No schema changes required:** Structure-factor telemetry is fully implemented.
2. **Test coverage is sufficient:** 3 CLI tests + 1 acceptance test cover refined MTZ path.
3. **Phase B/C scope:** May focus on additional validation or edge cases rather than new telemetry.

---

## References

- `tests/dbex/test_refine_one_cli.py:765-906` — Refined MTZ loading test
- `tests/dbex/test_refine_one_cli.py:1158-1260` — Fail-fast enforcement test
- `tests/dbex/test_refine_one_cli.py:1263-1431` — Telemetry provenance test
- `tests/dbex/test_mapping_consistency.py:156-172` — Refined MTZ asset loading
- `tests/dbex/test_mapping_consistency.py:494-514` — Telemetry validation
