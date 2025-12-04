# ARCH-SIM-CONSTRUCTION-001 — Supervisor Loop (2026-01-03T150000Z)

**Mode:** Parity  
**Action Type:** planning  
**DecisionStatus:** localized  
**Focus:** Phase C.32 prep — sincg reference comparison

## Observations
- Reviewed Phase C.30/C.31 artifacts (`2026-01-02T010000Z`, `2026-01-03T010000Z`). Single-pixel probe plus payload instrumentation confirm the deterministic deficit persists with one-pixel, single-phi runs: observed `(Na·Nb·Nc)^2` ratio = `8.46e4` vs expected `1.45e9` (0.000058×). Enforcement test remains red (ratio=3.56e6 vs 1.45e9, 99.75% error).
- Payload shows `F_total²_pre_lorentz` and `intensity_pre_polar` deficits align (factor ≈1.8e4), proving Lorentz/polarization are not hiding the issue. `partiality_stats['f_latt']` currently records pre-sum tensors whose mean is −3.8 (base=1.0), so the probe cannot yet attribute the deficit to the kernel vs downstream aggregation.
- Phase C.29 evidence already captured `Δh/Δk/Δl` + per-axis sincg arrays (medians ≈0.06, maxima 29–41), but we still lack a direct comparison against the analytic `sin(NπΔ)/sin(πΔ)` reference for the sampled offsets.

## Decisions
1. Closed Phase C.30/C.31 subtasks in the implementation plan; logged the C.31 attempt in docs/fix_plan.md.
2. Planned new Phase C.32 checklist that builds a high-precision sincg reference inside `probe_square_lattice_scaling.py`, computes per-axis relative error stats, and promotes the initiative to implementation-ready once the failing component (kernel vs downstream multiplication) is proven.
3. No production edits scheduled this loop; focus stays on evidence gathering to avoid patching the simulator without a clear unit-level mismatch.

## Next Actions for Ralph
Outlined in the updated `input.md`:
1. Extend `probe_square_lattice_scaling.py` to evaluate the analytic sincg formula in float64/decimal for each sampled Δh/Δk/Δl and emit per-axis error metrics.
2. Re-run the single-pixel probe plus enforcement test, capture artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T010000Z/`, and summarize whether the deficit exists inside `nanobrag_torch.utils.physics.sincg` or downstream.
3. Update `docs/fix_plan.md` + `implementation.md` with Phase C.32 findings and mark `input.md` patch-ready if the kernel is proven wrong.
