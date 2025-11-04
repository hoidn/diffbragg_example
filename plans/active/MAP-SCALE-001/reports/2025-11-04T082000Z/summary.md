# MAP-SCALE-001 — Planning Kickoff (2025-11-04T082000Z)

## Context
- DB_AT_024 mapping guard remains **xfail**: corr_median≈0.0489, localization_success_rate=0.0 (spec requires ≥0.2 / ≥0.90).
- `simulate_forward_once` diagnostics show per-panel Bragg tensors with max≈8.6e-02, mean≈2.6e-03, while `global_scale_hint≈6.27e+01` suggests targets are ~4 orders of magnitude larger.
- SCALE-001/002 findings bar pre-scaling structure factors but require post-simulation √spot_scale or equivalent global scaling.
- Spec references:
  - `docs/spec-db-workflow.md:33-44` — ADU mode must maintain a learnable global scale with mean(target)/mean(sim_initial) initialization.
  - `docs/architecture.md:88-97` — Stage A expects global scale parameter seeded from ADU averages.

## Observations
- `plans/active/DB-AT-024/reports/2025-11-04T070000Z/mapping_metrics.json` confirms diagnostics:
  - `bragg_stats.mean` ≈ 2.56e-03
  - `bragg_stats.max` ≈ 8.57e-02
  - `diagnostics.global_scale_hint` ≈ 6.27e+01
  - Localization fails because brightest simulated pixel rarely lands near measured ROI maxima (underscaled intensity landscape).
- Canonical generator logs (SCALE-002) show need for large post-sim scale factors (≈5.6e+08) driven by DiffBragg's `spot_scale_override`.
- New analysis (`scale_probe.json`) quantifies mismatch: global target/bragg mean ratio ≈ 2.46e+04, per-ROI ratios median ≈ 5.9e+03 (min ≈ 37, max ≈ 2.46e+05), confirming systematic under-scaling despite SCALE-002 application.
- Strategy evaluation (`strategy_none/global_hint/mean_ratio.json`) shows uniform scaling (global hint or mean ratio) leaves correlation/localization unchanged (median corr ≈ 0.049, localization_success_rate=0.0), implying shape mismatch rather than pure amplitude error.
- Reference check using canonical `bragg_torch.npy` (golden dataset) reproduces spec thresholds (median corr≈0.593, localization_success_rate≈0.935), reinforcing that simulator output is missing refined scale/structure-factor information rather than ROI logic defects.

## Next Steps
1. Capture per-ROI intensity statistics (target mean / bragg mean) to quantify scale gap.
2. Prototype scaling strategies respecting SCALE-001/002 (e.g., use `global_scale_hint`, ratio of means, or inferred `spot_scale_override`).
3. Prepare implementation Do Now for Ralph once a viable strategy meets corr/localization thresholds in analysis mode.

## Artifacts
- None yet (planning-only loop). Future diagnostics to live under this report directory.
