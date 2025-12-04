# Supervisor Summary — 2025-12-26T210000Z

## Evidence
- **Stage A vs reference**: Latest probe still reports `median Stage A / |F|^2·LP = 0.0176` and `median Stage A / |F|^2 = 0.0714`, with worst ROIs showing Stage A/|F|²·LP≈0 despite LP factors between 2.4–5.4× (plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/spot_profile_summary.md:81-118, 98-116).
- **Partiality ledger**: Every ROI remains at `Stage A / (|F|^2·F_latt^2·LP) = 0` even though the calibration advertises N_cells=(41,29,32) and representative reflections report `F_latt≈5.2e3` (same file, lines 125-168).
- **Simulator hook**: Captured stats show panel 0 `f_latt` min=-37533, median=1.3e-4, max=37069 while `f_latt_squared≈1` and Lorentz/polarization factors sit in the expected ranges (plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/summary.md:18-28).
- **Acceptance gates**: DB-AT-028 still records `chi2_per_pixel_initial=2.10e5` and `roi_cc_median_before=-0.053` (db_at_028/db_at_028_metrics.json:2-47), proving the deterministic mismatch persists.

## Diagnosis
`nanobrag_torch.simulator.compute_physics_for_position` (../diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py:292-345) computes `sincg(torch.pi * (h-h0), N)` in float32 and only snaps to ±N when the argument is within ~1e-10 of an integer multiple of π. Our fractional indices routinely land at `n±1e-4`, so both numerator and denominator underflow and the lattice factor collapses to ≈0. The independent reference and hook data confirm Na·Nb·Nc scaling never appears, so Stage A’s forward model is missing the required SQUARE-crystal lattice weighting.

## Directive
1. **Fix the SQUARE branch**: In `compute_physics_for_position` compute `delta_{h,k,l} = (h-h0)` in float64, feed them to `sincg(torch.pi * delta, N)`, multiply the three axes, then cast back to the simulator dtype. Leave ROUND/GAUSS/TOPHAT untouched. Ensure partiality stats keep storing the corrected tensors.
2. **Enforcement test**: Author `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` that instantiates a tiny detector/crystal pair twice (N_cells=(1,1,1) vs (Na,Nb,Nc)) and asserts the intensity ratio equals `(Na·Nb·Nc)^2 ±10%`. This test must fail if sincg regresses.
3. **Environment Freeze log**: Save the patch under `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`, rebuild the editable install (`python -m pip install -e src/nanobrag-torch`), and tag the state as `nanobrag-partiality-2025-12-26` inside the new artifact directory with the rebuild command + `git status` snapshot.
4. **Docs + findings**: Record the fix in docs/fix_plan.md, galph_memory.md, and add SIM-CONSTR-PARTIALITY-001 to docs/findings.md citing the new architecture test and artifact path.
5. **Validation**: Re-run (a) Stage A baseline probe with all collection flags (artifact path rooted here), (b) the new architecture test, and (c) DB-AT-028/029 selectors. Archive logs/metrics under this timestamp.

## Expected Outcome
The probe should now report `median Stage A / (|F|^2·F_latt^2·LP) ≈ 1` and simulator partiality stats should show `median f_latt ≈ Na·Nb·Nc`. DB-AT-028/029 should begin trending toward their gates, and the architecture test will guard against future regressions.
