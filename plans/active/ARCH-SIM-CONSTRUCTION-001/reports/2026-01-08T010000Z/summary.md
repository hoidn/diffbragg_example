# ARCH-SIM-CONSTRUCTION-001 Phase C.35 — SQUARE lattice normalization patch plan

**Loop**: 2026-01-08T010000Z  
**Focus**: Remove the `oversample²` normalization term for `CrystalShape.SQUARE` so the few subpixels that carry the `(N_a·N_b·N_c)^2` lattice boost are no longer averaged away.  
**DecisionStatus**: localized → patch_ready  
**Action Type**: implementation_ready (Environment-Freeze exception — targeted nanobrag_torch patch)

## Evidence Recap
- Phase C.34/C.35 instrumentation (`reports/2026-01-05T150000Z/`, `2026-01-07T150000Z/`) shows **0/169** subpixels hit the sincg central lobe (|Δk|, |Δl| ≥ 0.0538) while TRACE_PY at the pixel center still reports `F_latt=38,048`. The deficit is purely due to **uniform averaging over oversample² samples** even when only a handful carry the lattice weight.
- `_partiality_stats['steps_scalar']` currently multiplies `sources·phi·mosaic·oversample²` for all lattice shapes; removing the oversample factor for SQUARE lattices would scale the observed ratio by 169×, matching the `(N_a·N_b·N_c)^2` target when the sincg ridge is sparsely sampled.
- Analytic sincg comparison (Phase C.32) and HKL tensor capture (Phase C.35) proved the kernel math is correct; only the accumulation/normalization must change.

## Do Now for Ralph
1. **Simulator normalization fix** — Edit `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` so `steps = sources * phi_steps * mosaic_domains` when `crystal.shape == CrystalShape.SQUARE`; keep the existing `oversample * oversample` factor for other shapes. When partiality stats are enabled, emit the chosen scalar via `_partiality_stats['steps_scalar']` so probes/tests can assert the new behavior.
2. **Patch packaging (Environment Freeze exception)** — Save the diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`, rebuild/install nanobrag_torch (`python -m pip install -e src/nanobrag-torch --no-deps`), and record the rebuild command/tag (`nanobrag-partiality-2026-01-08`) in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/environment_tag.md` per CLAUDE.md requirements.
3. **Findings/doc updates** — Append a SIM-CONSTR-PARTIALITY-001 note to `docs/findings.md` describing the new normalization rule and enforcement hooks.
4. **Test/Probe coverage** — Rerun (a) the single-pixel probe (`plans/.../probe_square_lattice_scaling.py`) with all debug flags, (b) `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, and (c) DB-AT-028/029 selectors with Stage-A baseline metrics enabled. Store all artifacts, logs, the saved patch, and rebuild notes under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/`.

## Expected Outcome
- Single-pixel probe and enforcement test report observed ratio within ≤1% of `(N_a·N_b·N_c)^2`.
- `_partiality_stats['steps_scalar']` matches `sources·phi·mosaic` for SQUARE and retains the old value for other shapes.
- DB-AT-028/029 chi² and ROI correlations move sharply toward spec now that reconstruction and Stage A agree on simulator magnitude.
- Environment Freeze bookkeeping satisfied (patch file, rebuild log, findings entry, environment tag).
