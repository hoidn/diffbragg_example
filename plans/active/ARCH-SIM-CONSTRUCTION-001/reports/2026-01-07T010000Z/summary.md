# ARCH-SIM-CONSTRUCTION-001 — Oversample Sweep Probe (2026-01-07T010000Z)

## Context
- Input.md 2026-01-06T200000Z Do Now instructed a SQUARE-lattice normalization fix; Ralph implemented it but DB-AT-028/029 parity remained red with the same `(Na·Nb·Nc)^2` deficit.
- BLOCKED.md for that loop hypothesized that the remaining gap might be caused by coarse oversample sampling (13×13) failing to land subpixels inside the narrow sincg peaks, suggesting an oversample sweep.

## What I Ran
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
  --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T010000Z \
  --n-cells 41 29 32 --oversample 41 --phi-count 1 --mosaic-count 1 \
  --spixels 1 --fpixels 1 | tee \
  plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T010000Z/square_lattice_probe.log
```

## Evidence
- Probe JSON/Markdown: `square_lattice_scaling.{json,md}`
- Logs show TRACE_PY instrumentation confirming per-pixel HKL coordinates and F_latt, plus new coverage metrics (Phase C.34) at oversample=41.

## Findings
- **Oversample increase does NOT recover `(Na·Nb·Nc)^2` parity.** Even with 41×41=1681 subpixels, the single-pixel ratio stayed at **85,891.9** (0.0059× expected), identical to the oversample=13 run.
- `min_abs_delta_{h,k,l}` remained ≈5.12e-02, proving that none of the sampled subpixels enter the sincg peak despite the denser grid. Coverage table confirms 0/1681 subpixels meeting the `|Δ| < 1/N` criterion.
- Interestingly, TRACE_PY (from `_apply_debug_output`) still reports `F_latt=38048`, whereas `_partiality_stats['f_latt']` stays near −3.63. This divergence implies that `_compute_physics_for_position` and the later trace disagree on how lattice factors are computed, so the normalization fix alone cannot address the magnitude loss.

## Next Hypothesis
- The mismatch between TRACE_PY (correct F_latt) and `_partiality_stats` (collapsed F_latt) suggests the bug lies inside `_compute_physics_for_position` itself—likely a units mismatch or an incorrect use of fractional HKL deltas when accumulating subpixel contributions. We need instrumentation inside `_compute_physics_for_position` to dump the actual `h,k,l` tensors that drive `sincg()` so we can compare them against the trace output.

## Proposed Next Step
- Add a debug hook in `nanobrag_torch.simulator._compute_physics_for_position` that, when `debug_config['trace_pixel']` is set, records the per-subpixel `h`, `k`, `l`, `delta_{h,k,l}` arrays and the resulting `F_latt_a/b/c` values into `_partiality_stats`.
- Extend `probe_square_lattice_scaling.py` to persist these new arrays/statistics so we can compare the physics kernel inputs vs. the trace outputs in `_apply_debug_output`.
- Re-run the single-pixel probe (oversample=13 is fine) plus the architecture partiality test to capture the enriched telemetry before attempting another simulator fix.
