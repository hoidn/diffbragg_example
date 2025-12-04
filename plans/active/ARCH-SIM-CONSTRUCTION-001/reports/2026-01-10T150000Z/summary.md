# Phase C.38 — Oversample accumulation sanity check (2026-01-10T150000Z)

Goal: compare the sanctioned single-pixel probe with oversample toggled between 1×1 (no subpixel sampling) and {5, 13} to determine whether the remaining `(Na·Nb·Nc)^2` deficit is tied solely to the oversample accumulation path.

## Evidence

- `os1_square_lattice_scaling.md/json` — Oversample disabled (`--oversample 1`). Observed intensity ratio = **1,447,642,850.1** vs expected **1,447,650,304.0** (0.0005% error). `F_latt` telemetry hits 38,047.9 (≈41·29·32). Confirms that when the simulator renders a single sample per pixel, the `(Na·Nb·Nc)^2` contract holds.
- `os5_square_lattice_scaling.md/json` — Oversample enabled (`--oversample 5`). Observed ratio collapses to **137,151,105.6** (9.47% of spec), identical to the 13×13 probe from `2026-01-10T010000Z/`. The derived `F_latt` metric tracks the RMS of per-subpixel samples (~4.2k) even though the per-subpixel tensor still contains ±38k spikes.
- `square_lattice_scaling.{json,md}` under `2026-01-10T010000Z/` — Oversample=13 (sanctioned config) now hits Δk=Δl=0 for 48% of subpixels, but intensity ratio remains 0.0939× spec. Changing oversample density leaves the deficit unchanged, reinforcing that the failure lives in the oversample accumulation/normalization path rather than sincg itself.

## Conclusion

The simulator obeys `(Na·Nb·Nc)^2` scaling when oversample=1 but loses ~90% of the expected signal as soon as oversample>1. That isolates the remaining DMI to the oversample accumulation logic in `Simulator.run` (post-sincg, pre-final scaling). Next loop must instrument the accumulation branch to capture:

1. Sum of per-subpixel `F_total_squared_pre_lorentz` before any normalization.
2. Final `normalized_intensity` that gets divided by `steps`.
3. The per-pixel scaling applied when `oversample_omega=False` (currently `last_omega`).

We need to prove exactly where the extra 0.094× factor enters and patch the owner code so SQUARE lattices with `oversample>1` retain integral semantics end-to-end.
