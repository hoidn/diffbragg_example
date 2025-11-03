# NANOBRAG-GOLDEN-001 — Parity Gap Reconnaissance (2025-11-03T233556Z)

## Observations
- Current checkout lacks canonical tensor payloads under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/golden_dataset/` despite manifest references; generator runs recorded in `diffbragg_example_2` left this repo without `.npy` artifacts.
- Fixtures now point to canonical tensors (manifest timestamp 2025-11-03T23:21:14Z), but masked ROI correlation between `bragg_torch.npy` and `bragg_diffbragg.npy` remains ≈ -0.004 (computed via quick Python probe in this loop).
- Torch output exhibits large energy outside ROI mask (max ≈ 3.9e4 photons in excluded pixels). Within ROI, torch values span ~2e-14 to 6.7e3 photons with broad ratio spread (median torch/diff ≈ 2.7e3), confirming intensity mismatch beyond global scaling fixes (SCALE-001/002).

## Implications
- Exit Criterion 4 remains unmet for this checkout until canonical tensors are regenerated locally and archived.
- Parity thresholds (C2) cannot be enforced without understanding per-ROI divergence; instrumentation is required to capture representative ROI overlays/dumps for investigation.

## Next Step Candidates
1. Re-run `scripts/generate_simple_cubic_golden.py` in this repo with `--emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic` and archive outputs under a fresh timestamp.
2. Extend `compute_roi_metrics` to persist sampled ROI triptychs (DiffBragg vs Torch vs Target) and summary stats so Ralph can localize structural mismatches.
3. Add regression probes verifying ROI mask application inside nanobrag_torch (e.g., assert masked pixels retain zero intensity post-simulation).

