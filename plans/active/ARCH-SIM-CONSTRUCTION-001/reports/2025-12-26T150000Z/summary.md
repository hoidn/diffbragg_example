# ARCH-SIM-CONSTRUCTION-001 Loop Summary (2025-12-26T150000Z)

## Focus
Probe wiring repair: fix baseline probe helpers to accept CLI partiality flags, serialize simulator hook tensors to JSON-safe aggregates, and rerun mapped commands with evidence capture.

## Problem
Baseline probe `compare_stage_a_baseline.py` raised `NameError: name 'args' is not defined` when `--collect-simulator-partiality-stats` was enabled because helper functions `collect_stage_a_hkl_stats` and `collect_mapping_hkl_stats` referenced the global `args` object from `main()` without receiving it as a parameter. Additionally, even if the hook had run, raw torch tensors stored in `Simulator.partiality_stats` would have caused JSON serialization failures.

## Implementation
1. **Added serialization helper** (`_serialize_partiality_stats_to_json`, lines 209-263): Converts torch tensors to JSON-safe per-panel aggregates (min/median/max/has_nan/has_inf) for each field (f_latt, lorentz_factor, polarization_factor).
2. **Updated function signatures**: Added `collect_simulator_partiality_stats=False` parameter to both `collect_stage_a_hkl_stats` (line 275) and `collect_mapping_hkl_stats` (line 344).
3. **Fixed flag plumbing**: Replaced `args.collect_simulator_partiality_stats` with the parameter in both functions (lines 303, 368).
4. **Threaded flag from main()**: Updated both call sites in `main()` to pass `args.collect_simulator_partiality_stats` (lines 1944, 1961).
5. **Applied serialization**: Called `_serialize_partiality_stats_to_json` before storing partiality stats (line 322).

## Validation
- **Probe command**: Stage A baseline probe ran successfully with all flags enabled (--collect-hkl-stats, --collect-simulator-partiality-stats, etc.)
- **Partiality stats captured**: JSON output now contains non-empty `simulator_partiality_stats.stage_a` block with per-panel aggregates (panel 0: f_latt min=-37533.16, median=0.0001296, max=37069.60; lorentz_factor min=2.08, median=3.44, max=702.46; polarization_factor min=0.88, median=0.96, max=1.0)
- **DB-AT-028/029 tests**: Ran with artifacts captured; tests still fail as expected (chi²=2.098e5, ROI CC=-0.053) since underlying simulator physics issue remains unresolved
- **Artifacts written**: All outputs captured under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/`

## Key Metrics
- **f_latt median**: 0.0001296 (should be ≈ 5233.69 per partiality ledger expectations)
- **f_latt_squared median**: 0.999427 (nearly 1.0, indicating lattice partiality is near-zero)
- **lorentz_factor median**: 3.44 (matches expected range)
- **polarization_factor median**: 0.96 (matches expected range)
- **DB-AT-028 chi²/pixel**: 209790.45 (vs ≤1e2 spec)
- **DB-AT-029 median ROI CC**: -0.053 (vs ≥0.2 floor)

## Code Changes
- **File**: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py`
- **Lines added**: ~62 (serialization helper + parameter updates)
- **Lines modified**: 6 (function signatures + flag threading)

## Artifacts
- `stage_a_baseline_probe_baseline.json`: Stage A baseline probe output with simulator partiality stats
- `stage_a_baseline_probe_baseline.log`: Console output from probe run
- `db_at_028/db_at_028_metrics.json`: DB-AT-028 test metrics
- `db_at_029/db_at_029_metrics.json`: DB-AT-029 test metrics
- `pytest_db_at_028_029.log`: pytest execution log

## Next Boundary
The baseline probe now successfully captures simulator partiality hook output (f_latt, lorentz_factor, polarization_factor) in JSON-safe format. The median f_latt value (0.0001296) confirms the partiality ledger observation: Stage A is emitting near-zero lattice-weighted intensity even though inputs are correct. The next loop can now compare these simulator-reported values against the ledger expectations to justify the nanobrag_torch partiality implementation fix.

## Status
Phase C probe wiring complete. Probe helper instrumentation budget consumed (this was the final allowed probe before editing nanobrag_torch physics). Next action: Move to nanobrag_torch partiality implementation plan per supervisor guidance.
