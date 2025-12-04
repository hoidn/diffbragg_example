# ARCH-SIM-CONSTRUCTION-001 Loop Summary — 2025-12-27T180000Z

## Context
- 2025-12-27T120000Z patch of the SQUARE lattice sincg path (float64 fractional deltas + downcast) **failed**:
  - Enforcement node `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` observed ratio 3.56M vs expected 1.45B (0.25% of the target).
  - Stage A baseline probe metrics (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/stage_a_baseline_probe_baseline.json`) still report `median StageA/(|F|^2·F_latt^2·LP)=0.0` and DB-AT-028 chi²≈1.0e6.
  - Float64 patch triggered CUDA OOM before being trimmed; downcast version avoids OOM but retains the deficit.
- Environment Freeze guard forbids further speculative simulator edits; we must instrument within the real path to understand why sincg(π·Δh, N) never returns the Na·Nb·Nc boost.

## Decision
Plan a **parity-localization** loop focused on instrumenting the simulator partiality hook so we can inspect `Δh,Δk,Δl` distributions and the individual sincg factors (not just the product) for real ROIs. Goal: prove whether HKL deltas are actually near-integer (where sincg should hit ±N) or whether the arguments live far enough away that the product collapses.

## Next Loop Focus
1. **Extend simulator partiality stats** (`nanobrag_torch/simulator.py::compute_physics_for_position`): when `debug_config['collect_partiality_stats']=True`, record per-panel histograms/percentiles for `delta_h`, `delta_k`, `delta_l`, and the individual sincg outputs (`F_latt_a/b/c`) before the product. Thread these values into the existing stats dict (no new probe scripts per ARCH-PROBE-FREEZE-001).
2. **Update `compare_stage_a_baseline.py`** to consume the new fields and render them in `spot_profile_summary.md` / JSON so we can correlate fractional deltas with the collapsed `F_latt` medians.
3. **Re-run the Stage A baseline probe** (baseline geometry, all ledger flags) and stash artifacts under this timestamp directory. Target evidence: buckets showing whether |Δh|<1e-3 for most ROIs and what the per-axis sincg distributions look like.
4. **(Optional)** rerun the partiality enforcement test after instrumentation to confirm behavior remains unchanged (still failing) but now backed by fractional-delta telemetry.

Artifacts for this planning loop: TBD (inputs only). The next engineer loop should drop fresh logs + probe outputs into this directory.
