# Beam Flux Investigation

## Scenario B Trigger
Tests failed in Task C.8 with zero simulator output despite oversample=3 fix:
- `bragg_panel[0] mean (raw sim output): 0.000000e+00`
- `bragg_full mean (final output): 0.000000e+00`
- DB-AT-029 failed: No valid ROI correlations computed for bragg_before

This confirms Ralph's Phase D diagnostic hypothesis: beam flux=0.0 causes zero simulator output.

## Source Code Analysis

### BeamConfig Default
**Location**: `src/nanobrag-torch/src/nanobrag_torch/config.py:33`

```python
@dataclass
class BeamConfig:
    # ... other fields ...

    # Flux and fluence parameters (AT-FLU-001)
    flux: float = 0.0  # Photons per second
    exposure: float = 0.0  # Exposure time in seconds
    beamsize_mm: float = 0.0  # Beam size in mm
    fluence: float = 125932015286227086360700780544.0  # Default from C code
```

**Key finding**: `flux` defaults to `0.0` when not explicitly set.

### create_beam_config() Implementation
**Location**: `dbex/refinement/config_factories.py:234-284`

```python
def create_beam_config(beam, flux=None, beamsize_mm=None, exposure=None) -> BeamConfig:
    # Build kwargs for BeamConfig
    beam_kwargs = {
        'wavelength_A': wavelength_A,
        'polarization_factor': 0.0,
        'nopolar': False,
        'polarization_axis': polarization_axis,
        'dmin': 0.0
    }

    # Only add flux/beamsize/exposure if all three are provided
    if flux is not None:
        beam_kwargs['flux'] = flux
    if beamsize_mm is not None:
        beam_kwargs['beamsize_mm'] = beamsize_mm
    if exposure is not None:
        beam_kwargs['exposure'] = exposure

    return BeamConfig(**beam_kwargs)
```

**Behavior when flux=None**:
- The `flux` field is NOT added to `beam_kwargs`
- BeamConfig is instantiated without explicit `flux` parameter
- BeamConfig dataclass uses default value: `flux=0.0`

### Upstream Callers

**Where create_beam_config() is called**:

1. **stage_a_utils.py:276** (warm path with calibration metadata):
   ```python
   beam_config = create_beam_config(beam, flux=beam_flux, beamsize_mm=beamsize_mm, exposure=beam_exposure)
   ```
   - Extracts `beam_flux` from `calibration_metadata.get("beam_flux")` (line 256)
   - If calibration_metadata is None or doesn't have "beam_flux", then `beam_flux=None`

2. **stage_a_utils.py:525** (_compute_panel_loss cold path):
   ```python
   if beam_config_for_run is None:
       beam_config_for_run = create_beam_config(beam)
   ```
   - NO flux parameter → defaults to `flux=0.0`

3. **stage_a_utils.py:619** (_compute_panel_loss cold path):
   ```python
   if beam_config_for_run is None:
       beam_config_for_run = create_beam_config(beam)
   ```
   - NO flux parameter → defaults to `flux=0.0`

**What values are passed**:
- Warm path (line 276): `beam_flux` from calibration_metadata, which may be None
- Cold paths (lines 525, 619): No flux parameter at all

## Root Cause

**Primary issue**: When `flux=None` (no calibration metadata) or when create_beam_config is called without flux parameter, BeamConfig defaults to `flux=0.0`.

**Why this causes zero output**:
The simulator multiplies structure factors by flux (and other intensity factors):
```
simulator_output = structure_factors × flux × [other_factors] × ...
```

When `flux=0.0`, the entire computation becomes:
```
simulator_output = structure_factors × 0.0 × ... = 0.0
```

This explains:
- Zero bragg_panel mean/max in debug output
- Zero bragg_full mean/max
- No valid ROI correlations (all correlations with zero arrays are NaN/inf)
- chi²/pixel >> 1e2 (comparing real data to zeros)

## Recommended Fix

**Option A: Default flux to 1.0 in BeamConfig dataclass** (simplest)
```python
# src/nanobrag-torch/src/nanobrag_torch/config.py
flux: float = 1.0  # Dimensionless scale (photons per second, 1.0 = neutral scale)
```

**Rationale**:
- Flux=1.0 acts as a neutral dimensionless scale factor (no effect)
- Matches physics convention: when flux is unknown, use 1.0 as identity
- Simple 1-line change in nanobrag_torch
- No changes needed to dbex code

**Option B: Pass explicit flux=1.0 in cold paths** (more invasive)
```python
# dbex/refinement/stage_a_utils.py:525, 619
beam_config_for_run = create_beam_config(beam, flux=1.0)
```

**Rationale**:
- Keeps BeamConfig defaults aligned with C code (flux=0.0)
- Requires changes in multiple call sites
- More complex, less maintainable

**Option C: Extract flux from beam.get_flux() if available**
```python
# dbex/refinement/config_factories.py
def create_beam_config(beam, flux=None, beamsize_mm=None, exposure=None):
    # Try to extract flux from beam metadata
    if flux is None:
        try:
            flux = beam.get_flux()
        except (AttributeError, TypeError):
            flux = 1.0  # Fallback to neutral scale
```

**Rationale**:
- Most robust: uses beam metadata when available
- Fallback to 1.0 ensures non-zero output
- Requires checking if beam.get_flux() method exists in dxtbx

## Recommendation

**Preferred: Option A** — Change BeamConfig default from `flux: float = 0.0` to `flux: float = 1.0`

**Why**:
1. Simplest fix (1 line in nanobrag_torch)
2. Aligns with physics convention (1.0 = neutral scale)
3. No changes needed in dbex calling code
4. Fixes both warm and cold paths
5. Low risk: only affects cases where flux is not explicitly set

**Implementation**:
```python
# src/nanobrag-torch/src/nanobrag_torch/config.py:33
flux: float = 1.0  # Photons per second (1.0 = neutral dimensionless scale when unknown)
```

**Testing**:
- Rerun DB-AT-028/029 → expect PASS
- Verify non-zero bragg_before/bragg_after
- Confirm chi²/pixel initial ≤ 1e2
- Confirm ROI correlation before ≥ 0.2

## Next Steps

1. Apply Option A fix (change BeamConfig flux default to 1.0)
2. Rebuild nanobrag_torch
3. Rerun DB-AT-028/029 validation tests
4. If tests PASS → mark DIAG-NANOBRAGG-OVERSAMPLE-001 done
5. Document in docs/findings.md with DIAG-FLUX-001 tag
6. Unblock ARCH-SIM-CONSTRUCTION-001
