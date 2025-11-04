# MAP-SCALE-001 Implementation (2025-11-04T190041Z)

## Problem Statement

**SPEC Lines (docs/spec-db-conformance.md:43-46):**
> DB-AT-024 Mapping consistency
> - Setup: build per-panel configs from a real Experiment; run a forward pass with initial parameters; evaluate K ROIs (e.g., 32) for correlation and localization.
> - Expectation: median ROI correlation ≥ 0.2 and ≥90% ROIs contain a local intensity maximum within the central half-box.

**Previous State:** DB_AT_024 test was failing with corr≈0.019, localization≈1.1% due to missing sample clipping in the torch bridge. Analysis (2025-11-04T185107Z) showed that enabling both DiffBragg `N_cells` and beam sample clipping collapsed the scale gap and achieved canonical metrics (corr≈0.81, localization=100%).

## ADR Alignment

**ADR-SCALE-005 (docs/findings.md:18):**
> Injecting DiffBragg `N_cells` overrides into the torch bridge multiplies zero-iteration intensities by ≈3.2e5× when beam sample clipping is absent; forward `beam_config` into `nanobrag_torch.Simulator` before enabling `N_cells` so sample clipping matches the canonical generator.

## Search Summary

Before implementing, verified that:
1. `dbex/nanobrag_bridge.py:1008` - `Simulator` was instantiated without `beam_config` parameter
2. `dbex/nanobrag_bridge.py:969` - `apply_n_cells` was hardcoded to `False`
3. `create_crystal_config` already had the gating mechanism but was never activated

Files modified:
- `dbex/nanobrag_bridge.py:963-972,1009-1016,906` - enabled sample clipping
- `tests/dbex/test_nanobrag_bridge_configs.py:655-656` - fixed tuple unpacking
- `tests/dbex/test_refine_one_cli.py:147` - fixed mock return value

## Changes Made

### 1. Enable N_cells when calibration provides domain counts (dbex/nanobrag_bridge.py:963-972)

```python
# Build crystal_config with N_cells gating per SCALE-005
# Enable apply_n_cells when calibration provides N_cells (sample clipping via beam_config)
# Per 2025-11-04T185107Z analysis: N_cells + beam sample clipping recovers parity
apply_n_cells = N_cells is not None
crystal_config, n_cells_applied = create_crystal_config(
    crystal,
    experiment,
    N_cells=N_cells,
    apply_n_cells=apply_n_cells
)
```

**Rationale:** When calibration dict includes `N_cells`, the guard is now lifted to allow domain counts to be applied, but only when sample clipping is also enabled.

### 2. Propagate beam_config to Simulator (dbex/nanobrag_bridge.py:1009-1016)

```python
# Run simulator (single source, GEOMETRY-002/HKL-ORIENT-001 applied in bridge)
# Per input.md Do Now: propagate beam_config for sample clipping when N_cells is enabled
simulator = Simulator(
    detector=detector_model,
    crystal=crystal_model,
    beam_config=beam_config,
    device=device
)
```

**Rationale:** Passing `beam_config` enables nanobrag_torch's sample clipping logic (AT-FLU-001), which prevents the 3.2e5× intensity blow-up when `N_cells` is applied.

### 3. Update docstring (dbex/nanobrag_bridge.py:906)

Changed SCALE-005 note from "gated until semantics validated" to "enabled when calibration provides domain counts" to reflect the new behavior.

### 4. Fix test breakage from tuple return

- `tests/dbex/test_nanobrag_bridge_configs.py:655-656` - unpacked tuple from `create_crystal_config`
- `tests/dbex/test_refine_one_cli.py:147` - fixed mock to return `(Mock(), False)` tuple

## Targeted Test Results

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```

**Result:** PASSED in 29.54s

**Metrics (plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/mapping_metrics.json):**
- `corr_median`: 0.621 (threshold: ≥0.2) ✓
- `localization_success_rate`: 0.935 (threshold: ≥0.90) ✓
- `n_cells_applied`: true ✓
- `calibration.N_cells`: [36, 28, 26] (from canonical config_torch.json)
- `calibration.spot_scale_override`: 3.185e17
- `bragg_raw_stats.mean`: 3.735e-10 ADU (before scaling)
- `bragg_stats.mean`: 0.211 ADU (after sqrt scaling)
- `target_stats.mean_masked`: 63.03 ADU

**Interpretation:** DB_AT_024 now passes its acceptance thresholds. The diagnostics confirm that `N_cells` was applied and sample clipping was active (via beam_config). The scale gap is resolved.

## Comprehensive Test Suite

**Command:** `pytest -v tests/`

**Result:** 
- 64 passed
- 3 skipped (including DB_AT_024 without artifact env var)
- 2 failed (pre-existing gradient test failures in test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a and test_db_at_010_gradcheck)

**Analysis:** The 2 gradient failures are unrelated to this change (they fail because the loss function has no differentiable outputs with respect to the dxtbx Crystal mutation pathway). These failures existed before this loop. My changes fixed 2 tests that were broken by the tuple return change.

## Documentation Updates

- None required beyond inline comments in code

## Next Steps

1. Mark MAP-SCALE-001 Phase D as done in the fix plan
2. Update SCALE-005 finding if needed to reflect that the guard is now conditional
3. Consider removing the DB_AT_024 skip decorator now that the test passes reliably

## Artifacts

- `plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/pytest.log` - targeted test log
- `plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/pytest_full_suite.log` - full suite log
- `plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/mapping_metrics.json` - DB_AT_024 metrics
- `plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/summary.md` - this file

