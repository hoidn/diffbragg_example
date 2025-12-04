# Supervisor Loop — 2026-01-05T150000Z

## Observations
- DB-AT-028/029 remain red after the Phase C.33 subpixel-centering patch: single-pixel probe ratio is still only 0.25% of the expected `(Na·Nb·Nc)^2` even though TRACE_PY now shows `F_latt_a/b/c` hitting 41/29/32 for the traced pixel.
- Probe payloads reveal a gulf between per-sample TRACE_PY output (correct lattice weights) and the aggregated payload exported via `collect_partiality_stats`, which still averages to ~−3.8. This implies we are losing almost all lattice weight while accumulating subpixel contributions.
- To progress we need decision-carrying evidence on how many subpixels actually reach `|Δ_{k,l}| < 1/N` and what fraction of `F_total_squared_pre_lorentz` they contribute before touching the `steps` normalization in production code.

## Plan
1. **Instrument owner hook** — extend `nanobrag_torch.simulator.run` so that when both `collect_partiality_stats` and `trace_pixel` are enabled it slices the partiality tensors down to the traced pixel and caches per-subpixel `delta_{h,k,l}`, `F_latt_{a,b,c}`, and `F_total_squared_pre_lorentz` arrays under guarded `trace_*` keys. Keep tensors on device until serialization to avoid slowing Stage A.
2. **Upgrade the probe** — update `probe_square_lattice_scaling.py` to consume those trace arrays, compute counts for samples with `|Δ_{h,k,l}| < 1/N`, report cumulative `F_total²` mass for the “central lobe” vs the complement, and log the implied `(Na·Nb·Nc)^2` ratio if only those samples contributed. Persist both JSON + Markdown in this report tree.
3. **Validation** — rerun the single‑pixel probe and the enforcement test `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, capturing logs under this timestamp so we can decide whether the next loop tackles `steps` normalization or Lorentz/polar ordering.

Artifacts captured next loop: probe log/JSON/Markdown + pytest log under this directory.
