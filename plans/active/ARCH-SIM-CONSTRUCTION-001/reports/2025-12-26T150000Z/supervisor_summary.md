# ARCH-SIM-CONSTRUCTION-001 — Supervisor Loop (2025-12-26T150000Z)

## Evidence
- **DB-AT failures persist.** Latest Stage A smoke artifacts still show deterministic DMI: `chi2_per_pixel_initial=2.10e5` and `roi_cc_median_before=-0.053` in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T010000Z/db_at_028/db_at_028_metrics.json:2-63` and the matching DB-AT-029 metrics file lines 1-36.
- **Mapping vs Stage A mismatch is structural.** The baseline probe reports `target_mean_masked=87.118 ADU`, identical Stage A telemetry, but `chi_squared_per_pixel_initial=1.00e6` with a 3.25e3 ADU max difference vs mapping (`stage_a_baseline_probe_baseline.json:34-108`).
- **Partiality ledger isolates the missing term.** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-25T010000Z/spot_profile_summary.md:83-169` shows median `StageA/|F|²·LP=0.0176` and median `StageA/|F|²·F_latt²·LP≈0`, with worst-case ROIs diverging by 5–6 orders of magnitude (rows 64-153). Independent `|F|²` vs reflection ratios stay ≈1×, so the simulator is emitting almost no lattice-weighted energy even though the inputs are correct.
- **New simulator hook is not yet producing evidence.** Although `--collect-simulator-partiality-stats` was wired through the probe CLI, both Stage A and simulate_forward_once HKL stats now raise `"name 'args' is not defined"` and the `simulator_partiality_stats.stage_a` list is empty (`stage_a_baseline_probe_baseline.json:25-37`). The helper functions call `args.collect_simulator_partiality_stats` but never receive the CLI `args` object, so the instrumentation path never runs.

## Conclusion
- Architecture contracts from `docs/spec-db-conformance.md:255-349` (DB-AT-027/028/029) are still violated: Stage A and mapping bragg stacks do not match, chi²/pixel exceeds the 1e2 gate, and ROI correlations remain negative.
- The partiality ledger provides decisive localization (deterministic ≈0 ratios when `F_latt²` is included), but we still lack the “actual vs expected” comparison from the simulator hook. Until the baseline probe can serialize the hook output, we cannot close the boundary-bisection loop and move to the production fix.

## Next Action
1. **Fix the probe wiring.** Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` so `collect_stage_a_hkl_stats` / `collect_mapping_hkl_stats` accept the CLI flags instead of reaching for an undefined global `args`. Pass a `debug_config` object that includes both `collect_hkl_stats` and `collect_partiality_stats` down to `_build_stage_a_context` and `simulate_forward_once`.
2. **Summarize simulator stats for JSON.** The hook currently stores full torch tensors inside `Simulator.partiality_stats`, which would explode if serialization worked. Reduce these tensors to per-panel aggregates (min/median/max for `f_latt`, `lorentz_factor`, `polarization_factor`, etc.) so the probe emits compact, JSON-serializable summaries.
3. **Rerun the mapped commands.** Execute the Stage A baseline probe with `--collect-simulator-partiality-stats` and the DB-AT-028/029 selectors, writing artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/`. The JSON must now include a non-empty `simulator_partiality_stats.stage_a` block and the HKL stats sections should no longer report the NameError.

Once the hook evidence lands, we can compare the simulator-reported `F_latt` against the ledger to justify the nanobrag_torch partiality fix.
