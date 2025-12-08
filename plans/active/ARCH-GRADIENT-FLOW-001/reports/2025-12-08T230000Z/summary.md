### Turn Summary
Isolated the TRUE root cause of gradient magnitude mismatch: `mosaic_spread_deg > 0` in nanobrag_torch breaks gradient computation (ratios of -146× to 1072× vs 1.00× with zero mosaicity).
Systematic investigation (14 probes) ruled out previous hypotheses (HKL sparsity, unit conversion, fluence); the DBEX config factory sets `mosaic_spread_deg` from experiment metadata, causing real datasets to fail gradcheck.
Next: Await nanobrag_torch maintainer response on upstream bug report filed to `~/Documents/nanoBragg/inbox/mosaic_gradient_bug_2025_12_08.md`.
Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/ (dbex_gradient_trace.txt, nanobrag_isolated_gradcheck.txt)
