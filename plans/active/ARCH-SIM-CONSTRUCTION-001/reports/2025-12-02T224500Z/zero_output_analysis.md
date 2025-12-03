# Zero-Output Root Cause Analysis

## Status: BLOCKED - Outdated Probe Template

The diagnostic probe script template provided in `input.md` references APIs that have been refactored during ARCH-BRIDGE-RESP-001 and other initiatives. The probe cannot execute because:

1. **API Refactoring**: Config factory functions moved from `dbex.nanobrag_bridge` to `dbex.refinement.config_factories`
2. **Signature Changes**: `build_structure_factor_grid()` now takes `indices` and `amplitudes` directly instead of `crystal` and `mtz_file_path`
3. **Constructor API**: `Simulator` constructor takes `Crystal` and `Detector` objects (not config objects)
4. **Config Attribute Names**: Attributes renamed (e.g., `a` → `cell_a`, `wavelength` → `wavelength_A`, `pixel_size` → `pixel_size_mm`)

## Partial Probe Results

The probe successfully executed through the detector config creation stage before failing:

### HKL Grid ✓
- **Nonzero count**: 69,614 / 175,959 elements (39.6%)
- **Sum**: 3.305e+06
- **Max**: 5.183e+02
- **Conclusion**: HKL grid is **NOT zero** - structure factors loaded correctly

### Crystal ✓
- **Cell a**: 27.376 Å
- **n_cells**: None (not set)
- **Conclusion**: Crystal config created successfully

### Beam ✓
- **Wavelength**: 0.976800 Å
- **Flux**: 0.0 (default/not set - may be issue!)
- **Conclusion**: Beam config created but flux is zero

### Detector ✓
- **Distance**: 231.3 mm
- **Oversample**: 3 (correctly threaded per DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C)
- **Conclusion**: Detector config created with correct oversample

### Simulator ✗
- **Error**: `TypeError: __init__() got an unexpected keyword argument 'beam'`
- **Cause**: Probe template uses outdated API; Simulator now requires `Crystal` and `Detector` objects, not individual config objects

## Root Cause Hypothesis (Preliminary)

Based on partial probe execution:

**Primary Suspect**: **Beam flux = 0.0**

- HKL grid has 69,614 nonzero structure factors
- Crystal config looks valid (a=27.376 Å)
- Detector config looks valid (dist=231mm, oversample=3)
- **But beam flux is 0.0**

If the simulator multiplies structure factors by flux, then:
```
I_diffracted = |F|² × flux × (other factors)
I_diffracted = 69614 nonzero values × 0.0 × ... = 0.0
```

**Evidence**: The diagnostic shows `flux=0.0` for the beam config, which would cause all simulated intensities to be zero regardless of correct HKL/crystal/detector configurations.

**Counter-evidence needed**: Need to verify whether:
1. Flux is actually used in intensity calculation (check nanobrag_torch.simulator source)
2. Flux should default to 1.0 or some non-zero value for simulations
3. The test that's failing provides explicit flux, or relies on a default

## Recommended Actions

### Option A: Fix Probe Template (Preferred)
1. Galph should provide a corrected probe template matching current architecture
2. Template should demonstrate how to construct `Crystal` and `Detector` objects from configs
3. Rerun probe to completion to verify simulator output

### Option B: Direct Investigation
1. Read `nanobrag_torch.simulator` source to understand intensity calculation
2. Check if flux=0.0 causes zero output
3. If yes, identify where flux should be set in the config factories

### Option C: Test-Based Investigation
1. Run the failing test (`test_db_at_028_loss_scale_sanity`) with added print statements
2. Capture the beam config used by the test
3. Compare against probe's beam config to identify discrepancy

## Next Steps

**Immediate**: Escalate to Galph via `galph_memory.md` and `docs/fix_plan.md`:
- Note that probe template is outdated (post-ARCH-BRIDGE-RESP-001 refactor)
- Share preliminary finding: beam flux=0.0 is likely culprit
- Request either: (a) corrected probe template, or (b) authorization to investigate flux defaults directly in source

**If flux is confirmed as issue**: Open a `bugfix` initiative to ensure `create_beam_config()` sets flux to a sensible default (e.g., 1.0) when not explicitly provided, rather than 0.0.

## Artifacts

- `probe_run.log`: Partial execution log showing successful HKL/crystal/beam/detector creation
- `diagnose_zero_output.py`: Corrected probe script (imports fixed, but Simulator API still incompatible)
- This analysis document

## References

- ARCH-BRIDGE-RESP-001: Config factory relocation
- DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C: Oversample threading (confirmed working: 292/292 configs have oversample=3)
- DB-AT-028: Failing acceptance criterion (chi²/pixel initial ≤ 1e2)
