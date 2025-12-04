# ARCH-SIM-CONSTRUCTION-001 — Phase C.36 Planning (2026-01-08T150000Z)

**Focus**: Simulator Construction Convention Alignment (DB-AT-028/029 SCALE-009 parity)

**Loop Type**: Planning / Parity Localization (no production code edits this loop)

## Context
- Phase C.35 normalization patch landed in the previous loop (`reports/2026-01-08T010000Z/`), dropping the SQUARE-lattice `oversample²` divisor and proving the guard via `tests/architecture/test_nanobrag_partiality.py`. Architecture test now observes ≈601M vs 1.45B (≈41.5% of the target) so the deterministic deficit shrank but persists.
- Single-pixel probe + HKL tensor telemetry (`reports/2026-01-07T150000Z/`) still show the traced pixel’s k/l fractional offsets remain in `[0.0538, 0.1462]`, i.e., **no subpixel ever samples Δ≈0** along those axes. Coverage metrics confirm 0/169 subpixels reach the sincg central lobe even after the centering attempt, which explains the remaining 58.5% deficit.
- Without direct visibility into the subpixel grids we cannot tell whether `_compute_physics_for_position` still builds k/l offsets in the legacy `[0/N, (N-1)/N]` range or whether geometry clamps them positive. We need explicit telemetry on the actual `slow/fast` offsets the simulator uses.

## Decisions
1. **Add instrumentation instead of another blind patch.** Before touching simulator physics again, capture the per-axis subpixel offset arrays (post-centering, per axis) under the existing `_partiality_stats` hook so we can prove (a) whether both axes straddle zero, and (b) whether clamping/mod operations happen before sincg evaluation.
2. **Keep evidence inside owner path.** Reuse the existing `collect_partiality_stats` + `trace_pixel` path; no new plan-local probes allowed per PROBE-FREEZE-001.
3. **Next implementation loop = instrumentation + probe rerun.** Once offsets are logged, rerun the single-pixel probe and partiality architecture test to capture the new telemetry. That evidence will decide whether the next step is a simulator patch (fix offset construction) or a spec-change/escalation if geometry truly forces Δ≥0.

## Next Do Now (hand-off to Ralph)
See `input.md` (this loop) for the concrete command list. Highlights:
- Extend `src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` to record the per-axis `subpixel_offsets_slow` / `subpixel_offsets_fast` tensors (or their HKL deltas) whenever both `collect_partiality_stats` and `trace_pixel` are enabled. Store them under `_partiality_stats['subpixel_offsets']` so existing probes/tests can consume them.
- Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` to emit min/median/max for each offset axis (slow, fast, phi, mosaic) in both JSON + Markdown reports.
- Validation: rerun the single-pixel probe and the partiality enforcement test; no DB-AT rerun until a new simulator fix is proposed.

## Artifacts
- This summary: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/summary.md`
- Input/plan updates recorded in `docs/fix_plan.md`, `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`, and `input.md` (current loop).

