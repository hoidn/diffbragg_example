# TOOLING-VIS-001 Loop Summary (2025-11-25T05:12:35Z)

## Problem Statement

Implement shared helper `emit_mapping_context_diagnostics` to capture mapping_context diagnostics (dataset paths, sigma provenance, HKL source/path, target/loss_mask stats, ROI CC/scale ratios, device) before gating assertions so failures preserve context.

**SPEC compliance**: docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances)

## Implementation

Created `dbex.vis.mapping.emit_mapping_context_diagnostics` helper (163 lines) that emits JSON diagnostics including:
- timestamp, stage_name, device
- dataset paths (expt, refl, mask, mtz)
- sigma provenance (external_lookup vs cli_override)
- HKL source/path
- target stats (mean, std, min, max over loss_mask)
- loss_mask coverage, n_rois
- optional ROI CC median and scale ratio (when bragg_model provided)
- sigma_floor_value, spot_scale_override

Integrated helper into:
1. `plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py` - emits `mapping_context_probe.json` before parity probe assertions
2. `tests/dbex/test_stage_a_smoke_parity.py` - fixture returns mapping_context + refgeom_dataload; both DB-AT-028 and DB-AT-029 tests emit `mapping_context_fixture.json` before assertions

Fixed variable name collision in probe script (`args` → `cli_args` for parser args)

## Test Results

**Parity probe on CUDA**: EXIT 0 (Stage A refinement completed)
- Artifacts: `plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/parity_probe/{parity_metrics.json,mapping_context_probe.json}`

**pytest DB-AT-028/029**: 2 tests collected, 2 FAILED (expected - diagnostics captured before failures)
- DB-AT-028 FAILED: chi²/pixel initial 1.084e+05 exceeds 1e2 bound (physics issue, not diagnostic tooling)
- DB-AT-029 FAILED: median(corr_before) -0.6828 < 0.2 (physics issue, not diagnostic tooling)
- Artifacts: `plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/db_at_028/{db_at_028_metrics.json,mapping_context_fixture.json}`, `db_at_029/{db_at_029_metrics.json,mapping_context_fixture.json}`

**pytest --collect-only**: 2 tests collected (DB-AT-028, DB-AT-029)

## Hard Gate Compliance

✓ mapping_context diagnostics (probe + fixture) exist under artifacts path
✓ DB-AT-028/029 metrics emitted before assertions
✗ mapping metrics still diverge - probe vs fixture deltas noted in artifacts for follow-up (not this loop's scope)

## Files Changed

- `dbex/vis/mapping.py`: +163 lines (emit_mapping_context_diagnostics helper, updated __all__)
- `plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py`: +13 lines (import, emit call, args→cli_args fix)
- `tests/dbex/test_stage_a_smoke_parity.py`: +18 lines (import, fixture return keys, 2× emit calls)

## Artifacts

All artifacts exist under `plans/active/TOOLING-VIS-001/reports/2025-11-25T051235Z/`:
- `parity_probe.log`, `parity_probe/parity_metrics.json`, `parity_probe/mapping_context_probe.json`
- `pytest_db_at_028_029.log`, `pytest_db_at_028_029_collect.log`
- `db_at_028/db_at_028_metrics.json`, `db_at_028/mapping_context_fixture.json`
- `db_at_029/db_at_029_metrics.json`, `db_at_029/mapping_context_fixture.json`

## Next Actions

Per input.md Phase D.D: "If mapping metrics still diverge, note probe vs fixture deltas (ROI CC, scale_ratio, target means) in summary.md for follow-up."

**Divergence observed** (recorded for follow-up, not blocking this loop):
- Probe mapping forward: roi_cc_median_mapping ≈ 1.0, scale_ratio_mapping ≈ 1.0 (from parity_metrics.json)
- Fixture DB-AT-029: median_corr_before = -0.6828 (from db_at_029_metrics.json)

The diagnostic tooling is now complete and functional per TOOLING-VIS-001 requirements. Physics/parity issues are orthogonal and tracked separately.
