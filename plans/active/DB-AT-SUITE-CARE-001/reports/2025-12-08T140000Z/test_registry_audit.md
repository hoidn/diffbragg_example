# TEST_SUITE_INDEX Hygiene Audit

**Initiative:** DB-AT-SUITE-CARE-001 Phase D.4
**Date:** 2025-12-08T140000Z
**Auditor:** Ralph (Loop i=194)

## Executive Summary

This audit cross-references `docs/development/TEST_SUITE_INDEX.md` and `docs/TESTING_GUIDE.md` §2 to verify selector registry consistency. The registries are **well-synchronized** with no orphaned or stale selectors detected.

- **Total Active selectors in TEST_SUITE_INDEX.md:** 26
- **Total Active entries in TESTING_GUIDE.md §2:** 26 (matching)
- **Collection verification:** 189 tests collected, all selectors functional
- **Orphaned entries:** 0
- **Stale entries:** 0

## Full Selector Inventory

### Implementation Coverage (Active) — TEST_SUITE_INDEX.md

| ID | Selector Pattern | Collection Count | TESTING_GUIDE Status | Notes |
|----|------------------|------------------|---------------------|-------|
| 1 | `tests/dbex/test_nanobrag_bridge.py` | 5 | Present §2.1 | Bridge tensors & masks |
| 2 | `tests/dbex/test_nanobrag_bridge_configs.py` | varies | Present §2.1 | Config hydration |
| 3 | `tests/dbex/test_nanobrag_smoke.py` | 3 | Present §2.1 | Smoke harness |
| 4 | `tests/dbex/test_torch_refine_smoke.py` | varies | Present §2.1 | Stage A/B/C smokes |
| 5 | `tests/dbex/test_refine_one_cli.py` | 15 | Present §2.1 | CLI backend flag |
| 6 | `tests/dbex/test_data_load_sigma_map.py` | varies | Present §2.1 | Sigma map ingestion |
| 7 | `tests/sp_proc/test_sigma_metadata_fixture.py` | varies | Present §1.4 | Sigma metadata manifest |
| 8 | `tests/dbex/test_ub_parameterization_roundtrip.py` | 4 | Present §2 | DB-AT-026 |
| 9 | `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` | 1* | Present §2 | DB-AT-027 (*2 collected with broader match) |
| 10 | `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` | 1 | Present §2 | DB-AT-028 |
| 11 | `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity` | 1 | Present §2 | DB-AT-029 |
| 12 | `-k DB_AT_020` | 2 | Present §2 | Reflection Ingestion Sanity |
| 13 | `-k DB_AT_021` | 3 | Present §2 | Mask Semantics Guard |
| 14 | `-k DB_AT_022` | 3 | Present §2 | Background Sentinel Guard |
| 15 | `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` | 1 | Present §2 | ARCH-ENGINE-001 |
| 16 | `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` | 1 | Present §2.1 | ARCH-REFINE-FLOW-001 StageC |
| 17 | `tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry` | 1 | Present §2.1 | ARCH-REFINE-FLOW-001 Phase E |
| 18 | `tests/dbex/test_roi_analysis.py::TestScoreROIPayloads` | 5 | Present §2 | ARCH-BRIDGE-RESP-001 ROI Scoring |
| 19 | `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity` | 1 | Present §2 | TORCH-API-ALIGN-001 A1 |
| 20 | `tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes` | 2 | Present §2 | TORCH-API-ALIGN-001 A2 (xfail) |
| 21 | `tests/dbex/test_experiment_parity.py::test_parity_small_fixture` | 1 | Present §2 | TORCH-API-ALIGN-001 A3 (xfail) |
| 22 | `tests/dbex/test_bridge_custom_override.py::test_custom_override_exploratory` | 1 | Present §2 | TORCH-API-ALIGN-001 A4 (xfail) |
| 23 | `tests/architecture/test_gradient_contracts.py::TestGradientContracts` | 5 | Present §5.1 | ARCH-GRADIENT-FLOW-001 |
| 24 | `tests/architecture/test_nanobrag_partiality.py` | 2 | Present §5.2 | SQUARE Lattice Partiality |
| 25 | `tests/dbex/test_runtime_vectorization.py` | 1 | Present §2 | RUNTIME-VEC-001 |
| 26 | `tests/architecture/test_telemetry_surfaces.py` | 3 | Present §5.1 | ARCH-TELEMETRY-002 |

### DB-AT Selector Collection Summary

| Selector | Collection Count | Status |
|----------|------------------|--------|
| `-k DB_AT_001` | 15 | Active |
| `-k DB_AT_002` | 2 | Active |
| `-k DB_AT_010` | 5 | Active |
| `-k DB_AT_020` | 2 | Active |
| `-k DB_AT_021` | 3 | Active |
| `-k DB_AT_022` | 3 | Active |
| `-k DB_AT_023` | 4 | Active |
| `-k DB_AT_024` | 1 | Active |
| `-k DB_AT_026` | 4 | Active |
| `-k DB_AT_027` | 2 | Active |
| `-k DB_AT_028` | 1 | Active |
| `-k DB_AT_029` | 1 | Active |

## Gap Analysis

### Entries in TEST_SUITE_INDEX.md but NOT in TESTING_GUIDE.md

**None found.** All Active selectors in TEST_SUITE_INDEX.md have corresponding entries in TESTING_GUIDE.md.

### Entries in TESTING_GUIDE.md but NOT in TEST_SUITE_INDEX.md

**None found.** The registry is synchronized.

### Orphaned Entries (selector doesn't collect tests)

**None found.** All selectors collect ≥1 test.

### Stale Entries (outdated information)

**None found.** Artifact paths, environment variables, and spec references are current.

## Consistency Observations

### Environment Variable Coverage

Both documents correctly specify:
- `KMP_DUPLICATE_LIB_OK=TRUE` — required for all PyTorch tests
- `NANOBRAGG_DISABLE_COMPILE=1` — required for gradcheck tests
- `DBEX_SMOKE_DETECTOR_SIZE={small,full}` — detector size selection
- `DBEX_SMOKE_SIGMA_SOURCE={cli_override,metadata}` — sigma source selection
- Various `DBAT0XX_ARTIFACT_DIR` environment variables for artifact capture

### Spec Reference Coverage

All Active entries include spec references in the Notes column:
- `docs/spec-db-core.md` — 12 references
- `docs/spec-db-workflow.md` — 10 references
- `docs/spec-db-conformance.md` — 8 references
- `docs/config_crosswalk.md` — 4 references
- Various architecture docs — 6 references

### Artifact Path Consistency

All Active entries with artifacts document paths under:
- `plans/active/<INITIATIVE-ID>/reports/<TIMESTAMP>/`
- `archive/plans/<INITIATIVE-ID>/reports/<TIMESTAMP>/` (for archived plans)

## Minor Observations

### Unregistered pytest Mark Warning

The `pytest.mark.acceptance` mark in `tests/dbex/test_ub_parameterization_roundtrip.py:150,213` is unregistered. This is a cosmetic warning that does not affect test execution or collection.

**Recommendation:** Register the `acceptance` mark in `pyproject.toml` or remove the mark if not used for selection.

### Plan-local Visualization Drivers

TEST_SUITE_INDEX.md correctly documents that plan-local visualization drivers under `plans/active/TOOLING-VIS-001/bin/` are **not** pytest selectors and directs users to TESTING_GUIDE.md §2.4.

## Recommendations

1. **No immediate action required** — The registries are synchronized and functional.

2. **Optional: Register `acceptance` mark** — Add to `pyproject.toml` to suppress warning:
   ```toml
   [tool.pytest.ini_options]
   markers = [
       "acceptance: marks tests as acceptance tests",
   ]
   ```

3. **Maintenance cadence** — Continue D.4 audits quarterly or after major test additions.

## Collection Evidence

Full collection log saved to: `collect_all_tests.log`

```
189 tests collected in 2.16s
```

## Conclusion

The TEST_SUITE_INDEX.md and TESTING_GUIDE.md registries are **consistent and healthy**. No orphaned, stale, or missing entries were detected. All Active selectors collect tests successfully.

---
*Audit completed 2025-12-08T140000Z*
