# 2025-11-04T063053Z — DB-AT-024 zero-iteration baseline probe

## Scope
- Phase A checkpoint: reproduce zero-iteration forward baseline and capture correlation/localization metrics for canonical assets.
- Validate normative references for mapping guard (docs/spec-db-conformance.md, docs/forward_equivalence.md, docs/spec-db-tracing.md).

## Script (T2) — `plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py`
```
$ timeout 120 python plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py
```
```
auto-selected 1-fold oversampling
[HKL stats] h=[-23,8] k=[-27,11] l=[-28,10] hit_rate=6207106/6224001 (99.73%)
{
  "n_roi": 92,
  "corr_median": 0.0488710938419284,
  "corr_min": -0.26732915548656677,
  "corr_max": 0.4307618485236072,
  "localization_mean": 0.5,
  "localization_success_rate": 0.0,
  "global_scale_hint": 62.65738056380318,
  "hkl_stats": {
    "h_min": -24,
    "h_max": 24,
    "k_min": -28,
    "k_max": 28,
    "l_min": -31,
    "l_max": 31,
    "h_range": 49,
    "k_range": 57,
    "l_range": 63,
    "n_reflections": 69614,
    "n_in_range": 69614,
    "in_range_fraction": 1.0,
    "grid_nonzero": 69614,
    "grid_min": 0.0,
    "grid_max": 5.183336792e+02,
    "grid_mean": 18.78112030029297
  }
}
```
> Note: `timeout` terminates the process after metrics are emitted to avoid lingering torch threads.

## Key observations
- Zero-iteration torch vs `data-background` correlation remains low (median ≈ 0.049, min ≈ -0.27) with localization success 0.0; DB-AT-024 acceptance thresholds (≥0.2 / ≥0.90) will currently fail without improved mapping or relaxed gating.
- `global_scale_hint` from `prepare_refinement_inputs` is ≈62.66 ADU, aligning with calibration findings (DB-AT-023); helper should surface this for test assertions.
- HKL grid coverage is 100% in-range with ≈9.97M voxel hit rate, confirming `build_structure_factor_grid` readiness for reuse in helper extraction.
- Script conversion to T2 ensures reproducibility and can be reused by Ralph for metric regressions until automated tests land.

## Next actions
- Draft Do Now directing helper extraction (`simulate_forward_once`), scaling strategy (possibly leveraging `global_scale_hint`), and DB_AT_024 pytest with diagnostic artifact emission + provisional xfail while thresholds unmet.
- Decide whether to assert thresholds immediately or capture failure diagnostics with xfail reason citing current metrics.
