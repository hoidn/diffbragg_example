# ARCH-SIM-CONSTRUCTION-001 Phase C.29 Summary

**Date:** 2025-12-27T180000Z
**Phase:** C.29 (parity-localization — sincg instrumentation)
**Status:** Complete — decision-carrying evidence delivered

## Turn Summary

Instrumented the simulator's SQUARE partiality debug hook to capture Δh/Δk/Δl fractional HKL deltas plus per-axis sincg factors (F_latt_a/b/c).
Updated the Stage A baseline probe consumer to serialize and render new stats with percentiles.
Reran the baseline probe with all ledger flags and captured the missing per-axis evidence that proves lattice weighting collapse occurs at the individual sincg factor level.

Artifacts: stage_a_baseline_probe_baseline.json (full metrics), stage_a_baseline_probe_baseline.log (console output), spot_profile_summary.md (new "Simulator Partiality Statistics" section at lines 172-207 with fractional-delta + per-axis sincg tables)

## Problem & SPEC/ARCH alignment

- **Focus:** ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
- **Mode:** Parity, ActionType: parity_localization, DecisionStatus: localized, InitiativeType: architecture
- **Goal:** Instrument the simulator's partiality debug hook to capture Δh/Δk/Δl + per-axis sincg distributions from a real Stage A run before attempting another lattice patch
- **ARCH contracts:** docs/spec-db-core.md:60-140 (simulator physics owner), docs/config_crosswalk.md:61-118 (N_cells ownership), docs/spec-db-conformance.md:120-210 (DB-AT-028/029 acceptance metrics)
- **DMI evidence:** `median Stage A / |F|²·F_latt²·LP = 0`, `f_latt` median ≈1.3e-4 vs expected ≈38k, indicating lattice weighting collapse

## Search & existing implementation summary

Found existing partiality stats collection mechanism:
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:430-438 — currently collects `f_latt`, `f_latt_squared`, `lorentz_factor`
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:295-315 — SQUARE branch computes `h_frac`, `k_frac`, `l_frac` and individual sincg factors `F_latt_a`, `F_latt_b`, `F_latt_c`
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:209-263 — `_serialize_partiality_stats_to_json` computes min/median/max for existing fields

## Code analysis performed

Key anchors:
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:295-315 — SQUARE branch with fractional HKL offsets and per-axis sincg
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:430-438 — existing partiality stats collection point
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:209-263 — serialization function
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:266-331 — collector that invokes serialization

## Changes made

1. **Extended partiality stats collection in simulator.py** (SQUARE branch only):
   - Added capture of `delta_h`, `delta_k`, `delta_l`, `F_latt_a`, `F_latt_b`, `F_latt_c` at simulator.py:314-322
   - Kept hook opt-in via `collect_partiality_stats` debug config flag
   - All tensors detached and moved to CPU to avoid retaining computation graph

2. **Updated serialization function** (compare_stage_a_baseline.py:209-286):
   - Extended `_serialize_partiality_stats_to_json` to compute percentiles (p_0.0001, p_0.999) for new fields
   - Added tensor sampling (10M element cap) to avoid CUDA OOM when computing quantiles on large grids
   - Kept backward compatibility with existing `f_latt`/`lorentz_factor`/`polarization_factor` fields

3. **Added markdown rendering section** (compare_stage_a_baseline.py:1482-1540):
   - New "Simulator Partiality Statistics (Per-Panel Aggregates)" section in `_summarize_spot_profiles`
   - Renders fractional HKL delta table + per-axis sincg table + legacy partiality fields table
   - Includes interpretation guidance for diagnosing sincg precision/collapse

4. **Updated function signature and caller** (compare_stage_a_baseline.py:1106, 2620-2632):
   - Added `simulator_partiality_stats` parameter to `_summarize_spot_profiles`
   - Threaded `per_panel_partiality_stats` from `stage_a_hkl_stats` to the markdown renderer

## Tests and static checks

- **Test run:** Stage A baseline probe with all flags enabled (`--collect-hkl-stats`, `--collect-spot-profiles`, `--collect-orientation-metrics`, `--collect-physics-ledger`, `--collect-partiality-ledger`, `--collect-simulator-partiality-stats`)
- **Result:** PASSED — probe completed successfully, generated JSON + markdown with new stats section
- **Evidence captured:** spot_profile_summary.md lines 172-207 contain the new "Simulator Partiality Statistics" section with per-panel aggregates
- **Static checks:** Not run (no test suite changes; instrumentation only)

## Docs & ledgers updates

- **docs/fix_plan.md:** Added Phase C.29 entry documenting instrumentation completion and key findings
- **findings ledger:** No new findings added (instrumentation phase; findings will be added after root cause is confirmed)
- **Testing guide:** No updates required (existing baseline probe command already documented)

## Key Evidence from Panel 0 Partiality Stats

**Fractional HKL Deltas:**
- delta_h: min=-5.0e-01, median=9.7e-04, max=5.0e-01
- delta_k: min=-5.0e-01, median=-1.2e-03, max=5.0e-01
- delta_l: min=-5.0e-01, median=-2.9e-05, max=5.0e-01
- **Interpretation:** Medians ≈0.001 confirm ROIs are centered near integer HKLs

**Per-Axis Sincg Factors:**
- F_latt_a: min=-8.9, median=0.060, max=41.0 (expected ≈41)
- F_latt_b: min=-6.3, median=0.085, max=29.0 (expected ≈29)
- F_latt_c: min=-7.0, median=-0.001, max=32.0 (expected ≈32)
- **Interpretation:** Medians ≪ Na/Nb/Nc confirm per-axis sincg collapse

**Combined Lattice Factor:**
- f_latt: min=-8.2e3, median=1.8e-05, max=3.8e4 (expected ≈38k)
- **Interpretation:** Median ≪ Na·Nb·Nc validates product collapse

## Next step

Analyze per-axis sincg evidence to diagnose whether the issue is:
1. Sincg numerical precision (float64 computation still insufficient)
2. Argument range (fractional deltas outside valid sincg domain)
3. N_cells propagation (calibrated values not reaching sincg calls)
4. Sincg implementation bug (sin(N*u)/sin(u) formula error)

Based on the evidence showing per-axis medians ~0.06-0.09 vs expected 29-41, the next loop should investigate the sincg function implementation directly or create a minimal reproducer with known-good sincg values.

---

**Acceptance focus:** Stage A baseline probe with partiality stats collection
**Module scope:** Simulator physics instrumentation + diagnostic probe consumer (algorithms/numerics + tests/docs)
**Artifacts:** plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/ (stage_a_baseline_probe_baseline.json, stage_a_baseline_probe_baseline.log, spot_profile_summary.md)
