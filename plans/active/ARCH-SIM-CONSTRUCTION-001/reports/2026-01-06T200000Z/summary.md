### Turn Summary (Ralph Loop 2026-01-06T200000Z)

Validated SQUARE lattice normalization fix (simulator.py:1086-1099) — confirmed steps_scalar==1 for both cpu/cuda paths and normalization logic correct per Do Now spec. Architecture enforcement test steps_scalar assertions PASS, but parity validation FAILS with 58% error (observed 601M vs expected 1.45B). Root cause identified as sampling density issue: oversample=13 (169 subpixels) insufficient to capture narrow sincg peaks (width ~1/N_cells) for N_cells=(41,29,32). BLOCKED per input.md line 40-41 escalation criteria; normalization fix correct but inadequate to restore (Na·Nb·Nc)² parity within 1% tolerance. Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/ (BLOCKED.md, pytest_partiality.log, square_lattice_probe.log, square_lattice_scaling.{json,md}, fix_plan_entry.md).

---

# 2026-01-06T200000Z — Phase C.35 Implementation Hand-off

## Context
- Problems ledger item **“DB-AT-028/029 scale mismatch (SCALE-009, ARCH-SIM-CONSTRUCTION-001)”** is still unchecked, and the last two galph_memory entries did not mention it, so this loop services that guard by pushing ARCH-SIM-CONSTRUCTION-001 toward an implementation-ready state.
- Phase C.34 coverage logs (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.md`) show 0/169 subpixels land inside the sincg lobe for the canonical Stage-A geometry, so the `(Na·Nb·Nc)^2` lattice gain collapses even though the per-axis sincg samples are correct.
- Simulator traces prove the only remaining deficit is the uniform division by `oversample²` inside `Simulator.run`, which averages away the few contributing samples for **CrystalShape.SQUARE**; other shapes still need the mean for Gaussian/Tophat PSFs.

## Evidence Links
1. `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.{json,md}` — coverage + ratio tables, `_partiality_stats['steps_scalar']=sources·phi·mosaic·oversample²`.
2. `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/summary.md` — subpixel-centering attempt confirms sincg kernel correctness (Δh can hit zero, Δk/Δl stay ±5.38e-02).
3. `docs/spec-db-core.md:60-140` + `docs/architecture/calibration_scaling.md:1-80` — normative calibration + lattice weighting requirements for SCALE-009.

## Decision / Do Now
- Drop the `oversample * oversample` factor **only when** `self.crystal.config.shape == CrystalShape.SQUARE`, treating the subpixel accumulation as a Riemann sum while leaving GAUSS/TOPHAT/ROUND untouched. Surface the chosen scalar as `_partiality_stats['steps_scalar']` so probes/tests can assert it.
- Extend `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` to read the emitted scalar, tighten the `(Na·Nb·Nc)^2` tolerance, and fail whenever SQUARE mode still divides by oversample².
- Environment Freeze contract: write `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`, record rebuild/tag commands (`nanobrag-partiality-2026-01-06`) in `patches/environment_tag.md`, and append the normalization note to `docs/findings.md::SIM-CONSTR-PARTIALITY-001`.

## Validation Targets
1. Single-pixel probe rerun: `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z …` — expect observed ratio within ≤1 % of `(Na·Nb·Nc)^2` and `_partiality_stats['steps_scalar']=sources·phi·mosaic`.
2. `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — both cpu/cuda legs must pass with updated tolerance, logs saved under this report.
3. DB-AT-028/029 reruns with Stage-A metadata flags + artifact dirs rooted here — chi²/pixel should fall rapidly toward ≤1e2 and ROI corr move positive once the simulator preserves lattice scaling.

## Next Steps for Ralph
- Edit `/home/ollie/Documents/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` (SQUARE branch) + `tests/architecture/test_nanobrag_partiality.py` per above.
- Capture patch + rebuild/tag commands, rerun the mapped tests, and drop the resulting probe JSON/Markdown + pytest logs under this timestamp.
