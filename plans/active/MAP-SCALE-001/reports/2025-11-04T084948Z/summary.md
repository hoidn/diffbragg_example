# MAP-SCALE-001 — Golden Baseline Comparison (2025-11-04T084948Z)

## Command
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
python plans/active/MAP-SCALE-001/bin/compare_simulator_to_golden.py \
  --scale-probe plans/active/MAP-SCALE-001/reports/2025-11-04T082000Z/scale_probe.json \
  --artifact-dir plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z
```

## Key Metrics (`golden_comparison.json`)
- `post_sim_scale_factor` (√spot_scale_override) ≈ **5.64e8**; implied `spot_scale_override` ≈ 3.18e17.
- `golden_over_zero_iter` ratio (median) ≈ **6.0e3** (range 5.2 → 8.2e5) — canonical panels are ~6k× brighter than zero-iteration output per ROI.
- `target_over_golden` ratio (median) ≈ **0.99** — golden tensors track measured targets within ~1%; global mean ratio ≈ 0.81 due to ROI weighting.
- `zero_iter_over_golden_raw` ratio (median) ≈ **9.41e4** — zero-iteration “raw” simulator output is ~10^5× larger than the golden raw tensor prior to applying √spot_scale.
- `scale_probe_global_ratio` (target/zero-iteration mean) ≈ **2.46e4**, consistent with ROI medians once ROI size weighting is considered.

## Observations
- Canonical torch baseline matches DB_AT_024 targets (median target/golden ≈0.99) while current zero-iteration helper remains under-scaled by ~6k× on median ROI.
- DiffBragg metadata exposes a colossal √spot_scale factor (~5.6e8). Directly applying that factor to current simulator output would overshoot by ~9e4× because the unrefined MTZ amplitudes feeding `simulate_forward_once` are already ~9e4× larger than the refined torch raw tensor.
- The scale gap therefore decomposes into **(a)** missing DiffBragg `spot_scale_override` metadata and **(b)** absence of refined structure-factor amplitudes (`Fopt`) captured during DiffBragg refinement; both are required to reach parity with the golden tensors.
- Artifacts captured under `plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z/`:
  - `golden_comparison.json` — detailed per-ROI ratios and metadata provenance.

## Implications
- Remediation must source DiffBragg-refined scale information (global √spot_scale) **and** the refined |F| amplitudes (or equivalent normalization) before updating DB_AT_024 thresholds. Merely plumbing a global constant will not align the intensity field; we need a pipeline to ingest the same calibration artifacts used by canonical capture.
