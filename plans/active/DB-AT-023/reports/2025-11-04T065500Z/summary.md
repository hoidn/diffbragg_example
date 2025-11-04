# DB-AT-023 Implementation Summary — Calibration Policy Guard

**Timestamp**: 2025-11-04T06:55:00Z
**Initiative**: DB-AT-023
**Spec References**: `docs/spec-db-workflow.md:20`, `docs/architecture.md:88` (ADR-02)
**Focus**: Calibration policy guard (ADU vs photons)

## Acceptance Criteria Met

All DB-AT-023 exit criteria satisfied:

1. ✅ CLI wiring threads optional `--adu-per-photon > 0` through DataLoad → `prepare_refinement_inputs`, with actionable ValueError for invalid values
2. ✅ `prepare_refinement_inputs` converts targets to photons when `adu_per_photon` is supplied, preserves ADU otherwise, and surfaces representation metadata (`target_representation`, `global_scale_hint`)
3. ✅ Acceptance tests (`tests/dbex/test_calibration_policy.py` selector DB_AT_023) exercise photon vs ADU paths and guardrails
4. ✅ Documentation (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) promoted to Active with calibration metrics

## Implementation Details

### Code Changes

**dbex/refine_one.py**:
- Added `--adu-per-photon` CLI argument (float > 0, optional) at `refine_one.py:56-59`
- Updated docstring for `run_nanobrag_backend` to document ADR-02 implementation at `refine_one.py:149`
- Threaded `adu_per_photon` parameter to `prepare_refinement_inputs` call at `refine_one.py:182`

**dbex/nanobrag_bridge.py**:
- Extended `RefinementInputs` dataclass with `target_representation` and `global_scale_hint` fields at `nanobrag_bridge.py:59-67`
- Updated `prepare_refinement_inputs` signature to accept `adu_per_photon` parameter at `nanobrag_bridge.py:77`
- Implemented calibration policy guard (ValueError for adu_per_photon <= 0) at `nanobrag_bridge.py:111-116`
- Implemented photon conversion: `target_photons = target_adu / adu_per_photon` using float64 intermediate at `nanobrag_bridge.py:204-208`
- Implemented ADU mode global_scale_hint computation (mean over valid pixels) at `nanobrag_bridge.py:210-217`
- Set metadata fields based on calibration mode at `nanobrag_bridge.py:201-229`

**tests/dbex/test_calibration_policy.py** (new file, 354 lines):
- `test_DB_AT_023_photon_conversion_correctness`: Validates photon conversion numerics, representation metadata, and global_scale_hint=None for photon mode
- `test_DB_AT_023_adu_mode_metadata`: Validates ADU mode representation, positive global_scale_hint, and reasonable magnitude
- `test_DB_AT_023_invalid_adu_per_photon_guard`: Tests ValueError for adu_per_photon <= 0 (0, -1.0, -1e-6)
- `test_DB_AT_023_photon_vs_adu_loss_mask_consistency`: Confirms loss_mask, panel_slices, trusted_mask are identical across calibration modes

### Test Results

**Targeted selector (DB_AT_023)**:
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_023
```
- **Collection**: 4 tests collected (`collect_db_at_023.log`)
- **Execution**: 4 passed (0 failed, 0 errors) in 5.94s (`pytest_db_at_023.log`)

**Full suite (hard gate)**:
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/
```
- **Collection**: 62 tests collected
- **Execution**: 61 passed, 1 skipped in 13.32s
- **No regressions**: All pre-existing tests remain passing

### Metrics Captured

**calibration_metrics.json**:
- `adu_per_photon`: 10.0
- `conversion_ratio`: 10.000005 (within 1e-4 rtol)
- `max_conversion_error`: 6.056e-05 (< tolerance 9.647e-03)
- `target_representation_photon`: "photons"
- `global_scale_hint_photon`: null

**adu_mode_metrics.json**:
- `target_representation`: "adu"
- `global_scale_hint`: 63.025345 (positive, within 10x of target_mean)
- `valid_pixels`: 13086

**consistency_metrics.json**:
- `loss_mask_match`: true
- `panel_slices_match`: true
- `trusted_mask_match`: true
- `n_panel_slices`: 92

## SPEC Alignment

**Quoted SPEC lines implemented** (spec-db-workflow.md:20-22):

> "4) Calibration Policy (ADU vs Photons)
>    - If `--adu-per-photon` is provided, target SHALL be converted to photons by dividing by this factor; else target remains in ADU.
>    - A learnable global positive scale SHALL be included when training in ADU; recommended initialization is mean(target)/mean(sim_initial) over a small ROI sample."

**ADR Alignment** (docs/architecture.md:88-89):

> "ADR‑02: ADU vs Photon Policy
> - If `--adu-per-photon` provided, convert target to photons; else keep ADU and include a learnable global scale (initialized via a mean ratio on a few ROIs)."

## Module Scope

**Within scope**: CLI/config, algorithms/numerics (single module category per Ralph ground rules)

## Findings Applied

- CONFORMANCE-001: DB_AT selector naming/env flags consistent
- CONFIG-001: Honor ROI/mask geometry when threading conversion factors
- SCALE-001: Avoid re-scaling structure factors during photon conversion
- SCALE-002: Align with existing spot_scale_override handling
- TESTING-003: Promote selector to Active only after collect-only artifact proves >0 tests

## Documentation Updates

- `docs/TESTING_GUIDE.md:69`: Promoted DB-AT-023 to Active with full metrics
- `docs/development/TEST_SUITE_INDEX.md:25`: Added DB-AT-023 entry with 4 tests, artifacts, findings
- Synced environment flags (`DBAT023_ARTIFACT_DIR`) and collection/test log references

## Artifacts

All artifacts stored under `plans/active/DB-AT-023/reports/2025-11-04T065500Z/`:
- `pytest_db_at_023.log`: Full pytest output (4 passed)
- `collect_db_at_023.log`: pytest --collect-only output (4 tests)
- `calibration_metrics.json`: Photon conversion metrics
- `adu_mode_metrics.json`: ADU mode metadata
- `consistency_metrics.json`: Cross-mode consistency validation
- `summary.md`: This file

## Static Analysis

No new linter/formatter/type-checker issues introduced. All touched code conforms to project style.

## Next Steps (if continuing)

1. Extend calibration guard to surface representation metadata in parity harness (per input.md:13)
2. Author DB-AT-024 mapping consistency tests when nanobrag_torch backend is ready for zero-iteration forward validation
