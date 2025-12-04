# Phase C.39 — Omega compensation handoff (2026-01-12T010000Z)

## Context
- Phase C.38 instrumentation (reports/2026-01-11T010000Z/) isolated the remaining `(N_a·N_b·N_c)^2` deficit to the oversample>1 branch in `nanobrag_torch.simulator.Simulator.run`: the accumulated subpixel sum is multiplied by `last_omega ≈ 1e-6` and never compensated even though SQUARE lattices now use Riemann-sum semantics (steps scalar = 1).
- Single-pixel probe evidence (oversample=13) shows `trace_subpixel_F_total_sq_sum = 1.6148e17`, `trace_normalized_intensity = 1.6148e11`, ratio = 1e-6, while oversample=1 runs remain perfect. Architecture partiality test still fails with ~59% error. DB-AT-028/029 continue to show chi²≈1e5 and negative ROI correlations.

## Decision
- Proceed with Phase C.39 implementation: skip the per-subpixel omega multiplication whenever `crystal.shape == CrystalShape.SQUARE` and `oversample > 1`, then apply the Lorentz `omega_scalar` once after summing subpixels (mirrors oversample=1 path).
- Keep existing behavior for GAUSS/TOPHAT/ROUND shapes.
- Re-run the sanctioned probe + architecture test + DB-AT-028/029 after patching, capturing artifacts under this timestamp.

## Action Items for Ralph
1. Edit `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` to gate the oversample>1 omega multiplication on `crystal.shape != CrystalShape.SQUARE`. Add a single post-sum omega application for the SQUARE branch and leave the Riemann-sum normalization intact.
2. Ensure `_partiality_stats` still emits `trace_subpixel_F_total_sq_sum`, `trace_subpixel_omega_last/mean`, and `trace_normalized_intensity`; add a short marker if needed so the probe can prove omega moved to the post-sum location.
3. Update `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` to assert cpu/cuda legs hit `(N_a·N_b·N_c)^2` within ≤1% for oversample>1 and to guard the telemetry fields.
4. Keep `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` telemetry in sync so the Markdown/JSON show the recovered ratio and debug fields.
5. Capture the vendor diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/omega_compensation.patch`, rerun `python -m pip install -e src/nanobrag-torch`, note the env tag in `patches/environment_tag.md`, and append a one-liner to `docs/findings.md::SIM-CONSTR-PARTIALITY-001`.
6. Rerun the mapped commands (probe, architecture partiality test, DB-AT-028/029) with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and log outputs under this directory.

## Evidence Links
- Prior instrumentation + failure logs: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/`
- Problems ledger entry being serviced: `problems.md` — “DB-AT-028/029 scale mismatch (SCALE-009…)” (unchecked)
- Findings: SIM-CONSTR-PARTIALITY-001, PROBE-FREEZE-001, SCALE-009
