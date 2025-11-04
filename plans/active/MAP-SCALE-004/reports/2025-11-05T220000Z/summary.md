# MAP-SCALE-004 Implementation Summary

## Problem Statement
**Per `docs/spec-db-workflow.md §4` and `docs/spec-db-tracing.md §2`:**
> Zero-iteration helper (`simulate_forward_once`) and DB_AT_024 must surface structure-factor telemetry
> (hkl_source, reflection count, mean amplitude, MTZ path) to enforce refined MTZ usage and prevent regressions.

**Quoted SPEC requirement** (docs/spec-db-tracing.md:10-13):
> "Trace payload SHALL be produced by the same code paths used in production (no re‑derived physics)."

**ADR alignment:**
- ADR-DIAGNOSTICS-001: Torch diagnostics shall emit standardized metadata enabling reproducible parity debugging.
- SCALE-003/SCALE-004 findings: Zero-iteration must ingest and trace both calibration AND refined |F| to achieve thresholds.

## Search Summary
Searched `dbex/nanobrag_bridge.py:843-1094` (`simulate_forward_once`) and found `hkl_stats` already present in diagnostics (line 1085) but lacking provenance telemetry. CLI path (`dbex/refine_one.py:225-352`) showed reference implementation: `hkl_source`/`hkl_n_reflections`/`hkl_mean_amplitude`/`hkl_path` computed from MTZ loading logic and passed to `_write_torch_outputs`.

Test audit (`tests/dbex/test_mapping_consistency.py:149-359`) revealed string logging of `hkl_source` (line 254) without assertions, allowing silent regressions when refined MTZ path is omitted.

## Implementation
1. Extended `simulate_forward_once` signature (dbex/nanobrag_bridge.py:843-885) with `hkl_source` and `hkl_path` optional params.
2. Added telemetry dict to diagnostics return (dbex/nanobrag_bridge.py:1086-1091):
   ```python
   "hkl_telemetry": {
       "hkl_source": hkl_source if hkl_source is not None else None,
       "hkl_n_reflections": len(hkl_indices),
       "hkl_mean_amplitude": float(hkl_amplitudes.mean()),
       "hkl_path": hkl_path if hkl_path is not None else ""
   }
   ```
3. Updated DB_AT_024 test (tests/dbex/test_mapping_consistency.py:197-223,337-359):
   - Pass `hkl_source="refined"` and `hkl_path` when canonical assets provide refined MTZ
   - Assert telemetry fields present in diagnostics
   - Fail loudly if `hkl_source != "refined"` when refined assets available (regression guard)
   - Include telemetry in summary_metrics JSON for artifact traceability
4. Fixed `test_torch_diagnostics_metadata` mock (tests/dbex/test_refine_one_cli.py:511) to return real floats for score comparisons.

## Test Results
**Targeted DB_AT_024:** 1 passed in 29.71s (corr_median=0.6206, localization=0.935, telemetry confirmed refined source)
**CLI refined MTZ:** 1 passed in 3.21s
**Full test suite:** 66 passed, 3 skipped, 2 failed (pre-existing gradient tests: test_db_at_010_gradcheck_crystal_cell_a, test_db_at_010_gradcheck unrelated to this change)

## Metrics
- Diagnostics now expose 4 new telemetry fields (hkl_source/hkl_n_reflections/hkl_mean_amplitude/hkl_path)
- DB_AT_024 now fails on refined→raw regression (tested by assertion on line 350)
- 71 tests collected (no collection failures)

## Artifacts
- plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/pytest_db_at_024.log
- plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/pytest_cli_refined_mtz.log
- plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/pytest_full_suite.log
- plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/collect_db_at_024.log
- plans/active/MAP-SCALE-004/reports/2025-11-05T220000Z/summary.md (this file)

## Next Actions
- Mark MAP-SCALE-004 done in fix_plan.md
- Update docs/TESTING_GUIDE.md and docs/development/TEST_SUITE_INDEX.md with telemetry contract notes
- Consider archiving MAP-SCALE-003 artifacts during housekeeping
