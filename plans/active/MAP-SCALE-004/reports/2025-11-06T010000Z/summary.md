# MAP-SCALE-004 Documentation Sync Summary — 2025-11-06T010000Z

## Problem Statement
**Per `docs/spec-db-workflow.md §4` and `docs/spec-db-tracing.md §2`:**
> Zero-iteration helper (`simulate_forward_once`) and DB_AT_024 must surface structure-factor telemetry
> (hkl_source, reflection count, mean amplitude, MTZ path) to enforce refined MTZ usage and prevent regressions.

**Quoted SPEC requirement** (docs/spec-db-tracing.md:10-13):
> "Trace payload SHALL be produced by the same code paths used in production (no re‑derived physics)."

**ADR alignment:**
- SCALE-007: Zero-iteration bridge must emit structure-factor telemetry and DB_AT_024 must fail when refined assets are present but telemetry reports `raw` or is missing.
- MAP-SCALE-004 implementation (2025-11-05T220000Z) added telemetry to `simulate_forward_once`; this loop documents the contract.

## Documentation Updates

### 1. docs/TESTING_GUIDE.md:71
**Updated DB_AT_024 selector row:**
- Added **Telemetry requirements (SCALE-007)** section documenting the four required fields (`hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path`)
- Noted test failure behavior when refined assets exist but telemetry reports `raw` or is missing
- Updated metrics to 2025-11-06T010000Z: hkl_source="refined", hkl_n_reflections=69614, hkl_mean_amplitude=47.41
- Updated artifact directory from `MAP-SCALE-001/reports/2025-11-04T220000Z/` to `MAP-SCALE-004/reports/2025-11-06T010000Z/`
- Added SCALE-007 to Findings list

### 2. docs/development/TEST_SUITE_INDEX.md:27
**Updated DB_AT_024 registry entry:**
- Added `hkl_telemetry` to diagnostics field list in emission description
- Inserted **Telemetry requirements (SCALE-007)** section matching TESTING_GUIDE
- Included test source pointer: `tests/dbex/test_mapping_consistency.py:338-359` (telemetry assertion lines)
- Updated canonical metrics to 2025-11-06T010000Z with telemetry fields
- Updated artifact references (collect/pytest logs, mapping_metrics.json)
- Added SCALE-007 to Finding refs

### 3. docs/fix_plan.md:79
**Updated MAP-SCALE-004 Attempts History:**
- Recorded 2025-11-06T010000Z documentation loop
- Marked initiative status: `done`
- Captured metrics: corr_median=0.6206, localization=0.9348, hkl_source="refined"
- Listed artifacts under 2025-11-06T010000Z directory

## Test Validation

**Collection:**
```bash
NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE \
  DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z \
  pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```
Result: 1 test collected

**Execution:**
```bash
NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE \
  DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z \
  pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```
Result: 1 passed in 29.65s

## Metrics (from mapping_metrics.json)

```json
{
  "n_roi": 92,
  "corr_median": 0.6206,
  "localization_success_rate": 0.9348,
  "hkl_telemetry": {
    "hkl_source": "refined",
    "hkl_n_reflections": 69614,
    "hkl_mean_amplitude": 47.41,
    "hkl_path": ".../refined_structure_factors.mtz"
  },
  "calibration": {
    "spot_scale_override": 3.185e17,
    "N_cells": [36, 28, 26],
    "n_cells_applied": true
  }
}
```

## Artifacts
- plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/collect_db_at_024.log
- plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/pytest_db_at_024.log
- plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/mapping_metrics.json
- plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/mapping_metrics.csv
- plans/active/MAP-SCALE-004/reports/2025-11-06T010000Z/summary.md (this file)

## Exit Criteria Status
1. ✅ Telemetry implemented in `simulate_forward_once` (2025-11-05T220000Z)
2. ✅ DB_AT_024 asserts hardened (2025-11-05T220000Z)
3. ✅ Documentation synchronized (2025-11-06T010000Z) — this loop

## Mode: Docs Compliance
- **No production code changes** in this loop
- Telemetry field names preserved exactly: `hkl_source`, `hkl_n_reflections`, `hkl_mean_amplitude`, `hkl_path`
- Artifact references updated to 2025-11-06T010000Z per How-To Map
- SCALE-007 cross-linked in both documentation files
- Markdown table formatting preserved (pipes aligned, no parser issues)

## Next Actions
- Archive MAP-SCALE-004 artifacts during next housekeeping sweep
- Consider audit of CLI docs for refined telemetry references (optional follow-up)
