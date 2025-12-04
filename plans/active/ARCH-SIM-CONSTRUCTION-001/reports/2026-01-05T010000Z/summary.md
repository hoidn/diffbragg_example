# Supervisor Loop — 2026-01-05T010000Z

## Observations
- Phase C.33 landed the centered oversample grid plus `min_abs_delta_{h,k,l}` logging, but only the fast axis now hits Δ≈0. The single-pixel probe still reports `min_abs_delta_k=min_abs_delta_l=5.3846e-02`, and the `(Na·Nb·Nc)^2` ratio only rose from 8.46e4 to 3.56e6 (0.25 % of spec). DB-AT-028/029 remain hard red.
- TRACE_PY output shows the traced pixel evaluates to `F_latt = 41·29·32 = 38,048`, matching spec, while the aggregated payload continues to average `F_latt≈-3.8`. This mismatch plus the flat Δk/Δl data implies the sincg kernel is correct but the subpixel accumulation/normalization is starving the lattice factor (only a handful of subpixels ever reach the central lobe, yet we divide by `oversample²`).

## Decision
- Before prescribing a production fix we need decision-carrying coverage data: how many subpixels actually satisfy `|Δ_{k,l}| < 1/N` and how much of the total `F_total²` mass they contribute? Without that, we cannot tell whether the bug sits in the normalization (wrong `steps` weighting) or in the way subpixel coverage is being sampled.

## Next Action
1. Extend the existing partiality hook so that when both `collect_partiality_stats` and `trace_pixel` are enabled, the simulator caches the traced pixel’s per-subpixel `delta_{h,k,l}`, `F_latt_a/b/c`, and `F_total_squared_pre_lorentz` tensors (guarded, no plan-local probes).
2. Update `probe_square_lattice_scaling.py` to summarize those tensors (counts of samples with `|Δ_{k,l}| < 1/N`, cumulative `F_total²` share, etc.) and drop artifacts here.
3. Rerun the probe + `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, then decide whether the fix should target the `steps` normalization or the subpixel coverage model.
