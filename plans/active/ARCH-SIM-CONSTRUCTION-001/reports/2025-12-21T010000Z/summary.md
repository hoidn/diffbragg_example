# ARCH-SIM-CONSTRUCTION-001 — 2025-12-21T010000Z Supervisor Notes

## Evidence recap
- Transformation ledger at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/transformation_ledger.md` shows Stage A vs reflection deltas spanning 7.1e-5× to 234× even though global masked means match (target/model=87.118 ADU). Representative ROIs: panel 0 [275:287,303:315] overshoots by +1.59e3 ADU while [350:362,877:889] collapses by -11.2 ADU.
- ROI diagnostics inside `stage_a_baseline_probe_baseline.json` (same directory) confirm Stage A and mapping agree per ROI (CC≈1.0) yet DB-AT-028/029 still fail because median ROI correlation with target is -0.053 and `chi²/pixel=9.8e5`.
- Static audit of `dbex/refinement/config_factories.py::create_crystal_config` shows stills runs always force `mosaic_spread_deg=0.0` / `mosaic_domains=1` regardless of experiment metadata (`refGeom_small.expt` embeds `ML_half_mosaicity_deg=3.18e-3°`). The simulator therefore models a perfect crystal with zero mosaicity, concentrating energy into a few ROIs and starving the rest.

## Hypothesis
Injecting the measured mosaic spread from the DIALS experiment (`ML_half_mosaicity_deg`) into every `CrystalConfig` (Stage A, mapping, reconstruction) will smear intensity across the same ROI footprint used in the target/mapping data, collapsing the per-ROI deltas logged in the transformation ledger. Without that blur Stage A recreates the infinite-crystal sinc envelope, explaining the handful of >200× spikes and the 99 % deficits everywhere else.

## Next actions (handed to Ralph via input.md)
1. Teach `create_crystal_config` to read `ML_half_mosaicity_deg` (and optionally `ML_domain_size_ang` when `N_cells` is absent) from `experiment.crystal.to_dict()` and thread it through `CrystalConfig`.
2. Rebuild Stage A/mapping contexts so every simulator run uses the calibrated mosaic spread; document the populated value inside diagnostics for traceability.
3. Re-run `compare_stage_a_baseline.py` in both geometry modes plus DB-AT-028/029 to prove ROI-level correlations recover once mosaic blur is in place. Artifacts live under this loop’s directory.
