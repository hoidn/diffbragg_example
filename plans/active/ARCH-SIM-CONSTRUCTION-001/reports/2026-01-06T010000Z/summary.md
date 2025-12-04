# Supervisor Loop — 2026-01-06T010000Z

## Context
- Phase C.34 coverage probe (`2026-01-05T150000Z`) proved the oversample grid never samples \(|\Delta k|<1/29\) or \(|\Delta l|<1/32\) for the canonical single-pixel reproducibility harness. Only the h-axis ever hits \(\Delta=0\) after the C.33 centering patch, so `(Na·Nb·Nc)^2` scaling collapses after we divide by `oversample²` inside `steps`.
- The sincg kernel and per-axis deltas already match the analytic reference (Phase C.32), so the remaining deficit is squarely in the normalization stage of `Simulator.run`.

## Decision
Treat SQUARE lattices as Riemann sums instead of uniform means: when `crystal.shape == CrystalShape.SQUARE`, normalize the summed subpixel contributions by `sources·phi_steps·mosaic_domains` (exclude `oversample²`). Other shapes keep the legacy normalization. Surface the scalar through the partiality stats hook so probes/tests can assert it, and add a regression guard to `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`.

## Next Actions (for Ralph)
1. Edit `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` so `steps` omits the `oversample * oversample` term whenever `self.crystal.config.shape` is `CrystalShape.SQUARE`. Record the chosen scalar in `_partiality_stats['steps_scalar']` when debug hooks are enabled.
2. Update `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` to assert `(Na·Nb·Nc)^2` parity and to fail if `steps_scalar` ever includes `oversample²` for SQUARE lattices.
3. Environment Freeze compliance: capture the diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`, log rebuild/tag commands in `patches/environment_tag.md`, and append a SIM-CONSTR-PARTIALITY-001 note in `docs/findings.md` summarizing the normalization remedy.
4. Validation: rerun the single-pixel probe, `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, and `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with artifacts rooted at this directory. Expected outcome: probe/enforcement ratios ≈ `(41·29·32)²`, DB-AT chi² → ≤1e2, ROI corr ≥ 0.2.
