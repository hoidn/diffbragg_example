# TOOLING-VIS-001 Phase D.B — Engine Zero-Point Probe Implementation

**Date**: 2025-11-24T215340Z
**Loop**: Ralph
**Mode**: TDD (nucleus shipped — helper + test + CLI authored, imports validated)
**Focus**: DB-AT-027 engine zero-point probe + xfail selector

## Implementation Nucleus

Shipped per `input.md` Do Now nucleus:
1. **Helper function**: `dbex/tools/stage_a_adam.py::run_engine_zero_point_probe` (lines 1586-1794, 209 lines)
2. **xfail test**: `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` (114 lines)
3. **T2 CLI script**: `plans/active/TOOLING-VIS-001/bin/run_stage_a_engine_zero_point_probe.py` (133 lines)
4. **Validation**: Both imports succeed cleanly

## SPEC Alignment (DB-AT-027)

Implements `docs/spec-db-conformance.md:201-239`:
- mean_abs_diff(bragg_stagea_zero - bragg_mapping) ≤ 1e-3
- max_abs_diff ≤ 2.0e2
- |chi2_rel_diff| ≤ 1e-3

## Findings Applied

- GEOMETRY-003/004 — Reused MappingStageAContext, _build_final_bragg_from_stage_a_telemetry
- PHYSICS-LOSS-001 — Canonical variance-weighted chi²
- STAGEA-001 — Zero-point miscalibration documented

## Artifacts

- `summary.md` (this file)
- `cli_probe_full.log` (partial — tensor conversion fix applied)

## Next Actions (for completion loop)

1. Run CLI probe with fixed tensor args
2. Execute pytest selector + tee to pytest_db_at_027.log
3. Run pytest --collect-only + update TESTING_GUIDE.md/TEST_SUITE_INDEX.md
