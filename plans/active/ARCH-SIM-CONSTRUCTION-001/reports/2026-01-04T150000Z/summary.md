# ARCH-SIM-CONSTRUCTION-001 — Supervisor Loop (2026-01-04T150000Z)

**Mode:** Parity  
**Action Type:** planning  
**DecisionStatus:** localized  
**Focus:** Phase C.33 prep — center fractional HKL offsets for SQUARE lattice

## Observations
- Re-ran `probe_square_lattice_scaling.py` interactively to inspect the `collect_partiality_stats` payload for the 1×1 single-pixel reproducer. 169 subpixel samples (oversample=13) never place the slow (`k`) or `l` axes at zero fractional HKL: `delta_k` ∈ [0.0538, 0.1462], `delta_l` ∈ [−0.1462, −0.0538], and `min(|δ|)` stays at 0.0538. Only the fast axis (`h`) straddles zero (|δ|≤2e−4). Consequently the averaged lattice factor medians shrink to `F_latt_b≈0.11`, `F_latt_c≈0.50`, and the compounded `F_latt` payload remains `−3.8` even though `TRACE_PY` reports `F_latt=38048` at the pixel center.
- Because the oversample grid never samples the Bragg peak along `k`/`l`, the `(Na·Nb·Nc)^2` boost collapses to 0.000058× of the spec despite the sincg kernel matching the analytic reference to <1e−6 absolute error. The DMI now sits squarely in the pixel-coordinate→HKL projection: subpixel offsets are mis-centered for the slow/c axes.

## Decisions
1. Close Phase C.32 in the implementation plan (reference tables prove sincg is correct) and log this loop in docs/fix_plan.md (ATTEMPT 2026-01-04T150000Z) with the new hypothesis: oversample offsets are anchored to the wrong origin for the slow/c axes, so `delta_k/delta_l` never reach 0.
2. Draft Phase C.33 deliverable: re-center the subpixel offsets before the `sincg` call by aligning the oversample grid to the Stage-A pixel center. Concretely, adjust the `subpixel_offsets` block in `nanobrag_torch/simulator.py::_compute_physics_for_position` (or the helper that builds `subpixel_coords_all`) so that both slow and fast offsets span `[-(N-1)/(2N), +(N-1)/(2N)]` with a sample exactly at 0. Capture instrumentation proving `min(|delta_{h,k,l}|) < 1e−6` once the fix lands.
3. No production edits in this loop; enqueue an implementation-ready Do Now for Ralph that patches the oversample offset math plus reruns the single-pixel probe and `tests/architecture/test_nanobrag_partiality.py`.

## Next Actions for Ralph
As described in the refreshed `input.md`:
1. **Fix subpixel centering** — edit `src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` (oversample block around lines 1100-1160) so the subpixel offset grid is generated via `offsets = (torch.arange(N, device, dtype) - (N-1)/2) / N` for both axes (no +0.5 bias). Ensure the resulting `delta_h/k/l` tensors include a zero entry when the detector pixel sits on the reflection center.
2. **Add guard instrumentation** — when `debug_config['collect_partiality_stats']` is enabled, compute and store `min_abs_delta_{h,k,l}` so future probes can assert the oversample grid still spans zero. Update `probe_square_lattice_scaling.py` to display these statistics alongside the ratio ledger.
3. **Validation** — rerun `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py ...` (target directory `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/`) and `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`. Expect `(Na·Nb·Nc)^2` ratio to converge to ≥0.99× of spec and `delta_k/delta_l` medians near 0.
