# ARCH-SIM-CONSTRUCTION-001 — Supervisor Loop (2025-12-26T010000Z)

## Context
- **Divergence:** DB-AT-028/029 still fail with `chi2_per_pixel_initial ≈ 2.1e5` and `roi_cc_median_before ≈ -0.053` despite HKL coverage, Lorentz, and partiality-ledger instrumentation (see `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/spot_profile_summary.md`).
- **Latest evidence:** Partiality ledger shows `median StageA/(|F|²·F_latt²·LP) ≈ 0`, proving the simulator never applies lattice weighting.
- **Goal:** Instrument nanobrag_torch so we can observe the actual `F_latt` / LP factors emitted by the simulator, confirm the missing term, and unblock the next physics fix.

## Transformation Ledger Snapshot
| ROI | HKL | Evidence | Location |
| --- | --- | --- | --- |
| Panel 0 [644:656,21:33] | (-7,5,-3) | `StageA/Ref = 3.71e-05`, `StageA/|F|²·LP ≈ 0`, large LP=2.61, chi²/pixel initial fails | spot_profile_summary.md:64-107, db_at_028/db_at_028_metrics.json:2-33 |
| Panel 0 [661:673,940:952] | (1,-9,4) | `StageA/Ref = 8.46e-02`, LP=3.01 but StageA collapses despite |Δhkl|=0.233 | same as above |
| Panel 0 [535:547,842:854] | (2,-6,2) | `StageA/Ref = 1.32e-02`, `StageA/|F|²·LP ≈ 0`, resolution 4.14 Å | same |
| Panel 0 [257:269,37:49] | (-3,8,-9) | `StageA/Ref = 1.46e-03`, energy spilling outside ROI, LP gain absent | same |
| Panel 0 [144:156,619:631] | (4,1,-6) | Best case still `StageA/|F|²·LP = 4.78e-02` | same |
| Global | — | `median StageA/(|F|²·F_latt²·LP) ≈ 0`, `amp_sq_vs_ref median = 1.1447`, `n_masked_pixels = 4140` | stage_a_baseline_probe_baseline.json:111-140,3200-3210 |

## Next Actions
1. **Instrument simulator:** add `debug_config['collect_partiality_stats']` inside `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` so we can capture `lorentz_factor`, `polarization_factor`, `F_latt`, and `partiality_factor` per ROI without perturbing production.
2. **Thread debug flag:** update `dbex/refinement/stage_a_utils.py::_build_stage_a_context` (and the mapping cold path via `dbex/nanobrag_bridge.py::simulate_forward_once`) to pass the debug flag when requested.
3. **Probe wiring:** extend `compare_stage_a_baseline.py` with `--collect-simulator-partiality-stats` which toggles the new debug flag, records the simulator payload, and stores it next to the existing partiality ledger.
4. **Validation:** rerun the Stage A baseline probe plus DB-AT-028/029 selectors with artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/`.

## Guardrails
- Keep the simulator debug hook opt-in (default `debug_config=None`) to satisfy Environment Freeze.
- Probe budget for `compare_stage_a_baseline.py` is now exhausted; no further instrumentation may be added without attempting a production fix.
- All edits touching `src/nanobrag-torch` require patch files saved under `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/` if/when a fix lands.

## Artifacts to Capture
- `stage_a_baseline_probe_baseline.json` + `spot_profile_summary.md` with new `simulator_partiality_stats` block.
- `db_at_028` / `db_at_029` metrics + pytest log.
- Console logs proving the simulator debug hook ran (`collect_partiality_stats=True`).
