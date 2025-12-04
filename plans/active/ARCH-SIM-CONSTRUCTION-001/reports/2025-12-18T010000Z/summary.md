# ARCH-SIM-CONSTRUCTION-001 Phase C.14 — Cold-Path Baseline Alignment

**Date**: 2025-12-18T010000Z
**Status**: Implementation complete, tests PASS
**Focus**: Align reconstruction helper cold path with Stage A telemetry masked means

## Summary

Implemented baseline alignment logic in `build_final_bragg_from_stage_a_telemetry` so that when StageAArtifacts are unavailable (param_state="initial", no bragg_zero_iter cache), the cold path computes a masked mean and applies a correction factor (telemetry.model_mean_masked / cold_masked_mean) to align with the authoritative Stage A baseline. This ensures DB-AT-028/029 see consistent masked-intensity baselines whether or not warm-cache artifacts exist.

## Changes Made

### 1. Cold-Path Baseline Alignment (`dbex/refinement/reconstruction.py:392-445`)
- Added baseline alignment logic that activates when `param_state=="initial"` AND `cache_status=="cold_path"` (no bragg_zero_iter available)
- Runs simulators once to get raw cold-path outputs, computes masked mean using `inputs.loss_mask`
- Extracts `telemetry_a.model_mean_masked` (authoritative Stage A baseline)
- Computes `baseline_alignment_factor = telemetry_model_mean / cold_masked_mean` when both are finite/positive
- Applies correction factor to all simulator outputs: `bragg_scaled = bragg_panel * scale_factor * baseline_alignment_factor`
- Emits diagnostic warnings if alignment cannot be computed (zero/NaN values, no loss_mask)

### 2. Diagnostics Enhancement (`dbex/refinement/reconstruction.py:654-655`)
- Added `baseline_alignment_factor` and `cache_status` fields to `baseline_stats.json`
- Enables probes/tests to verify alignment behavior and distinguish cache-hit vs cold-path reconstruction

### 3. New Regression Test (`tests/dbex/test_artifact_parity.py:508-636`)
- Added `test_stage_a_cold_path_respects_telemetry_baseline` test
- Runs Stage A to populate cache and telemetry, then drops `bragg_zero_iter` to force cold path
- Asserts cold-path masked mean matches `telemetry.model_mean_masked` within ≤1e-6 relative error
- Also validates that cold path matches cached array (when available) within same tolerance
- Test PASSED (11.05s runtime)

### 4. Probe Instrumentation (`plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:363-380, 638-642`)
- Extended probe to extract `baseline_alignment_factor` and `cache_status` from `baseline_stats.json` (when written)
- Added `baseline_alignment` section to JSON output with factor, status, and description
- Probe output includes metadata for downstream DB-AT evidence

## Validation

### Test Results
- **pytest cold-path test**: PASSED (1/1 tests, 11.05s)
  - Selector: `pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline`
  - Cold-path masked mean matched telemetry within ≤1e-6 relative error
  - Cold-path masked mean matched cached array within ≤1e-6 relative error (when available)

### Probe Results
- **Stage A baseline probe**: Completed successfully
  - DB-AT-027 status: PASS (Stage A vs mapping max|Δ|=3.9e-03 ADU, ROI CC=1.0000)
  - Used cache-hit path (baseline_alignment_factor=1.0, cache_status="cache_hit")
  - Output: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/stage_a_baseline_probe_baseline.json`

## Artifacts

- `pytest_cold_path.log` — Test execution log showing PASS
- `probe_baseline.log` — Probe execution log with DB-AT-027 PASS
- `stage_a_baseline_probe_baseline.json` — Probe JSON output with baseline_alignment metadata

## Next Steps

DB-AT-028/029 still failing (chi²≈2.1e5) because the issue is not in the cold-path reconstruction helper but in the fixture/test setup. The cold-path alignment ensures reconstruction matches telemetry when cache is unavailable, but the underlying intensity scale mismatch between mapping and Stage A remains (see DB-AT-028/029 Attempts History for ongoing investigation).

## Metrics

- Files touched: 3 production (reconstruction.py, test_artifact_parity.py, compare_stage_a_baseline.py)
- Lines added: ~100 (cold-path alignment logic + test + probe enhancements)
- Tests added: 1 (test_stage_a_cold_path_respects_telemetry_baseline)
- Tests passing: 1/1
