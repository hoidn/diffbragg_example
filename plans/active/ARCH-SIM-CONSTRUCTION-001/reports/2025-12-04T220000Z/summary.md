# ARCH-SIM-CONSTRUCTION-001 Phase C.3 Probe Results

## Configuration

- `spot_scale_override`: 3.105059e+17
- `sqrt(spot_scale)`: 5.572305e+08
- `log_scale_baseline`: 20.138490

## Path A: simulate_forward_once()

- Raw output (before sqrt): mean=1.713925e-09, max=1.104069e-04
- Scaled output (after sqrt): mean=9.550518e-01, max=6.152212e+04

## Path B: Reconstruction Helper (Cold Path)

- Raw simulator output: mean=9.573705e-03, max=8.605372e-02
- After sqrt multiplication: mean=5.334761e+06, max=4.795176e+07
- After scale_factor: mean=5.334761e+06, max=4.795176e+07

## Comparison

- Raw output ratio (A/B): 0.00
- Scaled output ratio (A/B): 0.00
- scale_factor vs sqrt ratio: 1.000000

## Verdict

⚠️  RAW SIMULATOR OUTPUTS DIFFER by 0.00×
   → Simulators are constructed differently (config/calibration mismatch)
⚠️  SCALED OUTPUTS DIFFER by 0.00×
   → Post-run scaling logic differs between paths
✓  scale_factor = sqrt(spot_scale) (ratio=1.000000)

## Recommended Fix

Since `scale_factor = exp(log_scale_baseline)` already equals `sqrt(spot_scale)`, the reconstruction helper should:

1. **NOT** multiply by `sqrt(spot_scale)` separately (would cause double application)
2. Use `bragg_scaled = bragg_panel * scale_factor` only

The current code at `dbex/refinement/reconstruction.py:239` should keep only `scale_factor` and remove any explicit `* sqrt_spot_scale` multiplication.
